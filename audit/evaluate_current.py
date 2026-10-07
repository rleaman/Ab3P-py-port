"""Evaluate the installed Python code against BioC reference occurrences.

No monkeypatches, TSV parsing, whitespace normalization, or deduplication.
Historical audit results and saved example outputs are never rewritten.
"""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ab3p.algorithm import Ab3P
from audit.compare_ab3p import documents, read_annotations, as_relation, metrics


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def evaluate_file(input_path, reference_path, detector):
    reference = read_annotations(reference_path)
    seen = set()
    expected, predicted = Counter(), Counter()
    differences = []
    counts = Counter()
    for di, doc in enumerate(documents(input_path)):
        counts["documents"] += 1
        docid = doc.findtext("id")
        for pi, passage in enumerate(doc.findall("passage")):
            key = di, docid, pi
            seen.add(key)
            if key not in reference:
                raise ValueError(f"Missing reference passage: {input_path.name}, {key}")
            text = passage.findtext("text", "")
            offset = int(passage.findtext("offset", "0"))
            counts["passages"] += 1
            counts["characters"] += len(text)
            counts["non_ascii_characters"] += sum(ord(c) > 127 for c in text)
            found = detector.find(text, offset)
            r = Counter(reference[key])
            p = Counter(as_relation(a) for a in found)
            expected.update({key + item: n for item, n in r.items()})
            predicted.update({key + item: n for item, n in p.items()})
            # These offsets use Python code points. Byte-offset compatibility
            # with non-ASCII C++ input remains a separate validation task.
            for a in found:
                assert text[a.sf_offset-offset:a.sf_offset-offset+len(a.sf)] == a.sf
                assert text[a.lf_offset-offset:a.lf_offset-offset+len(a.lf)] == a.lf
            if r != p:
                differences.append(dict(file=input_path.name, document_index=di,
                    document_id=docid, passage_index=pi, passage_offset=offset, text=text,
                    reference_only=list((r-p).elements()), system_only=list((p-r).elements()),
                    current=[a.__dict__ for a in found]))
    if seen != reference.keys():
        raise ValueError(f"Reference contains passages absent from input: {reference_path}")
    return metrics(expected, predicted), counts, differences


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "examples/input")
    parser.add_argument("--reference", type=Path, default=ROOT / "examples/reference_output")
    parser.add_argument("--reference-kind", choices=["cpp", "gold"], default="cpp")
    parser.add_argument("--output", type=Path, default=ROOT / "audit/current_summary.json")
    parser.add_argument("--differences", type=Path, default=ROOT / "audit/current_differences.jsonl")
    parser.add_argument("--target", type=float,
                        help="fail unless exact precision AND recall meet this fraction in every stratum")
    args = parser.parse_args()
    if args.target is not None and not 0 < args.target <= 1:
        parser.error("--target must be greater than 0 and at most 1")
    if args.input.is_dir():
        if not args.reference.is_dir():
            parser.error("a directory input requires a directory reference")
        cases = [(p, args.reference / p.name) for p in sorted(args.input.iterdir())
                 if p.is_file() and p.suffix.lower() == ".xml"]
    else:
        cases = [(args.input, args.reference)]
    if not cases or any(not p.is_file() or not r.is_file() for p, r in cases):
        parser.error("every input must have a matching reference XML file")
    # Keep reports away from corpus/reference and checked-in historical files.
    protected = {p.resolve() for case in cases for p in case}
    for path in [args.output, args.differences]:
        if path.resolve() in protected:
            parser.error("report paths must not overwrite an input or reference")
        path.parent.mkdir(parents=True, exist_ok=True)
    if args.output.resolve() == args.differences.resolve():
        parser.error("summary and differences paths must differ")
    detector = Ab3P()
    started = time.perf_counter()
    summary = dict(reference_kind=args.reference_kind, min_precision=detector.min_precision,
                   offset_unit="Python Unicode code points; C++ equivalence tested separately",
                   target=args.target, files={}, source_sha256={}, data_sha256={})
    for path in sorted((ROOT / "ab3p").glob("*.py")) + [Path(__file__), ROOT / "audit/compare_ab3p.py"]:
        summary["source_sha256"][str(path.relative_to(ROOT))] = sha256(path)
    data = ROOT / "BioC_C++_1.1/BioC-APPL-ABBR/WordData"
    for path in sorted(data.glob("*.str")) + [data / "Ab3P_prec.dat"]:
        summary["data_sha256"][path.name] = sha256(path)
    totals = defaultdict(Counter)
    with args.differences.open("w", encoding="utf-8", newline="\n") as stream:
        for input_path, reference_path in cases:
            result, counts, differences = evaluate_file(input_path, reference_path, detector)
            summary["files"][input_path.name] = dict(result, input_sha256=sha256(input_path),
                reference_sha256=sha256(reference_path), input=str(input_path.resolve()),
                reference_path=str(reference_path.resolve()), corpus_counts=dict(counts))
            category = ("full" if "_full_" in input_path.name else
                        "tiab" if "_tiab_" in input_path.name else "other")
            for name in ["all", category]:
                totals[name].update({key: result[key] for key in
                                    ["reference", "system", "common", "reference_only", "system_only"]})
            for difference in differences:
                stream.write(json.dumps(difference, ensure_ascii=True) + "\n")
            print(input_path.name, result, flush=True)
    summary["exact_occurrences"] = {}
    for name, count in totals.items():
        r, s, c = count["reference"], count["system"], count["common"]
        summary["exact_occurrences"][name] = dict(count, precision=c/s if s else 0,
            recall=c/r if r else 0, f1=2*c/(r+s) if r+s else 0)
    summary["elapsed_seconds"] = time.perf_counter() - started
    summary["target_met"] = (None if args.target is None else all(
        row["precision"] >= args.target and row["recall"] >= args.target
        for row in summary["exact_occurrences"].values()))
    args.output.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary["exact_occurrences"], indent=2), flush=True)
    return 1 if summary["target_met"] is False else 0


if __name__ == "__main__":
    raise SystemExit(main())
