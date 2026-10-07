#!/usr/bin/env python3
"""Validate frozen inputs or returned C++ reference evidence. Standard library."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def in_root(root: Path, rel: str) -> Path:
    path = (root / rel).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Path escapes bundle: {rel}")
    return path


def text_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_inputs(root: Path, report: dict) -> list[dict]:
    errors = report["errors"]
    protocol = json.loads((root / "protocol.json").read_text(encoding="utf-8"))
    rows = read_jsonl(root / "manifests/inputs.jsonl")
    articles = read_jsonl(root / "manifests/articles.jsonl")
    counts = collections.Counter((r["partition"], r["cohort"]) for r in rows)
    for quota in protocol["allocation"]:
        for cohort in ("pubmed", "pmc"):
            key = (quota["partition"], cohort)
            if counts[key] != quota[cohort]:
                errors.append(f"count {key}: {counts[key]} != {quota[cohort]}")
    representative_rows = [r for r in rows if r["partition"] in ("development", "holdout", "reserve")]
    if len(representative_rows) != len(articles):
        errors.append("articles and representative inputs manifest lengths differ")
    identities = [(r["cohort"], r["partition"], r["document_id"]) for r in representative_rows]
    if len(identities) != len(set(identities)):
        errors.append("duplicate representative document identity")
    locations = [(r["file"], r["index"]) for r in rows]
    if len(locations) != len(set(locations)):
        errors.append("duplicate input file/index mapping")
    input_map = {(r["cohort"], r["partition"], r["document_id"]): r for r in representative_rows}
    for article in articles:
        key = (article["cohort"], article["partition"], article["document_id"])
        mapped = input_map.get(key)
        if not mapped or (mapped["file"], mapped["index"]) != (article["file"], article["index"]):
            errors.append(f"article/input manifest mapping mismatch: {key}")
    families: dict[str, str] = {}
    for row in articles:
        if row["partition"] not in ("development", "holdout", "reserve"):
            continue
        for key in row["family_keys"]:
            old = families.setdefault(key, row["partition"])
            if old != row["partition"]:
                errors.append(f"family crosses partitions: {key}")
    excluded_path = root / "manifests/excluded_family_keys.json"
    if excluded_path.exists():
        excluded = set(json.loads(excluded_path.read_text(encoding="utf-8")).get("keys", []))
        for key in families.keys() & excluded:
            errors.append(f"supplied example/gold family selected: {key}")
    else:
        errors.append("missing excluded-family manifest")
    links_path = root / "manifests/family_links.jsonl"
    if links_path.exists():
        for link in read_jsonl(links_path):
            pmid_key = "pmid:" + link["pmid"]
            partition = families.get(pmid_key)
            if partition is None:
                continue
            for kind in ("pmcid", "doi"):
                if link.get(kind) and families.get(kind + ":" + link[kind], partition) != partition:
                    errors.append(f"cross-reference family split: {pmid_key}/{kind}:{link[kind]}")
    else:
        errors.append("missing family-links manifest")
    paths = sorted({r["file"] for r in rows})
    for rel in paths:
        try:
            path = in_root(root, rel)
            data = path.read_bytes()
            data.decode("utf-8", errors="strict")
            expected_hashes = {r["file_sha256"] for r in rows if r["file"] == rel}
            if expected_hashes != {hashlib.sha256(data).hexdigest()}:
                errors.append(f"file hash mismatch: {rel}")
            xml = ET.fromstring(data)
            if xml.tag != "collection":
                errors.append(f"not a BioC collection: {rel}")
                continue
            subset = sorted((r for r in rows if r["file"] == rel), key=lambda r: r["index"])
            if not all(xml.findtext(field) for field in ("source", "date", "key")) \
                    and not all(r["partition"] == "sanity" for r in subset):
                errors.append(f"missing BioC collection metadata: {rel}")
            docs = xml.findall("document")
            if len(docs) != len(subset):
                errors.append(f"document count mismatch: {rel}")
                continue
            for doc, row in zip(docs, subset):
                key = f"{rel}#{row['index']}"
                if doc.findtext("id") != row["document_id"]:
                    errors.append(f"document ID mismatch: {key}")
                if doc.findall("annotation") or doc.findall("relation"):
                    errors.append(f"preexisting document annotations in detector input: {key}")
                passages = doc.findall("passage")
                if len(passages) != len(row["passages"]):
                    errors.append(f"passage count mismatch: {key}")
                    continue
                base = 0
                for passage, provenance in zip(passages, row["passages"]):
                    value = passage.findtext("text", "")
                    off = passage.findtext("offset")
                    if off != str(provenance["canonical_offset"]):
                        errors.append(f"manifest passage offset mismatch: {key}")
                    if row["partition"] != "sanity" and off != str(base):
                        errors.append(f"noncanonical passage offset: {key}")
                    if text_sha(value) != provenance["text_sha256"]:
                        errors.append(f"text round trip mismatch: {key}")
                    if len(value) != provenance["length_codepoints"]:
                        errors.append(f"passage length mismatch: {key}")
                    if passage.findall("annotation") or passage.findall("relation"):
                        errors.append(f"preexisting annotations in detector input: {key}")
                    base += len(value) + 1
        except (OSError, ValueError, ET.ParseError) as exc:
            errors.append(f"unreadable input {rel}: {exc}")
    checksum_path = root / "manifests/files.sha256"
    if checksum_path.exists():
        listed = set()
        for line in checksum_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            expected, rel = line.split("  ", 1)
            if rel in listed:
                errors.append(f"duplicate package hash entry: {rel}")
            listed.add(rel)
            try:
                if sha(in_root(root, rel)) != expected:
                    errors.append(f"package hash mismatch: {rel}")
            except (OSError, ValueError) as exc:
                errors.append(f"missing package file {rel}: {exc}")
        actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
                  and "reference_cpp" not in p.relative_to(root).parts
                  and p != checksum_path}
        if actual != listed:
            errors.append(f"package hash file set mismatch: {len(actual - listed)} unlisted, "
                          f"{len(listed - actual)} absent")
    else:
        errors.append("missing manifests/files.sha256")
    report["counts"] = {f"{k[0]}/{k[1]}": v for k, v in sorted(counts.items())}
    report["input_documents"] = len(rows)
    report["input_files"] = len(paths)
    return rows


def byte_span(text: str, begin: int, length: int) -> str | None:
    data = text.encode("utf-8")
    if begin < 0 or length < 0 or begin + length > len(data):
        return None
    try:
        return data[begin:begin + length].decode("utf-8")
    except UnicodeDecodeError:
        return None


def validate_output_doc(input_doc: ET.Element, output_doc: ET.Element) -> list[str]:
    errors = []
    if output_doc.findtext("id") != input_doc.findtext("id"):
        errors.append("document_id")
    source_doc_infons = sorted((x.get("key"), x.text or "") for x in input_doc.findall("infon"))
    result_doc_infons = sorted((x.get("key"), x.text or "") for x in output_doc.findall("infon"))
    if source_doc_infons != result_doc_infons:
        errors.append("document_infons")
    source_passages = input_doc.findall("passage")
    result_passages = output_doc.findall("passage")
    if len(source_passages) != len(result_passages):
        return errors + ["passage_count"]
    for source, result in zip(source_passages, result_passages):
        base = int(source.findtext("offset", "-1"))
        if result.findtext("offset") != str(base):
            errors.append("passage_offset")
        source_infons = sorted((x.get("key"), x.text or "") for x in source.findall("infon"))
        result_infons = sorted((x.get("key"), x.text or "") for x in result.findall("infon"))
        if source_infons != result_infons:
            errors.append("passage_infons")
        text = source.findtext("text", "")
        returned_text = result.find("text")
        if returned_text is not None and (returned_text.text or "") != text:
            errors.append("passage_text")
        ann = {}
        for a in result.findall("annotation"):
            aid = a.get("id")
            if not aid or aid in ann:
                errors.append("annotation_id")
            ann[aid] = a
            locations = a.findall("location")
            if len(locations) != 1:
                errors.append("annotation_location_count")
                continue
            try:
                offset = int(locations[0].get("offset", "-1")) - base
                length = int(locations[0].get("length", "-1"))
            except ValueError:
                errors.append("annotation_location_number")
                continue
            span = byte_span(text, offset, length)
            if span is None or span != a.findtext("text", ""):
                errors.append("annotation_span")
        for relation in result.findall("relation"):
            nodes = relation.findall("node")
            if len(nodes) != 2:
                errors.append("relation_node_count")
                continue
            roles = {n.get("role") for n in nodes}
            if roles != {"LongForm", "ShortForm"}:
                errors.append("relation_roles")
            if any(n.get("refid") not in ann for n in nodes):
                errors.append("relation_refid")
    return errors


def occurrence_signature(doc: ET.Element) -> collections.Counter:
    result = collections.Counter()
    for pindex, passage in enumerate(doc.findall("passage")):
        annotations = {a.get("id"): a for a in passage.findall("annotation")}
        for relation in passage.findall("relation"):
            nodes = {n.get("role"): annotations.get(n.get("refid")) for n in relation.findall("node")}
            if set(nodes) != {"LongForm", "ShortForm"} or any(a is None for a in nodes.values()):
                continue
            pair = []
            for role in ("LongForm", "ShortForm"):
                annotation = nodes[role]
                location = annotation.find("location")
                pair.append((annotation.findtext("text", ""),
                             location.get("offset") if location is not None else None,
                             location.get("length") if location is not None else None))
            result[(pindex, *pair)] += 1
    return result


def validate_reference(root: Path, rows: list[dict], report: dict) -> None:
    errors = report["errors"]
    ref = root / "reference_cpp"
    checksum_path = ref / "files.sha256"
    if checksum_path.exists():
        for line in checksum_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            expected, rel = line.split("  ", 1)
            try:
                if sha(in_root(ref, rel)) != expected:
                    errors.append(f"returned reference hash mismatch: {rel}")
            except (OSError, ValueError) as exc:
                errors.append(f"missing returned reference file {rel}: {exc}")
    if not (ref / "run.json").exists():
        errors.append("missing reference_cpp/run.json")
        return
    build_note = ref / "build_provenance.json"
    if not build_note.exists():
        errors.append("missing build provenance metadata")
    else:
        metadata = json.loads(build_note.read_text(encoding="utf-8"))
        for field in ("compiler", "build_flags", "source_patches"):
            if field not in metadata:
                errors.append(f"missing build provenance field: {field}")
    run = json.loads((ref / "run.json").read_text(encoding="utf-8"))
    if run.get("input_manifest_sha256") != sha(root / "manifests/inputs.jsonl"):
        errors.append("reference input manifest fingerprint mismatch")
    statuses = read_jsonl(ref / "documents.jsonl") if (ref / "documents.jsonl").exists() else []
    latest = {(r["input_path"], r["input_index"]): r for r in statuses}
    if len(latest) != len(statuses):
        errors.append("duplicate terminal document status rows")
    if len(latest) != len(rows):
        errors.append(f"terminal document count {len(latest)} != input count {len(rows)}")
    report["reference_statuses"] = dict(collections.Counter(r.get("status", "unknown") for r in latest.values()))
    current_input_rel = None
    current_input_docs: list[ET.Element] = []
    current_output_rel = None
    current_output_docs: list[ET.Element] = []
    current_output_hash = None
    sanity_checked = 0
    for row in rows:
        key = (row["file"], row["index"])
        result = latest.get(key)
        if not result:
            errors.append(f"missing reference status: {key}")
            continue
        if result.get("document_id") != row["document_id"] or result.get("input_sha256") != row["file_sha256"]:
            errors.append(f"mismatched reference input: {key}")
        if result.get("status") != "success":
            errors.append(f"reference failed: {key}: {result.get('reason')}")
            continue
        rel = result.get("output_path")
        if not rel:
            errors.append(f"missing output path: {key}")
            continue
        try:
            path = in_root(root, rel)
            if rel != current_output_rel:
                output_bytes = path.read_bytes()
                output_bytes.decode("utf-8", errors="strict")
                current_output_hash = hashlib.sha256(output_bytes).hexdigest()
                current_output_docs = ET.fromstring(output_bytes).findall("document")
                current_output_rel = rel
            if current_output_hash != result.get("output_sha256"):
                errors.append(f"reference output hash mismatch: {key}")
            out = current_output_docs[result["output_index"]]
            if row["file"] != current_input_rel:
                current_input_docs = ET.parse(in_root(root, row["file"])).getroot().findall("document")
                current_input_rel = row["file"]
            src = current_input_docs[row["index"]]
            for problem in validate_output_doc(src, out):
                errors.append(f"reference {problem}: {key}")
            if row["partition"] == "sanity":
                expected_path = root / "sanity_expected" / Path(row["file"]).name
                expected_docs = ET.parse(expected_path).getroot().findall("document")
                expected = expected_docs[row["index"]]
                if occurrence_signature(out) != occurrence_signature(expected):
                    errors.append(f"sanity oracle mismatch: {key}")
                sanity_checked += 1
        except (OSError, ValueError, ET.ParseError, IndexError, KeyError) as exc:
            errors.append(f"invalid reference output: {key}: {exc}")
    report["sanity_documents_checked"] = sanity_checked


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--stage", choices=("input", "reference"), required=True)
    args = parser.parse_args()
    root = args.corpus.resolve()
    report: dict = {"stage": args.stage, "errors": []}
    try:
        rows = validate_inputs(root, report)
        if args.stage == "reference":
            validate_reference(root, rows, report)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        report["errors"].append("validator exception: " + str(exc))
    report["ok"] = not report["errors"]
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.stage == "reference" and (root / "reference_cpp").exists():
        ref = root / "reference_cpp"
        checksum_path = ref / "files.sha256"
        if not checksum_path.exists():
            (ref / "validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            paths = sorted(p for p in ref.rglob("*") if p.is_file() and p.name != "files.sha256")
            checksum_path.write_text(
                "".join(f"{sha(p)}  {p.relative_to(ref).as_posix()}\n" for p in paths), encoding="utf-8")
    raise SystemExit(0 if report["ok"] else 1)


if __name__ == "__main__":
    main()
