"""Combine untouched primary holdout and its versioned expansion exactly.

Without --frozen-evaluation, only C++ reference counts and coverage are read.
The final option records holdout use before running Python comparisons.
"""

from __future__ import annotations

import argparse
from collections import Counter
import datetime as dt
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ab3p.algorithm import Ab3P
from audit.evaluate_representative import evaluate, metrics, sha, uncertainty_from_sufficient_stats
from audit.freeze_phase3 import FREEZE, data_paths, hashes, source_paths

PARENT = ROOT / "evaluation/representative_v1"
EXPANSION = ROOT / "evaluation/representative_v1_expansion_v1"
REPORTS = ROOT / "evaluation/phase3_reports"
ADDENDUM = ROOT / "corpus/holdout_expansion_v1.json"


def oracle_key(run: dict) -> dict:
    return {"executable_sha256": run.get("executable_sha256"),
            "source_files": run.get("source", {}).get("files"),
            "word_data_files": run.get("word_data", {}).get("files"),
            "medpost": run.get("medpost"),
            "path_Ab3P_sha256": run.get("path_Ab3P_sha256"),
            "runtime_data_paths": run.get("runtime_data_paths"),
            "compiler": run.get("compiler"),
            "build_flags": run.get("build_flags"),
            "portability_changes": run.get("portability_changes"),
            "locale": run.get("locale")}


def combined_counts(reports: list[dict], stratum: str) -> dict:
    totals = Counter()
    for report in reports:
        row = report["counts"].get(stratum, {})
        for name in ("reference", "python", "shared", "documents", "passages",
                     "characters", "non_ascii_characters"):
            totals[name] += row.get(name, 0)
    if all(report.get("reference_count_only") for report in reports):
        return {key: totals[key] for key in ("reference", "documents", "passages",
                                              "characters", "non_ascii_characters")}
    return dict(totals, **metrics(totals))


def validate_family_separation() -> None:
    existing = set()
    for line in (PARENT / "manifests/articles.jsonl").open(encoding="utf-8"):
        if line.strip():
            existing.update(json.loads(line).get("family_keys", []))
    for line in (EXPANSION / "manifests/articles.jsonl").open(encoding="utf-8"):
        if line.strip():
            row = json.loads(line)
            common = existing & set(row.get("family_keys", []))
            if common:
                raise ValueError(f"Expansion reuses parent family: {row['document_id']}: {sorted(common)[:3]}")


def collect_reports(detector: Ab3P | None, difference_prefix: Path | None) -> list[dict]:
    reports = []
    for name, corpus in (("primary", PARENT), ("expansion", EXPANSION)):
        differences = (difference_prefix.with_name(difference_prefix.name + f"_{name}.jsonl")
                       if difference_prefix else None)
        report = evaluate(corpus, "holdout", detector, differences)
        if (report["failures"] or report["full_manifest_missing_statuses"]
                or report["full_manifest_failure_statuses"]):
            raise ValueError(f"{name} oracle coverage incomplete: "
                             f"{len(report['failures'])} failures, "
                             f"{report['full_manifest_missing_statuses']} missing statuses, "
                             f"{report['full_manifest_failure_statuses']} failed statuses")
        if report["counts"]["all"]["documents"] != report["manifest_documents"]:
            raise ValueError(f"{name} document coverage incomplete")
        reports.append(report)
    return reports


def validate_code_freeze() -> str:
    record = json.loads(FREEZE.read_text(encoding="utf-8"))
    if (record.get("target") != 0.999 or record.get("holdout_python_inspected") is not False
            or record.get("test_exit_code") != 0):
        raise ValueError("phase 3 code freeze is not a tested, unopened 99.9% baseline")
    if record["source_sha256"] != hashes(source_paths()):
        raise ValueError("Python source or tests changed since the phase 3 code freeze")
    if record["word_data_sha256"] != hashes(data_paths()):
        raise ValueError("WordData changed since the phase 3 code freeze")
    return sha(FREEZE)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-evaluation", action="store_true")
    parser.add_argument("--output", type=Path,
                        default=REPORTS / "final_holdout_checkpoint.json")
    parser.add_argument("--differences-prefix", type=Path,
                        default=REPORTS / "final_holdout_differences")
    args = parser.parse_args()
    for path in (args.output, args.differences_prefix):
        if (path.resolve().is_relative_to(PARENT.resolve())
                or path.resolve().is_relative_to(EXPANSION.resolve())):
            parser.error("report output must be outside frozen bundles")
    for corpus in (PARENT, EXPANSION):
        if not (corpus / "reference_cpp/run.json").is_file():
            parser.error(f"missing C++ reference: {corpus}")
    spec = json.loads(ADDENDUM.read_text(encoding="utf-8"))
    primary_run, expansion_run = [json.loads((corpus / "reference_cpp/run.json")
                                             .read_text(encoding="utf-8"))
                                  for corpus in (PARENT, EXPANSION)]
    if oracle_key(primary_run) != oracle_key(expansion_run):
        parser.error("primary and expansion C++ oracle versions differ")
    if primary_run["executable_sha256"] != spec["required_executable_sha256"]:
        parser.error("C++ executable does not match expansion addendum")
    validate_family_separation()
    reference_reports = collect_reports(None, None)
    reference_counts = {name: combined_counts(reference_reports, name)
                        for name in ("all", "pmc", "pubmed")}
    minimums = spec["minimum_final_reference_occurrences"]
    adequate = all(reference_counts[name]["reference"] >= minimums[name]
                   for name in minimums)
    report = {"status": "reference-count-only", "evidence_size_met": adequate,
              "minimum_reference_occurrences": minimums,
              "addendum_sha256": sha(ADDENDUM),
              "combiner_sha256": sha(Path(__file__)),
              "reference_counts": reference_counts,
              "primary_manifest_sha256": reference_reports[0]["manifest_sha256"],
              "expansion_manifest_sha256": reference_reports[1]["manifest_sha256"],
              "executable_sha256": primary_run["executable_sha256"],
              "primary_oracle_fingerprint": primary_run["fingerprint"],
              "expansion_oracle_fingerprint": expansion_run["fingerprint"],
              "holdout_python_inspected": False}
    if args.frozen_evaluation and adequate:
        report["code_freeze_sha256"] = validate_code_freeze()
        REPORTS.mkdir(parents=True, exist_ok=True)
        history = REPORTS / "holdout_use_history.jsonl"
        begun = {"at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                 "status": "started", "primary_manifest_sha256": report["primary_manifest_sha256"],
                 "expansion_manifest_sha256": report["expansion_manifest_sha256"],
                 "executable_sha256": report["executable_sha256"]}
        with history.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(begun, sort_keys=True) + "\n")
        detector = Ab3P()
        scored = collect_reports(detector, args.differences_prefix)
        if scored[0]["implementation_sha256"] != scored[1]["implementation_sha256"]:
            raise ValueError("Python implementation changed between holdout parts")
        if scored[0]["word_data_sha256"] != scored[1]["word_data_sha256"]:
            raise ValueError("WordData changed between holdout parts")
        names = sorted(set(scored[0]["counts"]) | set(scored[1]["counts"]))
        counts = {name: combined_counts(scored, name) for name in names}
        uncertainty = {}
        for name in names:
            stats = Counter()
            for part in scored:
                stats.update(part["article_cluster_uncertainty"]
                             .get(name, {}).get("sufficient_stats", {}))
            uncertainty[name] = uncertainty_from_sufficient_stats(stats)
        target_met = all(counts[name]["prediction_agreement"] is not None
                         and counts[name]["recovery"] is not None
                         and counts[name]["prediction_agreement"] >= 0.999
                         and counts[name]["recovery"] >= 0.999
                         for name in ("all", "pmc", "pubmed"))
        report.update(status="frozen-evaluation", holdout_python_inspected=True,
                      counts=counts, article_cluster_uncertainty=uncertainty,
                      implementation_sha256=scored[0]["implementation_sha256"],
                      word_data_sha256=scored[0]["word_data_sha256"],
                      target=0.999, target_met=target_met)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    if report["holdout_python_inspected"]:
        history = REPORTS / "holdout_use_history.jsonl"
        with history.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps({"at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                                     "status": "completed", "target_met": report["target_met"],
                                     "output": str(args.output.resolve())}, sort_keys=True) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "evidence_size_met",
                                                 "reference_counts", "holdout_python_inspected")}, indent=2))
    if args.frozen_evaluation and not adequate:
        print("C++ reference count is below the frozen minimum; Python holdout remained unopened.",
              file=sys.stderr)
    return 0 if (not args.frozen_evaluation and adequate) or report.get("target_met") else 1


if __name__ == "__main__":
    raise SystemExit(main())
