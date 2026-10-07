"""Finalize a complete representative_v1 bundle and portable input archive."""
from __future__ import annotations

import collections
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET

try:
    from .make_challenge import generate
    from .enrich_metadata import enrich
    from .prepare import BUNDLE, CACHE, ROOT, digest, infons, jd
    from .verify_archive import workspace_copy_dir
except ImportError:  # direct: python corpus/package.py
    from make_challenge import generate
    from enrich_metadata import enrich
    from prepare import BUNDLE, CACHE, ROOT, digest, infons, jd
    from verify_archive import workspace_copy_dir


def read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def file_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(jd(row) + "\n" for row in rows), encoding="utf-8", newline="\n")


def sanity_rows(bundle: Path) -> list[dict]:
    rows = []
    for source in sorted((ROOT / "examples/input").glob("*.xml")):
        rel = "input/sanity/" + source.name
        dest = bundle / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        expected_source = ROOT / "examples/reference_output" / source.name
        expected_dest = bundle / "sanity_expected" / source.name
        expected_dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(expected_source, expected_dest)
        if digest(dest.read_bytes()) != digest(source.read_bytes()):
            raise RuntimeError(f"Sanity input copy changed: {source.name}")
        if digest(expected_dest.read_bytes()) != digest(expected_source.read_bytes()):
            raise RuntimeError(f"Sanity reference copy changed: {source.name}")
        file_hash = digest(dest.read_bytes())
        xml = ET.parse(source).getroot()
        for index, doc in enumerate(xml.findall("document")):
            passages = []
            for pindex, passage in enumerate(doc.findall("passage")):
                value = passage.findtext("text", "")
                passages.append({"index": pindex,
                                 "canonical_offset": int(passage.findtext("offset", "0")),
                                 "source_offset": passage.findtext("offset"),
                                 "source_offset_unit": "supplied_sanity",
                                 "type": infons(passage).get("type"),
                                 "length_codepoints": len(value),
                                 "text_sha256": digest(value.encode("utf-8"))})
            rows.append({"cohort": "sanity", "partition": "sanity",
                         "document_id": doc.findtext("id", ""), "file": rel,
                         "file_sha256": file_hash, "index": index, "passages": passages})
    return rows


def manifest_hashes(bundle: Path) -> None:
    entries = []
    for path in sorted(bundle.rglob("*")):
        if not path.is_file() or "reference_cpp" in path.parts:
            continue
        rel = path.relative_to(bundle).as_posix()
        if rel == "manifests/files.sha256":
            continue
        entries.append(f"{digest(path.read_bytes())}  {rel}\n")
    (bundle / "manifests/files.sha256").write_text("".join(entries), encoding="utf-8", newline="\n")


def main() -> None:
    bundle = BUNDLE
    archive = bundle.parent / "representative_v1.input.tar.gz"
    archive_tmp = archive.with_suffix(archive.suffix + ".tmp")
    if not bundle.is_dir():
        raise SystemExit("Run corpus/prepare.py --build after all quotas are filled")
    if archive.exists():
        raise SystemExit("Archive already exists; version a revision")
    if archive_tmp.exists():
        raise SystemExit(f"Unfinished archive staging file exists: {archive_tmp}")
    if (bundle / "manifests/files.sha256").exists():
        raise SystemExit("Bundle already frozen; version a revision instead")
    if (bundle / "manifests/family_conflicts.json").exists():
        raise RuntimeError("Unresolved article-family conflicts; do not package")
    marker = bundle / "manifests/metadata_complete.json"
    if not marker.exists():
        enrich(bundle)
    completion = json.loads(marker.read_text(encoding="utf-8"))
    for name, expected in completion["sha256"].items():
        if digest((bundle / "manifests" / name).read_bytes()) != expected:
            raise RuntimeError(f"Metadata completion hash mismatch: {name}")
    shutil.copy2(ROOT / "corpus/protocol_v1_0.json",
                 bundle / "manifests/protocol_v1_0.json")
    shutil.copy2(ROOT / "corpus/protocol_v1_1.json",
                 bundle / "manifests/protocol_v1_1.json")
    link_path = CACHE / "metadata/selected_family_links.jsonl"
    if not link_path.exists():
        raise RuntimeError("Missing frozen PMC/PubMed family cross-reference")
    shutil.copy2(link_path, bundle / "manifests/family_links.jsonl")
    shutil.copy2(CACHE / "metadata/PMC-ids.csv.json",
                 bundle / "manifests/family_links_source.json")
    shutil.copy2(CACHE / "metadata/excluded_family_keys.json",
                 bundle / "manifests/excluded_family_keys.json")
    excluded_count = len(json.loads((bundle / "manifests/excluded_family_keys.json").read_text(
        encoding="utf-8")).get("keys", []))
    inputs = [r for r in read_rows(bundle / "manifests/inputs.jsonl")
              if r["partition"] in ("development", "holdout", "reserve")]
    articles = read_rows(bundle / "manifests/articles.jsonl")
    challenge, intents = generate(bundle)
    inputs += challenge + sanity_rows(bundle)
    write_rows(bundle / "manifests/inputs.jsonl", inputs)
    runner = bundle / "runner"
    runner.mkdir(exist_ok=True)
    for name in ("run_reference.py", "validate_bundle.py"):
        shutil.copy2(ROOT / "corpus/runner" / name, runner / name)
    version = {
        "git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                   capture_output=True, text=True).stdout.strip(),
        "code_sha256": {p.relative_to(ROOT).as_posix(): digest(p.read_bytes())
                        for p in sorted((ROOT / "corpus").rglob("*.py"))},
        "protocol_sha256": digest((bundle / "protocol.json").read_bytes()),
    }
    (bundle / "manifests/code.json").write_text(json.dumps(version, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (bundle / "reference_cpp").mkdir(exist_ok=True)
    counts = collections.Counter((r["partition"], r["cohort"]) for r in articles)
    years = collections.Counter((str(r.get("metadata", {}).get("pub_year") or r.get("year") or "missing")[:4] for r in articles))
    publishers = collections.Counter((r.get("metadata", {}).get("publisher") or r.get("publisher") or "missing" for r in articles))
    journals = collections.Counter((r.get("metadata", {}).get("journal") or "missing" for r in articles))
    article_types = collections.Counter(t for r in articles for t in r.get("metadata", {}).get("article_types", []))
    subjects = collections.Counter(t for r in articles for t in r.get("metadata", {}).get("subjects", []))
    missing_metadata = {
        "year": sum(not (r.get("metadata", {}).get("pub_year") or r.get("year")) for r in articles),
        "article_type": sum(not r.get("metadata", {}).get("article_types") for r in articles),
        "subject_mesh": sum(not r.get("metadata", {}).get("subjects") for r in articles),
        "publisher": sum(not (r.get("metadata", {}).get("publisher") or r.get("publisher")) for r in articles),
    }
    split_periods: dict[str, collections.Counter] = {}
    split_types: dict[str, collections.Counter] = {}
    split_subjects: dict[str, collections.Counter] = {}
    split_publishers: dict[str, collections.Counter] = {}
    for row in articles:
        split = row["partition"] + "/" + row["cohort"]
        year = str(row.get("metadata", {}).get("pub_year") or row.get("year") or "")[:4]
        period = str(int(year) // 10 * 10) + "s" if year.isdigit() else "missing"
        split_periods.setdefault(split, collections.Counter())[period] += 1
        split_types.setdefault(split, collections.Counter()).update(row.get("metadata", {}).get("article_types", []) or ["missing"])
        split_subjects.setdefault(split, collections.Counter()).update(row.get("metadata", {}).get("subjects", []) or ["missing"])
        split_publishers.setdefault(split, collections.Counter()).update(
            [row.get("metadata", {}).get("publisher") or row.get("publisher") or "missing"])
    unicode_docs = collections.Counter()
    by_file: dict[str, list[dict]] = {}
    for row in articles:
        by_file.setdefault(row["file"], []).append(row)
    for rel, subset in by_file.items():
        docs = ET.parse(bundle / rel).getroot().findall("document")
        for row in subset:
            if any(ord(char) > 127 for passage in docs[row["index"]].findall("passage")
                   for char in passage.findtext("text", "")):
                unicode_docs[row["partition"], row["cohort"]] += 1
    passage_types = collections.Counter(t for r in articles if r["cohort"] == "pmc" for t in r["passage_types"])
    special_passages = {
        "tables": sum(n for typ, n in passage_types.items() if "table" in typ.lower()),
        "captions": sum(n for typ, n in passage_types.items() if "caption" in typ.lower()),
        "references": sum(n for typ, n in passage_types.items()
                          if typ.lower() in ("ref", "reference") or typ.lower().startswith("ref_")),
        "supplements": sum(n for typ, n in passage_types.items() if "supp" in typ.lower()),
    }
    licenses = collections.Counter((r.get("license") or "missing" for r in articles if r["cohort"] == "pmc"))
    source_dates = collections.Counter((r.get("source_collection_date") or "missing" for r in articles))
    raw_bytes = sum(r["raw_bytes"] for r in articles)
    id_gaps = {
        cohort: {kind: sum(not r["identifiers"].get(kind) for r in articles if r["cohort"] == cohort)
                 for kind in ("pmid", "pmcid", "doi")}
        for cohort in ("pubmed", "pmc")}
    retrieval = read_rows(bundle / "manifests/retrieval.jsonl")
    status = collections.Counter(r["status"] for r in retrieval)
    duplicate_batch_ids = { (r["cohort"], r["batch"]["start_ordinal"]): r["batch"]["duplicate_returned_ids"]
                           for r in retrieval if r.get("batch", {}).get("duplicate_returned_ids") }
    source_responses = {}
    for row in retrieval:
        batch = row.get("batch")
        if batch and batch.get("raw_batch_sha256"):
            source_responses[batch["raw_batch_sha256"]] = batch["raw_batch_bytes"]
        elif row.get("raw_sha256"):
            source_responses[row["raw_sha256"]] = row.get("raw_bytes", 0)
    bioc_downloaded_bytes = sum(source_responses.values())
    draws = collections.Counter(r["cohort"] for r in retrieval)
    weights = {}
    for cohort, frame in json.loads((bundle / "protocol.json").read_text(encoding="utf-8"))["frames"].items():
        total = sum(counts[part, cohort] for part in ("development", "holdout", "reserve"))
        estimated_eligible = frame["id_range_inclusive"][1] * total / draws[cohort] if draws[cohort] else 0
        weights[cohort] = {"draws": draws[cohort], "selected": total,
                           "estimated_eligible_frame": round(estimated_eligible),
                           "by_partition": {
                               part: {"estimated_inclusion_probability": counts[part, cohort] / estimated_eligible if estimated_eligible else None,
                                      "estimated_inverse_probability_weight": estimated_eligible / counts[part, cohort] if counts[part, cohort] else None}
                               for part in ("development", "holdout", "reserve")}}
    cache_bytes = sum(p.stat().st_size for p in CACHE.rglob("*") if p.is_file())
    input_bytes = sum(p.stat().st_size for p in (bundle / "input").rglob("*.xml"))
    report = [
        "# Preparation report", "",
        "Snapshot/retrieval date: 2026-10-07 onward; exact attempt times are in manifests/retrieval.jsonl.",
        "Protocol: protocol.json. Source: NCBI Unicode BioC APIs listed there.",
        "Article-family cross-reference source URL, timestamp, size and SHA-256: manifests/family_links_source.json.",
        "PubMed abstract reuse rights can vary and are not supplied by the BioC response; the local transfer package is for the authorized reference run and is not a publication of article text.",
        "PMC BioC license labels are retained verbatim, including author_manuscript and NO-CC CODE where returned; a label alone is not a blanket redistribution grant. PMC describes author manuscripts as available for text mining and says OA reuse terms vary by article. See https://pmc.ncbi.nlm.nih.gov/tools/textmining/ and https://pmc.ncbi.nlm.nih.gov/about/copyright/.",
        "Selection is by numeric identifier-frame probability sampling, independent of abbreviation output.", "",
        "No explicit strata were imposed: publication, MeSH, publisher and article-type metadata are not present for every numeric ID before BioC eligibility checks. Random identifier ordering samples eligible records proportionally in expectation; realized coverage is audited below.",
        "## Counts", "",
        "| Partition | PubMed title/abstract | PMC full text |",
        "| --- | ---: | ---: |",
    ]
    for part in ("development", "holdout", "reserve"):
        report.append(f"| {part} | {counts[part, 'pubmed']} | {counts[part, 'pmc']} |")
    report += ["", f"Challenge cases: {len(intents)}. Sanity XML files: {len(list((bundle / 'input/sanity').glob('*.xml')))}.",
               f"Selected derived source-document bytes: {raw_bytes:,}. Unique BioC response bytes: {bioc_downloaded_bytes:,}.",
               f"Total local cache bytes: {cache_bytes:,}; cache stays outside the archive.",
               f"Input XML bytes: {input_bytes:,}.",
               f"Input-manifest SHA-256: {digest((bundle / 'manifests/inputs.jsonl').read_bytes())}.",
               "Preparation code and protocol hashes: manifests/code.json.",
               "The actual compressed archive byte count and SHA-256 are reported by corpus/package.py and written to the adjacent .sha256 sidecar after this report is sealed.",
               "", "## Retrieval status", "", "All sampled draws, including rejected and failed attempts, appear in manifests/retrieval.jsonl.",
               "Status counts: " + jd(status), "",
               f"Supplied example/gold exclusion identifiers (including linked aliases): {excluded_count:,}.",
               "Identifier gaps by cohort: " + jd(id_gaps),
               "Duplicate-family draws: " + str(status.get("duplicate_article_family", 0)) + ".", "",
               "Byte-identical duplicate documents returned within BioC batches: "
               + str(sum(len(ids) for ids in duplicate_batch_ids.values())) + ".", "",
               "## Sampling probabilities and weights", "",
               "For the frozen random identifier ordering, the selected fraction among draws estimates eligible-frame density.",
               "These are estimated marginal probabilities; family exclusions and PMC linked-family assignment can alter them.",
               jd(weights), "",
               "## Coverage", "", "Publication-year counts: " + jd(years),
               "Publisher counts (top 50; missing retained): " + jd(dict(publishers.most_common(50))),
               "Journal counts (top 50; reported separately where publisher is missing): " + jd(dict(journals.most_common(50))),
               "Article-type counts: " + jd(article_types),
               "MeSH subject counts (top 100): " + jd(dict(subjects.most_common(100))),
               "Missing metadata counts: " + jd(missing_metadata),
               "Publication period by partition/cohort: " + jd({k: dict(v) for k, v in split_periods.items()}),
               "Top article types by partition/cohort: " + jd({k: dict(v.most_common(20)) for k, v in split_types.items()}),
               "Top MeSH subjects by partition/cohort: " + jd({k: dict(v.most_common(20)) for k, v in split_subjects.items()}),
               "Top publishers by partition/cohort: " + jd({k: dict(v.most_common(20)) for k, v in split_publishers.items()}),
               "Documents containing non-ASCII text by partition/cohort: " + jd({f"{a}/{b}": n for (a, b), n in unicode_docs.items()}),
               "PMC passage-type counts: " + jd(passage_types),
               "PMC table/caption/reference/supplement passage counts from the main BioC response: " + jd(special_passages),
               "PMC license counts: " + jd(licenses), "",
               "BioC source collection dates: " + jd(source_dates), "",
               "## Limitations", "",
               "Source-producer offsets have unspecified units and are retained per passage; canonical inputs use code-point bases.",
               "Passage text is the XML parser's decoded text; no additional Unicode normalization, case conversion or whitespace processing is applied.",
               "Decoded carriage returns are serialized as XML character references so parsing the frozen input restores the same code point.",
               "The BioC conversion may omit table, caption, reference or supplement text present in publisher source.",
               "The manifest records all passage types actually retrieved. No unavailable type is claimed covered.",
               "Subject and article-type metadata can be absent from PubMed metadata or unavailable for articles without PMIDs; they are recorded as missing rather than inferred.",
               "Probability weights above estimate unknown eligible-frame sizes from draw acceptance; family linkage and missing metadata limit inferential use.", ""]
    (bundle / "reports/preparation.md").write_text("\n".join(report), encoding="utf-8")
    handoff = """# Linux reference handoff

The archive contains one top-level directory, representative_v1/. Python 3.10+
standard library is enough for the runner and validator. Keep the exact UTF-8 XML.
Inside are protocol.json, manifests/, reports/, runner/, input/development/,
input/holdout/, input/reserve/, input/challenge/, input/sanity/,
sanity_expected/, and an empty reference_cpp/. manifests/files.sha256 lists
immutable package-file SHA-256 values. The sidecar checks the archive bytes.

Copy representative_v1.input.tar.gz and representative_v1.input.tar.gz.sha256 to
Linux. From their directory run:

    sha256sum -c representative_v1.input.tar.gz.sha256
    tar -xzf representative_v1.input.tar.gz
    cd representative_v1
    python3 runner/validate_bundle.py --corpus . --stage input
    python3 runner/run_reference.py --corpus . --abbr-app /absolute/path/to/BioC_C++_1.1/BioC-APPL-ABBR --timeout-seconds 300
    python3 runner/validate_bundle.py --corpus . --stage reference

Use the bundled-source-compatible C++ executable and data. The runner invokes
./abbr with its application directory as cwd and records the executable, source,
WordData, MedPost, path_Ab3P and locale fingerprints in reference_cpp/run.json.
The bundled application Makefile uses xml2-config and links libxml2, libBioC
and libiret; the application directory must retain path_Ab3P and WordData,
and its parent must retain MedPost.
Compiler/build flags and patches unknown to the executable require a documented
supplement in reference_cpp/build_provenance.json. Fill in known build and patch
details before the final validation; leave an explicit unknown reason otherwise.
Qualify sanity outputs against sanity_expected before treating this Linux build
as the same reference target.

The run covers development, holdout, reserve, challenge and sanity. Do not use
holdout or reserve differences for repairs. Copy the entire reference_cpp/
directory back to evaluation/representative_v1/reference_cpp/ in this checkout.
Preserve failed attempts and statuses; a failed document is not a zero result.
"""
    (bundle / "HANDOFF.md").write_text(handoff, encoding="utf-8")
    manifest_hashes(bundle)
    check = subprocess.run([sys.executable, str(bundle / "runner/validate_bundle.py"),
                            "--corpus", str(bundle), "--stage", "input"], capture_output=True, text=True)
    if check.returncode:
        (bundle / "manifests/files.sha256").unlink(missing_ok=True)
        raise RuntimeError("Input validation failed: " + check.stdout + check.stderr)
    with archive_tmp.open("wb") as binary, gzip.GzipFile(filename="", mode="wb", fileobj=binary,
                                                      compresslevel=6, mtime=0) as compressed:
        with tarfile.open(fileobj=compressed, mode="w") as tar:
            for path in [bundle] + sorted(bundle.rglob("*")):
                if path.is_file() and "reference_cpp" in path.relative_to(bundle).parts:
                    continue
                name = Path("representative_v1") / path.relative_to(bundle)
                info = tar.gettarinfo(str(path), arcname=name.as_posix())
                info.uid = info.gid = 0
                info.uname = info.gname = ""
                info.mtime = 0
                info.mode = 0o644 if path.is_file() else 0o755
                if path.is_file():
                    with path.open("rb") as stream:
                        tar.addfile(info, stream)
                else:
                    tar.addfile(info)
    archive_tmp.replace(archive)
    sidecar = archive.with_suffix(archive.suffix + ".sha256")
    sidecar.write_text(f"{file_digest(archive)}  {archive.name}\n", encoding="ascii")
    expected_hash, expected_name = sidecar.read_text(encoding="ascii").strip().split("  ", 1)
    if expected_name != archive.name or expected_hash != file_digest(archive):
        raise RuntimeError("Archive sidecar integrity check failed")
    with workspace_copy_dir(bundle.parent) as tmp:
        with tarfile.open(archive, "r:gz") as tar:
            members = tar.getmembers()
            if any(Path(m.name).is_absolute() or ".." in Path(m.name).parts for m in members):
                raise RuntimeError("Unsafe archive path")
            if sys.version_info >= (3, 12):
                tar.extractall(tmp, filter="data")
            else:
                tar.extractall(tmp)
        relocated = Path(tmp) / "representative_v1"
        check = subprocess.run([sys.executable, str(relocated / "runner/validate_bundle.py"),
                                "--corpus", str(relocated), "--stage", "input"], capture_output=True, text=True)
        if check.returncode:
            raise RuntimeError("Relocated validation failed: " + check.stdout + check.stderr)
    print(f"Archive: {archive} bytes={archive.stat().st_size} sha256={file_digest(archive)}")


if __name__ == "__main__":
    main()
