"""Compare Python Ab3P with the frozen, manifest-paired Linux C++ output.

Development and challenge may be inspected during repair. Holdout and reserve
require --frozen-evaluation; --reference-count-only reads no Python predictions.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys
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


def evaluate(corpus: Path, partition: str, detector: Ab3P | None,
             differences_path: Path | None = None) -> dict:
    corpus = corpus.resolve()
    manifest_path = corpus / "manifests/inputs.jsonl"
    status_path = corpus / "reference_cpp/documents.jsonl"
    run = json.loads((corpus / "reference_cpp/run.json").read_text(encoding="utf-8"))
    if run.get("input_manifest_sha256") != sha(manifest_path):
        raise ValueError("reference run and input manifest fingerprints differ")
    rows = [row for row in read_jsonl(manifest_path) if row["partition"] == partition]
    if not rows:
        raise ValueError(f"no manifest rows for {partition}")
    status_rows = read_jsonl(status_path)
    statuses = {}
    for status in status_rows:
        key = status["input_path"], status["input_index"]
        if key in statuses:
            raise ValueError(f"duplicate terminal status: {key}")
        statuses[key] = status
    file_rows = defaultdict(list)
    for row in rows:
        file_rows[row["file"]].append(row)
    totals = defaultdict(Counter)
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
                source_passages, result_passages = source.findall("passage"), result.findall("passage")
                if len(source_passages) != len(result_passages):
                    raise ValueError("output passage count mismatch")
                document_counts = Counter()
                document_differences = []
                for pi, (source_p, result_p) in enumerate(zip(source_passages, result_passages)):
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
                    if detector:
                        document_counts.update(reference=sum(reference.values()),
                                               python=sum(prediction.values()),
                                               shared=sum(shared.values()), passages=1)
                    else:
                        document_counts.update(reference=sum(reference.values()), passages=1)
                    if detector and reference != prediction:
                        document_differences.append(dict(input_path=input_relative, input_index=row["index"],
                                                         document_id=row["document_id"], passage_index=pi,
                                                         cohort=row["cohort"], passage_offset=base,
                                                         text=text, reference_only=list((reference - prediction).elements()),
                                                         python_only=list((prediction - reference).elements())))
                for stratum in ("all", row["cohort"]):
                    totals[stratum].update(document_counts)
                    totals[stratum]["documents"] += 1
                differences.extend(document_differences)
            except (OSError, ValueError, ET.ParseError, IndexError, KeyError, TypeError) as exc:
                failures.append(dict(key=key, reason=str(exc)))
    if differences_path is not None:
        differences_path.parent.mkdir(parents=True, exist_ok=True)
        with differences_path.open("w", encoding="utf-8", newline="\n") as stream:
            for row in differences:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    return dict(partition=partition, reference_count_only=detector is None,
                manifest_sha256=sha(manifest_path), oracle_fingerprint=run["fingerprint"],
                counts={name: dict(totals[name], **(metrics(totals[name]) if detector else {}))
                        for name in sorted(totals)},
                manifest_documents=len(rows), failures=failures,
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
    args = parser.parse_args()
    if args.partition in ("holdout", "reserve") and not (args.reference_count_only or args.frozen_evaluation):
        parser.error("holdout/reserve Python comparison requires --frozen-evaluation")
    if args.reference_count_only and args.differences:
        parser.error("reference counts do not produce differences")
    protected = [args.corpus.resolve() / name for name in
                 ("reference_cpp", "input", "manifests", "sanity_expected")]
    for path in (args.output, args.differences):
        if path and any(path.resolve().is_relative_to(directory) for directory in protected):
            parser.error("reports must not overwrite frozen corpus or reference evidence")
    report = evaluate(args.corpus, args.partition, None if args.reference_count_only else Ab3P(), args.differences)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "failures"}, indent=2))
    if report["failures"]:
        print(json.dumps(report["failures"][:10], indent=2), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
