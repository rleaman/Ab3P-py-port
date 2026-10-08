"""Compare Python Ab3P with the frozen, manifest-paired Linux C++ output.

Development and challenge may be inspected during repair. Holdout and reserve
require --frozen-evaluation; --reference-count-only reads no Python predictions.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Iterable
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ab3p.algorithm import Ab3P


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def family_clusters(articles: Iterable[dict], partition: str) -> dict[tuple[str, int], str]:
    """Union selected PubMed/PMC records that share a frozen family key."""
    articles = [article for article in articles if article["partition"] == partition]
    parents: dict[str, str] = {}

    def root(key: str) -> str:
        parents.setdefault(key, key)
        if parents[key] != key:
            parents[key] = root(parents[key])
        return parents[key]

    for article in articles:
        identity = f"document:{article['file']}#{article['index']}"
        keys = [identity, *article.get("family_keys", [])]
        for key in keys[1:]:
            parents[root(key)] = root(identity)
    result = {}
    for article in articles:
        key = article["file"], article["index"]
        if key in result:
            raise ValueError(f"duplicate article manifest identity: {key}")
        result[key] = root(f"document:{article['file']}#{article['index']}")
    return result


def contained(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"path escapes corpus: {relative}")
    return path


def byte_boundaries(text: str) -> dict[int, int]:
    """Map valid local UTF-8 byte boundaries to local code point boundaries."""
    result = {0: 0}
    position = 0
    for index, character in enumerate(text, 1):
        position += len(character.encode("utf-8"))
        result[position] = index
    return result


def cpp_span(text: str, base: int, global_offset: int, byte_length: int,
             boundaries: dict[int, int] | None = None) -> tuple[int, int]:
    """Convert C++ passage-base-plus-local-byte span to code point units."""
    if boundaries is None:
        boundaries = byte_boundaries(text)
    local_begin = global_offset - base
    local_end = local_begin + byte_length
    if local_begin not in boundaries or local_end not in boundaries or byte_length < 0:
        raise ValueError(f"invalid UTF-8 byte span at {global_offset}, length {byte_length}, base {base}")
    return base + boundaries[local_begin], boundaries[local_end] - boundaries[local_begin]


def reference_relations(passage: ET.Element, text: str, base: int) -> Counter:
    boundaries = byte_boundaries(text)
    annotations = {}
    for annotation in passage.findall("annotation"):
        aid = annotation.get("id")
        if not aid or aid in annotations:
            raise ValueError("missing or duplicate annotation ID")
        annotations[aid] = annotation
    pairs = Counter()
    for relation in passage.findall("relation"):
        nodes = relation.findall("node")
        if len(nodes) != 2 or {node.get("role") for node in nodes} != {"ShortForm", "LongForm"}:
            raise ValueError("invalid relation roles")
        parts = {}
        for node in nodes:
            role = node.get("role")
            if node.get("refid") not in annotations:
                raise ValueError("relation refers to missing annotation")
            annotation = annotations[node.get("refid")]
            locations = annotation.findall("location")
            if len(locations) != 1:
                raise ValueError("annotation must have one location")
            location = locations[0]
            offset, length = cpp_span(text, base, int(location.get("offset")),
                                      int(location.get("length")), boundaries)
            label = annotation.findtext("text", "")
            if text[offset - base:offset - base + length] != label:
                raise ValueError(f"C++ annotation text disagrees with source: {label!r}")
            parts[role] = label, offset, length
        sf, lf = parts["ShortForm"], parts["LongForm"]
        pairs[(sf[0], lf[0], sf[1], lf[1], sf[2], lf[2])] += 1
    return pairs


def python_relations(detector: Ab3P, text: str, base: int) -> Counter:
    pairs = Counter()
    for item in detector.find(text, base):
        sf_start, lf_start = item.sf_offset - base, item.lf_offset - base
        if (sf_start < 0 or lf_start < 0 or text[sf_start:sf_start + len(item.sf)] != item.sf
                or text[lf_start:lf_start + len(item.lf)] != item.lf):
            raise ValueError(f"Python prediction has invalid source span: {item}")
        pairs[(item.sf, item.lf, item.sf_offset, item.lf_offset,
               len(item.sf), len(item.lf))] += 1
    return pairs


def metrics(counts: Counter) -> dict:
    reference, system, shared = (counts[key] for key in ("reference", "python", "shared"))
    return dict(reference=reference, python=system, shared=shared,
                reference_only=reference - shared, python_only=system - shared,
                prediction_agreement=shared / system if system else None,
                recovery=shared / reference if reference else None)


def article_cluster_uncertainty(documents: list[Counter]) -> dict:
    """Linearized ratio uncertainty, clustering all passages by article family."""
    stats = Counter()
    for row in documents:
        reference, system, shared = (row[key] for key in ("reference", "python", "shared"))
        stats.update(clusters=1, reference=reference, python=system, shared=shared,
                     reference_squared=reference ** 2, python_squared=system ** 2,
                     shared_squared=shared ** 2,
                     shared_reference=shared * reference,
                     shared_python=shared * system)
    return uncertainty_from_sufficient_stats(stats)


def uncertainty_from_sufficient_stats(stats: Counter) -> dict:
    """Recompute a cluster interval after adding disjoint article sets."""
    count = stats["clusters"]
    result = {"method": "article-family-cluster linearized SE, normal 95% interval",
              "clusters": count, "sufficient_stats": dict(stats)}
    for label, denominator in (("prediction_agreement", "python"),
                               ("recovery", "reference")):
        total = stats[denominator]
        if count < 2 or total == 0:
            result[label] = None
            continue
        point = stats["shared"] / total
        sum_influence_squared = (stats["shared_squared"]
                                 - 2 * point * stats["shared_" + denominator]
                                 + point ** 2 * stats[denominator + "_squared"])
        variance = count / (count - 1) * max(0.0, sum_influence_squared) / total ** 2
        se = math.sqrt(variance)
        result[label] = {"point": point, "standard_error": se,
                         "lower_95": max(0.0, point - 1.96 * se),
                         "upper_95": min(1.0, point + 1.96 * se)}
    return result


def evaluate(corpus: Path, partition: str, detector: Ab3P | None,
             differences_path: Path | None = None, target: float | None = None) -> dict:
    corpus = corpus.resolve()
    manifest_path = corpus / "manifests/inputs.jsonl"
    status_path = corpus / "reference_cpp/documents.jsonl"
    run = json.loads((corpus / "reference_cpp/run.json").read_text(encoding="utf-8"))
    if run.get("input_manifest_sha256") != sha(manifest_path):
        raise ValueError("reference run and input manifest fingerprints differ")
    manifest_rows = read_jsonl(manifest_path)
    rows = [row for row in manifest_rows if row["partition"] == partition]
    if not rows:
        raise ValueError(f"no manifest rows for {partition}")
    status_rows = read_jsonl(status_path)
    statuses = {}
    for status in status_rows:
        key = status["input_path"], status["input_index"]
        if key in statuses:
            raise ValueError(f"duplicate terminal status: {key}")
        statuses[key] = status
    manifest_keys = {(row["file"], row["index"]) for row in manifest_rows}
    if len(manifest_keys) != len(manifest_rows):
        raise ValueError("duplicate input manifest document identity")
    extra_statuses = statuses.keys() - manifest_keys
    if extra_statuses:
        raise ValueError(f"terminal statuses absent from manifest: {sorted(extra_statuses)[:5]}")
    full_manifest_failures = [status for status in statuses.values()
                              if status.get("status") != "success"]
    file_rows = defaultdict(list)
    for row in rows:
        file_rows[row["file"]].append(row)
    totals = defaultdict(Counter)
    article_manifest = corpus / "manifests/articles.jsonl"
    if article_manifest.exists():
        with article_manifest.open(encoding="utf-8") as stream:
            clusters_by_article = family_clusters(
                (json.loads(line) for line in stream if line.strip()), partition)
        row_keys = {(row["file"], row["index"]) for row in rows}
        if partition in ("development", "holdout", "reserve") and set(clusters_by_article) != row_keys:
            raise ValueError("article and input manifests disagree for partition")
    else:
        clusters_by_article = {}
    clusters = defaultdict(lambda: defaultdict(Counter))
    failures = []
    differences = []
    for input_relative, selected in sorted(file_rows.items()):
        input_path = contained(corpus, input_relative)
        if sha(input_path) != selected[0]["file_sha256"]:
            raise ValueError(f"input hash mismatch: {input_relative}")
        input_docs = ET.parse(input_path).getroot().findall("document")
        output_cache = {}
        for row in selected:
            key = input_relative, row["index"]
            status = statuses.get(key)
            if status is None or status.get("status") != "success":
                failures.append(dict(key=key, reason="missing status" if status is None else status.get("reason")))
                continue
            if (status.get("document_id") != row["document_id"]
                    or status.get("input_sha256") != row["file_sha256"]):
                failures.append(dict(key=key, reason="stale or mispaired status"))
                continue
            try:
                source = input_docs[row["index"]]
                if source.findtext("id") != row["document_id"]:
                    raise ValueError("manifest/input document ID mismatch")
                output_relative = status["output_path"]
                if output_relative not in output_cache:
                    output_path = contained(corpus, output_relative)
                    if sha(output_path) != status["output_sha256"]:
                        raise ValueError("output hash mismatch")
                    output_cache[output_relative] = ET.parse(output_path).getroot().findall("document")
                result = output_cache[output_relative][status["output_index"]]
                if result.findtext("id") != row["document_id"]:
                    raise ValueError("recovered output document ID mismatch")
                if (sorted((x.get("key"), x.text or "") for x in source.findall("infon"))
                        != sorted((x.get("key"), x.text or "") for x in result.findall("infon"))):
                    raise ValueError("output document infons mismatch")
                source_passages, result_passages = source.findall("passage"), result.findall("passage")
                if len(source_passages) != len(result_passages):
                    raise ValueError("output passage count mismatch")
                document_counts = Counter()
                document_strata = defaultdict(Counter)
                document_differences = []
                for pi, (source_p, result_p) in enumerate(zip(source_passages, result_passages)):
                    if (sorted((x.get("key"), x.text or "") for x in source_p.findall("infon"))
                            != sorted((x.get("key"), x.text or "") for x in result_p.findall("infon"))):
                        raise ValueError("output passage infons mismatch")
                    text = source_p.findtext("text", "")
                    base = int(source_p.findtext("offset", "0"))
                    if result_p.findtext("offset") != str(base):
                        raise ValueError("output passage base mismatch")
                    returned_text = result_p.find("text")
                    if returned_text is not None and (returned_text.text or "") != text:
                        raise ValueError("output passage text mismatch")
                    reference = reference_relations(result_p, text, base)
                    prediction = python_relations(detector, text, base) if detector else Counter()
                    shared = reference & prediction
                    unicode_kind = "non_ascii" if any(ord(char) > 127 for char in text) else "ascii"
                    passage_info = row.get("passages", [])
                    passage_type = (passage_info[pi].get("type") or "unspecified"
                                    if pi < len(passage_info) else "unspecified")
                    passage_counts = Counter(reference=sum(reference.values()), passages=1,
                                             characters=len(text),
                                             non_ascii_characters=sum(ord(char) > 127 for char in text))
                    if detector:
                        passage_counts.update(python=sum(prediction.values()),
                                              shared=sum(shared.values()))
                    document_counts.update(passage_counts)
                    for name in (f"passage_type:{passage_type}", f"unicode:{unicode_kind}"):
                        document_strata[name].update(passage_counts)
                    if detector and reference != prediction:
                        document_differences.append(dict(input_path=input_relative, input_index=row["index"],
                                                         document_id=row["document_id"], passage_index=pi,
                                                         cohort=row["cohort"], passage_offset=base,
                                                         text=text, reference_only=list((reference - prediction).elements()),
                                                         python_only=list((prediction - reference).elements())))
                for stratum in ("all", row["cohort"]):
                    totals[stratum].update(document_counts)
                    totals[stratum]["documents"] += 1
                    if detector:
                        cluster = clusters_by_article.get(key, f"{input_relative}#{row['index']}")
                        clusters[stratum][cluster].update(document_counts)
                for stratum, counts in document_strata.items():
                    totals[stratum].update(counts)
                    totals[stratum]["documents"] += 1
                    if detector:
                        cluster = clusters_by_article.get(key, f"{input_relative}#{row['index']}")
                        clusters[stratum][cluster].update(counts)
                differences.extend(document_differences)
            except (OSError, ValueError, ET.ParseError, IndexError, KeyError, TypeError) as exc:
                failures.append(dict(key=key, reason=str(exc)))
    if differences_path is not None:
        differences_path.parent.mkdir(parents=True, exist_ok=True)
        with differences_path.open("w", encoding="utf-8", newline="\n") as stream:
            for row in differences:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    measured = {name: dict(totals[name], **(metrics(totals[name]) if detector else {}))
                for name in sorted(totals)}
    implementation = {path.relative_to(ROOT).as_posix(): sha(path) for path in
                      [*sorted((ROOT / "ab3p").glob("*.py")), Path(__file__)]}
    word_data_dir = ROOT / "BioC_C++_1.1/BioC-APPL-ABBR/WordData"
    word_data = {path.name: sha(path) for path in
                 [*sorted(word_data_dir.glob("*.str")), word_data_dir / "Ab3P_prec.dat"]}
    gate_strata = (["all", "pmc", "pubmed"] if partition in
                   ("development", "holdout", "reserve") else ["all"])
    target_met = (None if target is None else
                  detector is not None and not failures
                  and not full_manifest_failures
                  and not (manifest_keys - statuses.keys()) and all(
                      name in measured
                      and measured[name].get("documents", 0) > 0
                      and measured[name].get("reference", 0) > 0
                      and row.get("prediction_agreement") is not None
                      and row.get("recovery") is not None
                      and row["prediction_agreement"] >= target
                      and row["recovery"] >= target
                      for name in gate_strata for row in [measured.get(name, {})]))
    return dict(partition=partition, reference_count_only=detector is None,
                manifest_sha256=sha(manifest_path), oracle_fingerprint=run["fingerprint"],
                terminal_status_sha256=sha(status_path),
                implementation_sha256=implementation, word_data_sha256=word_data,
                counts=measured, target=target, gate_strata=gate_strata,
                target_met=target_met,
                article_cluster_uncertainty={name: article_cluster_uncertainty(list(clusters[name].values()))
                                             for name in sorted(clusters)},
                manifest_documents=len(rows), failures=failures,
                full_manifest_documents=len(manifest_rows),
                full_manifest_statuses=len(statuses),
                full_manifest_missing_statuses=len(manifest_keys - statuses.keys()),
                full_manifest_failure_statuses=len(full_manifest_failures),
                difference_passages=len(differences) if detector else None)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=ROOT / "evaluation/representative_v1")
    parser.add_argument("--partition", choices=("development", "challenge", "holdout", "reserve"),
                        default="development")
    parser.add_argument("--reference-count-only", action="store_true")
    parser.add_argument("--frozen-evaluation", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--differences", type=Path)
    parser.add_argument("--target", type=float)
    args = parser.parse_args()
    if args.target is not None and not 0 < args.target <= 1:
        parser.error("--target must be greater than 0 and at most 1")
    if args.partition in ("holdout", "reserve") and not (args.reference_count_only or args.frozen_evaluation):
        parser.error("holdout/reserve Python comparison requires --frozen-evaluation")
    if args.reference_count_only and args.differences:
        parser.error("reference counts do not produce differences")
    protected = [args.corpus.resolve() / name for name in
                 ("reference_cpp", "input", "manifests", "sanity_expected")]
    for path in (args.output, args.differences):
        if path and any(path.resolve().is_relative_to(directory) for directory in protected):
            parser.error("reports must not overwrite frozen corpus or reference evidence")
    report = evaluate(args.corpus, args.partition, None if args.reference_count_only else Ab3P(),
                      args.differences, args.target)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "failures"}, indent=2))
    if report["failures"]:
        print(json.dumps(report["failures"][:10], indent=2), file=sys.stderr)
        return 1
    return 1 if report["target_met"] is False else 0


if __name__ == "__main__":
    raise SystemExit(main())
