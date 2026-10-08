"""Record the repaired implementation before the untouched reserve comparison."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audit.evaluate_representative import sha

REPORTS = ROOT / "evaluation/phase3_reports"
FREEZE = ROOT / "corpus/phase3_reserve_code_freeze.json"
FAILED_FINAL = REPORTS / "final_holdout_checkpoint.json"
INPUT_FREEZE = ROOT / "corpus/reserve_input_freeze_v1.json"
INPUT_BUNDLE = ROOT / "evaluation/representative_v1_reserve_expansion_v1"
INPUT_CACHE = ROOT / "evaluation/representative_v1_reserve_expansion_v1_cache"
WORD_DATA = ROOT / "BioC_C++_1.1/BioC-APPL-ABBR/WordData"


def source_paths() -> list[Path]:
    return [*sorted((ROOT / "ab3p").glob("*.py")),
            *sorted((ROOT / "tests").glob("test_*.py")),
            *(ROOT / "audit" / name for name in (
                "compare_ab3p.py", "evaluate_current.py", "evaluate_representative.py",
                "evaluate_final_holdout.py", "freeze_phase3.py",
                "evaluate_final_reserve.py", "freeze_reserve.py")),
            ROOT / "corpus/prepare.py", ROOT / "corpus/expand_reserve.py"]


def data_paths() -> list[Path]:
    return sorted(path for path in WORD_DATA.iterdir() if path.is_file())


def hashes(paths: list[Path]) -> dict[str, str]:
    return {path.relative_to(ROOT).as_posix(): sha(path) for path in paths}


def check_input_freeze() -> str:
    record = json.loads(INPUT_FREEZE.read_text(encoding="utf-8"))
    archive = INPUT_BUNDLE.with_name(INPUT_BUNDLE.name + ".input.tar.gz")
    files = {"protocol_sha256": ROOT / "corpus/reserve_expansion_v1.json",
             "selection_log_sha256": INPUT_CACHE / "selection.jsonl",
             "input_manifest_sha256": INPUT_BUNDLE / "manifests/inputs.jsonl",
             "package_files_sha256": INPUT_BUNDLE / "manifests/files.sha256",
             "input_archive_sha256": archive}
    if record.get("status") != "input-frozen-before-reserve-python-comparison":
        raise ValueError("Reserve input freeze status is invalid")
    for field, path in files.items():
        if record.get(field) != sha(path):
            raise ValueError(f"Reserve input changed: {field}")
    if archive.stat().st_size != record["input_archive_bytes"]:
        raise ValueError("Reserve input archive size changed")
    return sha(INPUT_FREEZE)


def check_baselines() -> dict[str, dict]:
    names = {"examples": ROOT / "audit/current_summary.json",
             "development": REPORTS / "development_family_cluster.json",
             "challenge": REPORTS / "challenge_family_cluster.json",
             "gold": ROOT / "audit/current_gold_summary.json"}
    reports = {name: json.loads(path.read_text(encoding="utf-8"))
               for name, path in names.items()}
    sources = hashes(source_paths())
    for name in ("examples", "development", "challenge"):
        if reports[name].get("target_met") is not True:
            raise ValueError(f"{name} compatibility gate has not passed")
    for name in ("examples", "gold"):
        for relative, digest in reports[name]["source_sha256"].items():
            normalized = relative.replace("\\", "/")
            if sources.get(normalized) != digest:
                raise ValueError(f"{name} report uses stale source: {normalized}")
    for name in ("development", "challenge"):
        for relative, digest in reports[name]["implementation_sha256"].items():
            if sources.get(relative) != digest:
                raise ValueError(f"{name} report uses stale source: {relative}")
        if (reports[name]["full_manifest_missing_statuses"]
                or reports[name]["full_manifest_failure_statuses"]):
            raise ValueError(f"{name} reference coverage incomplete")
    data = hashes(data_paths())
    for name in ("development", "challenge"):
        for filename, digest in reports[name]["word_data_sha256"].items():
            relative = "BioC_C++_1.1/BioC-APPL-ABBR/WordData/" + filename
            if data.get(relative) != digest:
                raise ValueError(f"{name} report uses stale WordData: {filename}")
    return {name: {"path": path.relative_to(ROOT).as_posix(), "sha256": sha(path)}
            for name, path in names.items()}


def main() -> None:
    history = REPORTS / "reserve_use_history.jsonl"
    if history.exists() and history.stat().st_size:
        raise RuntimeError("Reserve was already opened; this freeze cannot be replaced")
    if FREEZE.exists():
        raise RuntimeError("A reserve code freeze already exists; inspect it before replacement")
    failed = json.loads(FAILED_FINAL.read_text(encoding="utf-8"))
    if (failed.get("status") != "frozen-evaluation" or failed.get("target_met") is not False
            or failed.get("holdout_python_inspected") is not True):
        raise RuntimeError("The first final holdout failure is not recorded")
    input_freeze_sha = check_input_freeze()
    reports = check_baselines()
    command = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests"]
    tested = subprocess.run(command, cwd=ROOT, capture_output=True,
                            text=True, check=False)
    if tested.returncode:
        raise RuntimeError("Test suite failed:\n" +
                           (tested.stdout + tested.stderr)[-3000:])
    record = {"frozen_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "target": 0.999, "holdout_python_inspected": False,
              "retired_first_final_report_sha256": sha(FAILED_FINAL),
              "reserve_input_freeze_sha256": input_freeze_sha,
              "python": sys.version, "platform": platform.platform(),
              "source_sha256": hashes(source_paths()),
              "word_data_sha256": hashes(data_paths()),
              "baseline_reports": reports,
              "test_command": "python -m pytest -q -p no:cacheprovider tests",
              "test_output": tested.stdout.strip(), "test_exit_code": tested.returncode}
    FREEZE.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Frozen {len(record['source_sha256'])} source/test files and "
          f"{len(record['word_data_sha256'])} data files at {FREEZE}")
    print(record["test_output"])


if __name__ == "__main__":
    main()
