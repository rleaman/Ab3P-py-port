"""Profile a declared development PMC shard without opening protected splits."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import tracemalloc
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ab3p.algorithm import Ab3P


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def profile(input_path: Path, limit_documents: int) -> dict:
    if limit_documents < 1:
        raise ValueError("limit_documents must be positive")
    approved = (ROOT / "evaluation/representative_v1/input/development").resolve()
    if not input_path.resolve().is_relative_to(approved):
        raise ValueError("profile input must be in the development partition")
    detector = Ab3P()
    root = ET.parse(input_path).getroot()
    durations = []
    document_count = passage_count = occurrence_count = character_count = 0
    tracemalloc.start()
    started = time.perf_counter()
    for document in root.findall("document")[:limit_documents]:
        document_count += 1
        for index, passage in enumerate(document.findall("passage")):
            value = passage.findtext("text", "")
            begin = time.perf_counter()
            predictions = detector.find(value, int(passage.findtext("offset", "0")))
            seconds = time.perf_counter() - begin
            durations.append(dict(document_id=document.findtext("id"), passage_index=index,
                                  characters=len(value), seconds=seconds,
                                  predictions=len(predictions)))
            passage_count += 1
            occurrence_count += len(predictions)
            character_count += len(value)
    elapsed = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return dict(input=str(input_path.resolve()), input_sha256=sha(input_path),
                algorithm_sha256=sha(ROOT / "ab3p/algorithm.py"),
                documents=document_count, passages=passage_count,
                characters=character_count, predictions=occurrence_count,
                wall_seconds=elapsed, peak_tracemalloc_bytes=peak,
                slowest_passages=sorted(durations, key=lambda row: row["seconds"],
                                        reverse=True)[:10])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path,
                        default=ROOT / "evaluation/representative_v1/input/development/pmc_full_00001.xml")
    parser.add_argument("--limit-documents", type=int, default=20)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "evaluation/phase3_reports/profile_pmc_development.json")
    args = parser.parse_args()
    report = profile(args.input, args.limit_documents)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
