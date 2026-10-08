"""Create a separate, versioned holdout expansion from frozen draw continuations.

No Python abbreviation predictions enter selection. The original bundle and
selection log are read only. Public BioC retrieval needs network access.
"""

from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import time

try:
    from . import prepare
except ImportError:
    import prepare

ROOT = Path(__file__).resolve().parents[1]
ADDENDUM = ROOT / "corpus/holdout_expansion_v1.json"
PARENT = ROOT / "evaluation/representative_v1"
PARENT_CACHE = ROOT / "evaluation/representative_v1_cache"
CACHE = ROOT / "evaluation/representative_v1_expansion_v1_cache"
BUNDLE = ROOT / "evaluation/representative_v1_expansion_v1"
CROSSREF = PARENT_CACHE / "metadata/PMC-ids.csv.gz"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_addendum() -> dict:
    spec = json.loads(ADDENDUM.read_text(encoding="utf-8"))
    if sha(PARENT / "manifests/inputs.jsonl") != spec["parent_input_manifest_sha256"]:
        raise RuntimeError("Parent input manifest changed")
    if sha(PARENT_CACHE / "selection.jsonl") != spec["parent_retrieval_log_sha256"]:
        raise RuntimeError("Parent retrieval log changed")
    if sha(CROSSREF) != spec["pmc_crossref_sha256"]:
        raise RuntimeError("Pinned PMC cross-reference changed")
    parent = json.loads((PARENT / "protocol.json").read_text(encoding="utf-8"))
    for field in ("seed", "sources", "frames", "batching", "shards"):
        if field == "frames":
            values = {kind: {"id_range_inclusive": row["id_range_inclusive"]}
                      for kind, row in parent[field].items()}
        elif field == "shards":
            values = {"pubmed_documents": parent[field]["pubmed_documents"],
                      "pmc_documents": parent[field]["pmc_documents"]}
        else:
            values = parent[field]
        if spec[field] != values:
            raise RuntimeError(f"Expansion changes frozen {field}")
    latest = {}
    for row in prepare.load_log(PARENT_CACHE / "selection.jsonl"):
        latest[row["cohort"]] = max(latest.get(row["cohort"], -1), row["ordinal"])
    for cohort, rule in spec["continuation"].items():
        if rule["first_ordinal"] != latest[cohort] + 1:
            raise RuntimeError(f"Incorrect {cohort} continuation ordinal")
    return spec


def family_keys(row: dict) -> set[str]:
    return set(row.get("family_keys", [])) or prepare.family_keys(row["identifiers"])


def existing_keys() -> set[str]:
    blocked = set(json.loads((PARENT / "manifests/excluded_family_keys.json")
                             .read_text(encoding="utf-8"))["keys"])
    for row in prepare.load_log(PARENT / "manifests/articles.jsonl"):
        blocked.update(family_keys(row))
    # Propagate the pinned PMC ID cross-reference through existing families.
    links = prepare.load_log(PARENT / "manifests/family_links.jsonl")
    changed = True
    while changed:
        changed = False
        for row in links:
            keys = link_keys(row)
            if keys & blocked and not keys <= blocked:
                blocked.update(keys)
                changed = True
    return blocked


def link_keys(row: dict) -> set[str]:
    keys = set()
    if row.get("pmid"):
        keys.add("pmid:" + str(int(row["pmid"])))
    if row.get("pmcid"):
        numeric = row["pmcid"].upper().removeprefix("PMC")
        if numeric.isdigit():
            keys.add("pmcid:PMC" + str(int(numeric)))
    if row.get("doi"):
        keys.add("doi:" + prepare.norm_doi(row["doi"]))
    return keys


def family_status(keys: set[str], blocked: set[str], same_cohort: set[str]) -> str:
    """Apply frozen exclusions before accepting a new holdout family."""
    if keys & blocked:
        return "existing_or_excluded_family"
    if keys & same_cohort:
        return "duplicate_new_family"
    return "selected"


def validate_selection_log(spec: dict, rows: list[dict]) -> None:
    """Reject stale, truncated or reordered continuation records on resume."""
    expected_hash = sha(ADDENDUM)
    counts = collections.Counter()
    seen_pmc = False
    for row in rows:
        cohort = row["cohort"]
        if cohort not in ("pubmed", "pmc"):
            raise RuntimeError("Unknown expansion cohort")
        if cohort == "pmc":
            seen_pmc = True
        elif seen_pmc:
            raise RuntimeError("PubMed draw after PMC continuation began")
        rule = spec["continuation"][cohort]
        ordinal = rule["first_ordinal"] + counts[cohort]
        if (row.get("protocol_sha256") != expected_hash or row["ordinal"] != ordinal
                or row["id"] != prepare.candidate(cohort, ordinal, spec)):
            raise RuntimeError(f"Stale or misordered expansion draw: {cohort} {ordinal}")
        counts[cohort] += 1
        if counts[cohort] > rule["maximum_draws"]:
            raise RuntimeError(f"Expansion draw window exceeded: {cohort}")


def crossref_maps(spec: dict) -> dict[str, dict[str, list[dict]]]:
    cache_path = CACHE / "crossref_links.json"
    spec_hash = sha(ADDENDUM)
    if cache_path.exists():
        saved = json.loads(cache_path.read_text(encoding="utf-8"))
        if saved["protocol_sha256"] != spec_hash or saved["source_sha256"] != spec["pmc_crossref_sha256"]:
            raise RuntimeError("Stale expansion cross-reference map")
        return saved["links"]
    wanted = {}
    for cohort in ("pubmed", "pmc"):
        rule = spec["continuation"][cohort]
        wanted[cohort] = {str(prepare.candidate(cohort, ordinal, spec)) for ordinal in
                          range(rule["first_ordinal"], rule["first_ordinal"] + rule["maximum_draws"])}
    links: dict[str, dict[str, list[dict]]] = {"pubmed": {}, "pmc": {}}
    with gzip.open(CROSSREF, "rt", encoding="utf-8", newline="") as stream:
        for source in csv.DictReader(stream):
            pmid = (source.get("PMID") or source.get("pmid") or "").strip()
            pmcid = (source.get("PMCID") or source.get("pmcid") or "").strip()
            numeric_pmcid = pmcid.upper().removeprefix("PMC")
            row = {"pmid": pmid, "pmcid": pmcid,
                   "doi": prepare.norm_doi((source.get("DOI") or source.get("doi") or "").strip())}
            if pmid in wanted["pubmed"]:
                links["pubmed"].setdefault(pmid, []).append(row)
            if numeric_pmcid in wanted["pmc"]:
                links["pmc"].setdefault(numeric_pmcid, []).append(row)
    CACHE.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps({"protocol_sha256": spec_hash,
                                      "source_sha256": spec["pmc_crossref_sha256"],
                                      "links": links}, sort_keys=True) + "\n", encoding="utf-8")
    return links


def collect(spec: dict, limit_draws: int | None, gap_seconds: float) -> None:
    prepare.CACHE = CACHE
    blocked = existing_keys()
    crossref = crossref_maps(spec)
    log_path = CACHE / "selection.jsonl"
    rows = prepare.load_log(log_path)
    fingerprint = sha(ADDENDUM)
    validate_selection_log(spec, rows)
    selected = collections.Counter(row["cohort"] for row in rows if row["status"] == "selected")
    new_by_cohort = {"pubmed": set(), "pmc": set()}
    for row in rows:
        if row["status"] == "selected":
            new_by_cohort[row["cohort"]].update(row["family_keys"])
    attempts_by_cohort = collections.Counter(row["cohort"] for row in rows)
    clock = [0.0]
    batches: dict = {}
    known_batch_hashes = {(row["cohort"], row["batch"]["start_ordinal"]):
                          row["batch"]["raw_batch_sha256"] for row in rows
                          if row.get("batch") and row["batch"].get("raw_batch_sha256")}
    draws = 0
    for cohort in ("pubmed", "pmc"):
        rule = spec["continuation"][cohort]
        target = spec["allocation"][0][cohort]
        while selected[cohort] < target:
            if limit_draws is not None and draws >= limit_draws:
                print(f"Paused after {draws} new draws; selected={dict(selected)}", flush=True)
                return
            if attempts_by_cohort[cohort] >= rule["maximum_draws"]:
                raise RuntimeError(f"Predeclared {cohort} continuation window exhausted")
            ordinal = rule["first_ordinal"] + attempts_by_cohort[cohort]
            ident = prepare.candidate(cohort, ordinal, spec)
            attempts_by_cohort[cohort] += 1
            draws += 1
            row = {"cohort": cohort, "id": ident, "ordinal": ordinal,
                   "partition": "holdout", "protocol_sha256": fingerprint,
                   "at_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
            primary = ("pmid:" if cohort == "pubmed" else "pmcid:PMC") + str(ident)
            preliminary = family_status({primary}, blocked, new_by_cohort[cohort])
            if preliminary != "selected":
                row["status"] = preliminary
            else:
                data, attempts, batch = prepare.fetch_sample(
                    cohort, ident, ordinal, spec, gap_seconds, clock, batches)
                row["attempts"] = attempts
                if batch is not None:
                    row["batch"] = batch
                    batch_key = cohort, batch["start_ordinal"]
                    old = known_batch_hashes.get(batch_key)
                    if old and old != batch["raw_batch_sha256"]:
                        raise RuntimeError(f"Raw BioC batch changed on resume: {batch_key}")
                    known_batch_hashes[batch_key] = batch["raw_batch_sha256"]
                if data is None:
                    row["status"] = ("api_no_result" if batch and batch["raw_batch_sha256"]
                                     else "retrieval_failed")
                else:
                    row["raw_sha256"] = prepare.digest(data)
                    row["raw_bytes"] = len(data)
                    source, info = prepare.parse_source(data, cohort, ident)
                    row.update(info)
                    if source is not None:
                        links = crossref[cohort].get(str(ident), [])
                        keys = prepare.family_keys(info["identifiers"])
                        for link in links:
                            keys.update(link_keys(link))
                        row["status"] = family_status(keys, blocked, new_by_cohort[cohort])
                        if row["status"] == "selected":
                            row["family_keys"] = sorted(keys)
                            row["crossref_links"] = links
                            new_by_cohort[cohort].update(keys)
                            selected[cohort] += 1
            prepare.append_log(log_path, row)
            if draws % 100 == 0:
                print(f"{cohort} draw {ordinal}: {selected[cohort]}/{target}", flush=True)
    print(f"Expansion quotas filled: {dict(selected)}", flush=True)


def build(spec: dict) -> None:
    if BUNDLE.exists():
        raise RuntimeError("Versioned expansion bundle exists; never overwrite it")
    rows = prepare.load_log(CACHE / "selection.jsonl")
    validate_selection_log(spec, rows)
    selected = {cohort: [row for row in rows if row["cohort"] == cohort
                         and row["status"] == "selected"] for cohort in ("pubmed", "pmc")}
    if any(len(selected[cohort]) != spec["allocation"][0][cohort]
           for cohort in selected):
        raise RuntimeError("Expansion quotas incomplete")
    staging = BUNDLE.with_name(BUNDLE.name + "_staging")
    if staging.exists():
        raise RuntimeError(f"Staging exists: {staging}")
    staging.mkdir(parents=True)
    shutil.copy2(ADDENDUM, staging / "protocol.json")
    (staging / "manifests").mkdir()
    (staging / "runner").mkdir()
    (staging / "reference_cpp").mkdir()
    for name in ("run_reference.py", "validate_bundle.py"):
        shutil.copy2(PARENT / "runner" / name, staging / "runner" / name)
    input_rows = []
    article_rows = []
    for cohort in ("pubmed", "pmc"):
        size = spec["shards"][cohort + "_documents"]
        for start in range(0, len(selected[cohort]), size):
            shard = start // size + 1
            name = f"{cohort}_{'tiab' if cohort == 'pubmed' else 'full'}_expansion_{shard:05d}.xml"
            rel = f"input/holdout/{name}"
            docs = []
            local = []
            for row in selected[cohort][start:start + size]:
                raw = prepare.raw_path(cohort, row["id"])
                data = raw.read_bytes()
                if prepare.digest(data) != row["raw_sha256"]:
                    raise RuntimeError(f"Raw source changed: {raw}")
                source, info = prepare.parse_source(data, cohort, row["id"])
                if source is None:
                    raise RuntimeError(f"Selected source became invalid: {row['id']}: {info}")
                doc, passages = prepare.canonical_document(source, cohort)
                docs.append(doc)
                local.append((row, passages, doc.findtext("id", ""), info))
            file_hash = prepare.write_xml(staging / rel, docs)
            for index, (row, passages, docid, info) in enumerate(local):
                article_rows.append({"cohort": cohort, "partition": "holdout",
                                     "document_id": docid, "id": row["id"],
                                     "family_keys": row["family_keys"],
                                     "identifiers": row["identifiers"],
                                     "file": rel, "index": index,
                                     "draw_ordinal": row["ordinal"],
                                     "raw_sha256": row["raw_sha256"],
                                     "license": info["license"],
                                     "license_statements": info["license_statements"],
                                     "passage_types": info["passage_types"],
                                     "year": info["year"], "publisher": info["publisher"]})
                input_rows.append({"cohort": cohort, "partition": "holdout",
                                   "document_id": docid, "file": rel,
                                   "file_sha256": file_hash, "index": index,
                                   "passages": passages})
    def write_jsonl(name: str, values: list[dict]) -> None:
        (staging / "manifests" / name).write_text(
            "".join(prepare.jd(value) + "\n" for value in values), encoding="utf-8", newline="\n")
    write_jsonl("inputs.jsonl", input_rows)
    write_jsonl("articles.jsonl", article_rows)
    write_jsonl("retrieval.jsonl", rows)
    links = {(link.get("pmid", ""), link.get("pmcid", ""), link.get("doi", "")):
             link for row in rows if row["status"] == "selected"
             for link in row.get("crossref_links", []) if link.get("pmid")}
    write_jsonl("family_links.jsonl", list(links.values()))
    (staging / "manifests/excluded_family_keys.json").write_text(
        json.dumps({"keys": sorted(existing_keys()),
                    "source": "parent selected families and supplied example/gold exclusions"},
                   indent=2) + "\n", encoding="utf-8")
    handoff = ("# Versioned primary holdout expansion\n\n"
               "This input is separate from the frozen representative_v1 bundle. "
               "The expansion was selected from unused parent permutations without "
               "Python predictions. Preserve all input bytes.\n\n"
               "Verify the archive sidecar, unpack, and from this directory run:\n\n"
               "    python3 runner/validate_bundle.py --corpus . --stage input\n"
               "    sha256sum /absolute/path/to/BioC_C++_1.1/BioC-APPL-ABBR/abbr\n"
               "    python3 runner/run_reference.py --corpus . --abbr-app /absolute/path/to/BioC_C++_1.1/BioC-APPL-ABBR --timeout-seconds 300\n"
               "    python3 runner/validate_bundle.py --corpus . --stage reference\n\n"
               f"The executable SHA-256 must equal {spec['required_executable_sha256']}. "
               "Return the complete reference_cpp tree. Record MEDPOST_HOME, "
               "path_medpost, compiled MedPost default, compiler, flags and patches. "
               "Do not compare Python on this expansion until the evaluator and "
               "implementation are frozen; its records are part of the primary holdout.\n")
    (staging / "HANDOFF.md").write_text(handoff, encoding="utf-8")
    files = sorted(path for path in staging.rglob("*") if path.is_file())
    (staging / "manifests/files.sha256").write_text(
        "".join(f"{sha(path)}  {path.relative_to(staging).as_posix()}\n" for path in files),
        encoding="utf-8")
    staging.replace(BUNDLE)
    print(f"Built {len(input_rows)} expansion documents at {BUNDLE}")


def package() -> None:
    if not BUNDLE.exists():
        raise RuntimeError("Build and validate the expansion before packaging")
    if any((BUNDLE / "reference_cpp").rglob("*")):
        raise RuntimeError("Input transfer package must not include returned C++ output")
    archive = BUNDLE.with_name(BUNDLE.name + ".input.tar.gz")
    if archive.exists():
        raise RuntimeError("Expansion archive exists; never overwrite")
    with tarfile.open(archive, "w:gz") as stream:
        stream.add(BUNDLE, arcname=BUNDLE.name)
    archive.with_name(archive.name + ".sha256").write_text(
        f"{sha(archive)}  {archive.name}\n", encoding="utf-8")
    print(f"Packaged {archive}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("links", "collect", "build", "package"))
    parser.add_argument("--limit-draws", type=int)
    parser.add_argument("--gap-seconds", type=float, default=1.5)
    args = parser.parse_args()
    if args.limit_draws is not None and args.limit_draws < 0:
        parser.error("--limit-draws must be nonnegative")
    if args.gap_seconds < 1.5:
        parser.error("--gap-seconds must be at least 1.5")
    spec = load_addendum()
    if args.action == "links":
        links = crossref_maps(spec)
        print({cohort: len(values) for cohort, values in links.items()})
    elif args.action == "collect":
        collect(spec, args.limit_draws, args.gap_seconds)
    elif args.action == "build":
        prepare.CACHE = CACHE
        build(spec)
    else:
        package()


if __name__ == "__main__":
    main()
