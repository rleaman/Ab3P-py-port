"""Cache NCBI's PMC ID cross-reference and extract links for sampled PMIDs."""
from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path
import time
import urllib.request

try:
    from .prepare import CACHE, digest
except ImportError:  # direct: python corpus/family_index.py
    from prepare import CACHE, digest

URL = "https://ftp.ncbi.nlm.nih.gov/pub/pmc/PMC-ids.csv.gz"
DEST = CACHE / "metadata/PMC-ids.csv.gz"


def download() -> Path:
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if DEST.exists() and (DEST.with_suffix(".json")).exists():
        known = json.loads(DEST.with_suffix(".json").read_text(encoding="utf-8"))
        if digest(DEST.read_bytes()) == known["sha256"]:
            return DEST
    partial = DEST.with_suffix(".part")
    for attempt in range(1, 6):
        offset = partial.stat().st_size if partial.exists() else 0
        headers = {"User-Agent": "Ab3P-representative-v1/1.0"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        try:
            with urllib.request.urlopen(urllib.request.Request(URL, headers=headers), timeout=90) as response:
                mode = "ab" if offset and response.status == 206 else "wb"
                with partial.open(mode) as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
                last_modified = response.headers.get("Last-Modified")
                expected = response.headers.get("Content-Length")
            with gzip.open(partial, "rb") as stream:
                stream.read(1024)
            partial.replace(DEST)
            record = {"url": URL, "bytes": DEST.stat().st_size, "sha256": digest(DEST.read_bytes()),
                      "last_modified": last_modified, "content_length_last_response": expected}
            DEST.with_suffix(".json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
            return DEST
        except (OSError, EOFError) as exc:
            if attempt == 5:
                raise
            time.sleep(min(60, 2 ** attempt))
    raise RuntimeError("unreachable")


def links_for(pmids: set[str]) -> dict[str, list[dict[str, str]]]:
    path = download()
    found: dict[str, list[dict[str, str]]] = {}
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            pmid = (row.get("PMID") or row.get("pmid") or "").strip()
            if pmid in pmids:
                record = {"pmcid": (row.get("PMCID") or row.get("pmcid") or "").strip(),
                          "doi": (row.get("DOI") or row.get("doi") or "").strip().lower()}
                if record not in found.setdefault(pmid, []):
                    found[pmid].append(record)
    return found


def links_for_pmcids(pmcids: set[str]) -> dict[str, list[dict[str, str]]]:
    path = download()
    found: dict[str, list[dict[str, str]]] = {}
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            pmcid = (row.get("PMCID") or row.get("pmcid") or "").strip()
            if pmcid in pmcids:
                record = {"pmid": (row.get("PMID") or row.get("pmid") or "").strip(),
                          "doi": (row.get("DOI") or row.get("doi") or "").strip().lower()}
                if record not in found.setdefault(pmcid, []):
                    found[pmcid].append(record)
    return found
