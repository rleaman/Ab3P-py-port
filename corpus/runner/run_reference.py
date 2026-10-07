#!/usr/bin/env python3
"""Run the pinned Ab3P BioC application on a frozen input bundle.

Standard-library only. This script records execution evidence; it does not
measure agreement with Python.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import locale
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    return sha(path.read_bytes())


def dump(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def append(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(obj, sort_keys=True, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def tree_hash(path: Path) -> dict:
    if not path.exists():
        return {"status": "unknown", "reason": "path absent", "path": str(path)}
    files = sorted(p for p in path.rglob("*") if p.is_file())
    if not files:
        return {"path": str(path.resolve()), "status": "unknown", "reason": "directory contains no files"}
    listing = {p.relative_to(path).as_posix(): file_sha(p) for p in files}
    return {"path": str(path.resolve()), "sha256": sha(json.dumps(listing, sort_keys=True).encode()), "files": listing}


def source_hash(path: Path) -> dict:
    suffixes = {".cpp", ".c", ".C", ".h", ".hpp"}
    files = sorted(p for p in path.rglob("*") if p.is_file()
                   and (p.suffix in suffixes or p.name == "Makefile"))
    if not files:
        return {"path": str(path.resolve()), "status": "unknown", "reason": "no source files found"}
    listing = {p.relative_to(path).as_posix(): file_sha(p) for p in files}
    return {"path": str(path.resolve()), "sha256": sha(json.dumps(listing, sort_keys=True).encode()),
            "files": listing}


def input_files(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(row["file"], []).append(row)
    return grouped


def parse_output(data: bytes, expected: list[dict]) -> tuple[bool, str]:
    try:
        data.decode("utf-8", errors="strict")
        root = ET.fromstring(data)
    except UnicodeDecodeError as exc:
        return False, "invalid_utf8:" + str(exc)
    except ET.ParseError as exc:
        return False, "invalid_xml:" + str(exc)
    docs = root.findall("document")
    if root.tag != "collection" or len(docs) != len(expected):
        return False, "document_count_or_root_mismatch"
    for doc, row in zip(docs, expected):
        if doc.findtext("id") != row["document_id"]:
            return False, "document_id_mismatch"
        passages = doc.findall("passage")
        if len(passages) != len(row["passages"]):
            return False, "passage_count_mismatch"
        for passage, provenance in zip(passages, row["passages"]):
            if passage.findtext("offset") != str(provenance["canonical_offset"]):
                return False, "passage_offset_mismatch"
    return True, "ok"


def singleton_xml(source: Path, index: int, output: Path) -> None:
    root = ET.parse(source).getroot()
    docs = root.findall("document")
    if index >= len(docs):
        raise ValueError("Index beyond input shard")
    selected = docs[index]
    for doc in docs:
        root.remove(doc)
    root.append(selected)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True).replace(b"\r", b"&#13;"))


def execute(app: Path, inp: Path, out: Path, err: Path, timeout: int,
            attempts: Path, group: str, index: int | None, oracle: str,
            expected: list[dict]) -> tuple[bool, str, str | None]:
    # Avoid reading bytes from stdout through a shell or treating empty stdout as success.
    command = [str((app / "abbr").resolve()), str(inp.resolve())]
    out.parent.mkdir(parents=True, exist_ok=True)
    err.parent.mkdir(parents=True, exist_ok=True)
    started = dt.datetime.now(dt.timezone.utc).isoformat()
    attempt_tag = str(time.time_ns())
    err = err.with_name(err.stem + "." + attempt_tag + err.suffix)
    start = time.monotonic()
    reason = ""
    stdout = b""
    try:
        result = subprocess.run(command, cwd=app, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=timeout, check=False)
        stdout = result.stdout
        err.write_bytes(result.stderr)
        reason = "exit_" + str(result.returncode)
        good = result.returncode == 0
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or b""
        err.write_bytes(exc.stderr or b"")
        reason, good = "timeout", False
    except OSError as exc:
        err.write_text(str(exc), encoding="utf-8")
        reason, good = "exec_error:" + str(exc), False
    if good:
        good, parse_reason = parse_output(stdout, expected)
        if not good:
            reason = parse_reason
    if good:
        tmp = out.with_suffix(out.suffix + ".tmp")
        tmp.write_bytes(stdout)
        tmp.replace(out)
    else:
        out.with_suffix(out.suffix + "." + attempt_tag + ".failed").write_bytes(stdout)
    append(attempts, {"at_utc": started, "elapsed_seconds": round(time.monotonic() - start, 3),
                      "group": group, "input_index": index, "command": command,
                      "cwd": str(app), "input_sha256": file_sha(inp),
                      "oracle_fingerprint": oracle, "status": "success" if good else "failed",
                      "reason": reason, "stdout_bytes": len(stdout), "stdout_sha256": sha(stdout),
                      "stderr_path": str(err), "stderr_sha256": file_sha(err),
                      "output_path": str(out) if good else None})
    return good, reason, sha(stdout) if good else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", required=True, type=Path)
    parser.add_argument("--abbr-app", required=True, type=Path)
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--retries", type=int, default=1)
    args = parser.parse_args()
    corpus = args.corpus.resolve()
    app = args.abbr_app.resolve()
    executable = app / "abbr"
    if not executable.is_file():
        parser.error(f"Missing executable: {executable}")
    rows = read_jsonl(corpus / "manifests/inputs.jsonl")
    if not rows:
        parser.error("No input manifest")
    ref = corpus / "reference_cpp"
    ref.mkdir(exist_ok=True)
    manifest_hash = file_sha(corpus / "manifests/inputs.jsonl")
    source = source_hash(app.parent)
    path_config = app / "path_Ab3P"
    path_value = path_config.read_text(errors="replace").strip() if path_config.exists() else "./WordData/"
    word_data_path = Path(path_value)
    if not word_data_path.is_absolute():
        word_data_path = (app / word_data_path).resolve()
    data = tree_hash(word_data_path)
    medpost = tree_hash(app.parent / "MedPost")
    oracle_info = {"executable": str(executable), "executable_sha256": file_sha(executable),
                   "source": source, "word_data": data, "medpost": medpost,
                   "path_Ab3P_sha256": file_sha(path_config) if path_config.exists() else None,
                   "input_manifest_sha256": manifest_hash,
                   "platform": platform.platform(), "python": sys.version,
                   "locale": locale.setlocale(locale.LC_ALL, None),
                   "environment": {key: os.environ.get(key) for key in
                                   ("LANG", "LC_ALL", "LC_CTYPE", "TZ", "LD_LIBRARY_PATH")},
                   "path_sha256": sha(os.environ.get("PATH", "").encode("utf-8")),
                   "invocation": "./abbr /absolute/path/to/input.xml",
                   "cwd": str(app), "build_flags": {"status": "unknown", "reason": "not supplied by executable"},
                   "compiler": {"status": "unknown", "reason": "not supplied by executable"},
                   "runtime_data_paths": {"word_data": str(word_data_path),
                                          "medpost": str(app.parent / "MedPost"),
                                          "path_Ab3P": path_value},
                   "portability_changes": {"status": "unknown", "reason": "inspect Linux installation"}}
    oracle = sha(json.dumps(oracle_info, sort_keys=True).encode())
    oracle_info["fingerprint"] = oracle
    run_path = ref / "run.json"
    if run_path.exists():
        previous = json.loads(run_path.read_text(encoding="utf-8"))
        if previous.get("fingerprint") != oracle:
            parser.error("Existing reference_cpp fingerprint differs; use a new result directory")
    else:
        dump(run_path, oracle_info)
    build_note = ref / "build_provenance.json"
    if not build_note.exists():
        dump(build_note, {
            "compiler": {"status": "unknown", "reason": "record from Linux build or existing installation"},
            "build_flags": {"status": "unknown", "reason": "record from Linux build or existing installation"},
            "source_patches": {"status": "unknown", "reason": "compare installation against bundled source"},
            "qualification_notes": "pending comparison with sanity_expected",
        })
    attempts = ref / "runs.jsonl"
    terminal_path = ref / "documents.jsonl"
    journal_path = ref / "documents.journal.jsonl"
    terminal = {(r["input_path"], r["input_index"]): r
                for r in read_jsonl(terminal_path) + read_jsonl(journal_path)}
    invalidated_prior_validation = False
    output_hash_cache: dict[str, str | None] = {}

    def save_terminal() -> None:
        ordered = [terminal[key] for key in sorted(terminal)]
        tmp = terminal_path.with_suffix(".jsonl.tmp")
        tmp.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in ordered),
                       encoding="utf-8")
        tmp.replace(terminal_path)

    def completed(row: dict) -> bool:
        old = terminal.get((row["file"], row["index"]))
        if not old or old.get("status") != "success" or old.get("input_sha256") != row["file_sha256"]:
            return False
        rel = old.get("output_path")
        if not rel:
            return False
        if rel not in output_hash_cache:
            path = corpus / rel
            output_hash_cache[rel] = file_sha(path) if path.is_file() else None
        return output_hash_cache[rel] == old.get("output_sha256")
    for rel, group in sorted(input_files(rows).items()):
        group.sort(key=lambda r: r["index"])
        inp = corpus / rel
        if file_sha(inp) != group[0]["file_sha256"]:
            raise RuntimeError(f"Input changed: {inp}")
        pending = [r for r in group if not completed(r)]
        if not pending:
            continue
        if not invalidated_prior_validation:
            prior = [ref / "files.sha256", ref / "validation.json"]
            if any(path.exists() for path in prior):
                stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                history = ref / "history" / stamp
                history.mkdir(parents=True, exist_ok=False)
                for path in prior:
                    if path.exists():
                        shutil.move(str(path), str(history / path.name))
            invalidated_prior_validation = True
        outrel = rel.replace("input/", "reference_cpp/outputs/", 1)
        out = corpus / outrel
        err = ref / "stderr" / (Path(rel).stem + ".stderr")
        good = False
        for _ in range(args.retries + 1):
            good, reason, output_hash = execute(app, inp, out, err, args.timeout_seconds,
                                                  attempts, rel, None, oracle, group)
            if good:
                break
        if good:
            output_hash_cache[outrel] = output_hash
            for row in group:
                record = {"cohort": row["cohort"], "partition": row["partition"],
                          "document_id": row["document_id"], "input_path": rel,
                          "input_index": row["index"], "input_sha256": row["file_sha256"],
                          "output_path": outrel, "output_index": row["index"],
                          "output_sha256": output_hash, "status": "success"}
                append(journal_path, record)
                terminal[(rel, row["index"])] = record
            continue
        for row in pending:
            docid = row["document_id"]
            safeid = "".join(c for c in docid if c.isalnum() or c in "._-")
            one = ref / "recovered" / "inputs" / row["partition"] / f"{safeid}.xml"
            singleton_xml(inp, row["index"], one)
            one_out = ref / "recovered" / "outputs" / row["partition"] / f"{safeid}.xml"
            one_err = ref / "stderr" / row["partition"] / f"{safeid}.stderr"
            isolated = False
            isolated_reason = ""
            output_hash = None
            for _ in range(args.retries + 1):
                isolated, isolated_reason, output_hash = execute(
                    app, one, one_out, one_err, args.timeout_seconds, attempts,
                    rel, row["index"], oracle, [row])
                if isolated:
                    break
            record = {"cohort": row["cohort"], "partition": row["partition"],
                      "document_id": docid, "input_path": rel,
                      "input_index": row["index"], "input_sha256": row["file_sha256"],
                      "output_path": one_out.relative_to(corpus).as_posix() if isolated else None,
                      "output_index": 0 if isolated else None, "output_sha256": output_hash,
                      "status": "success" if isolated else "failed",
                      "reason": None if isolated else isolated_reason}
            append(journal_path, record)
            terminal[(rel, row["index"])] = record
            if isolated and output_hash:
                output_hash_cache[record["output_path"]] = output_hash
        print(f"Isolated failed shard {rel}", flush=True)
    # The fsynced journal supports resume after interruption; compact once.
    save_terminal()
    print(f"Recorded {len(terminal)} document statuses in {terminal_path}")


if __name__ == "__main__":
    main()
