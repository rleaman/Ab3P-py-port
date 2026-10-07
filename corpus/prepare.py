"""Prepare the frozen representative BioC corpus. Python 3.10+, standard library.

Run from the repository root. All downloaded article text stays in the ignored
evaluation/representative_v1_cache directory. No detector is invoked.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "corpus/protocol_v1.json"
CACHE = ROOT / "evaluation/representative_v1_cache"
BUNDLE = ROOT / "evaluation/representative_v1"
ORDER = ("development", "holdout", "reserve")
HEADERS = {"User-Agent": "Ab3P-representative-v1/1.0 (public research corpus)"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def xml_bytes(root: ET.Element, declaration: bool = True) -> bytes:
    # XML 1.0 normalizes literal CR on parse; a character reference preserves
    # the decoded code point and makes source-text round trips exact.
    return ET.tostring(root, encoding="utf-8", xml_declaration=declaration,
                       short_empty_elements=False).replace(b"\r", b"&#13;")


def jd(obj: object) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def infons(element: ET.Element) -> dict[str, str]:
    return {e.get("key", ""): e.text or "" for e in element.findall("infon")}


def norm_doi(value: str) -> str:
    value = value.strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if value.startswith(prefix):
            value = value[len(prefix):]
    return value


def identifiers(document: ET.Element) -> dict[str, str]:
    found: dict[str, str] = {}
    fields = [infons(document)] + [infons(p) for p in document.findall("passage")]
    docid = document.findtext("id", "").strip()
    if docid.upper().startswith("PMC") and docid[3:].isdigit():
        found["pmcid"] = "PMC" + str(int(docid[3:]))
    elif docid.isdigit():
        found["pmid"] = str(int(docid))
    for field in fields:
        for key, target in (("article-id_pmid", "pmid"), ("article-id_pmc", "pmcid"),
                            ("article-id_doi", "doi")):
            val = field.get(key, "").strip()
            if not val:
                continue
            if target == "doi":
                val = norm_doi(val)
            elif target == "pmcid":
                val = "PMC" + str(int(val.upper().removeprefix("PMC"))) if val.upper().removeprefix("PMC").isdigit() else val
            elif val.isdigit():
                val = str(int(val))
            found[target] = val
    return found


def exclusion_ids() -> set[str]:
    ids: set[str] = set()
    paths = list((ROOT / "examples/input").glob("*.xml"))
    paths.append(ROOT / "Ab3P-BioC/Ab3P_bioc_corpus.xml")
    paths.append(ROOT / "Ab3P-BioC/Ab3P_bioc_gold.xml")
    for path in paths:
        if not path.exists():
            continue
        for _, elem in ET.iterparse(path, events=("end",)):
            if elem.tag != "document":
                continue
            for kind, value in identifiers(elem).items():
                ids.add(kind + ":" + value)
            elem.clear()
    return ids


def candidate(cohort: str, ordinal: int, protocol: dict) -> int:
    upper = protocol["frames"][cohort]["id_range_inclusive"][1]
    seed = hashlib.sha256((protocol["seed"] + ":" + cohort).encode()).digest()
    a = 1 + int.from_bytes(seed[:8], "big") % (upper - 1)
    while math.gcd(a, upper) != 1:
        a += 1
    b = int.from_bytes(seed[8:16], "big") % upper
    if ordinal >= upper:
        raise RuntimeError("Identifier permutation exhausted")
    return 1 + (a * ordinal + b) % upper


def load_log(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def append_log(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(jd(row) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def raw_path(cohort: str, ident: int) -> Path:
    return CACHE / "raw" / cohort / f"{ident // 100000:04d}" / f"{ident}.xml"


def fetch(cohort: str, ident: int, protocol: dict, gap: float, clock: list[float]) -> tuple[bytes | None, list[dict]]:
    url = protocol["sources"][cohort].format(id=ident)
    path = raw_path(cohort, ident)
    old_path = CACHE / "raw" / cohort / f"{ident}.xml"
    if old_path.exists():
        path = old_path
    if path.exists():
        data = path.read_bytes()
        return data, [{"status": "cache", "url": url, "sha256": digest(data), "bytes": len(data)}]
    attempts: list[dict] = []
    for attempt in range(1, 6):
        wait = gap - (time.monotonic() - clock[0])
        if wait > 0:
            time.sleep(wait)
        clock[0] = time.monotonic()
        req = urllib.request.Request(url, headers=HEADERS)
        started = dt.datetime.now(dt.timezone.utc).isoformat()
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                data = response.read(12_000_001)
                if len(data) > 12_000_000:
                    raise ValueError("Response exceeds 12 MB bound")
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(".tmp")
                tmp.write_bytes(data)
                tmp.replace(path)
                attempts.append({"attempt": attempt, "at_utc": started, "status": response.status,
                                 "url": url, "bytes": len(data), "sha256": digest(data)})
                return data, attempts
        except urllib.error.HTTPError as exc:
            attempts.append({"attempt": attempt, "at_utc": started, "status": exc.code, "url": url})
            if exc.code not in (429, 500, 502, 503, 504):
                break
            retry_after = exc.headers.get("Retry-After")
            time.sleep(min(120, max(2 ** attempt, int(retry_after) if retry_after and retry_after.isdigit() else 0)))
        except (OSError, ValueError) as exc:
            attempts.append({"attempt": attempt, "at_utc": started, "status": "error",
                             "url": url, "error": type(exc).__name__ + ": " + str(exc)[:200]})
            time.sleep(min(60, 2 ** attempt))
    return None, attempts


def fetch_sample(cohort: str, ident: int, ordinal: int, protocol: dict,
                 gap: float, clock: list[float], batches: dict) -> tuple[bytes | None, list[dict], dict | None]:
    rule = protocol["batching"][cohort]
    if ordinal < rule["start_ordinal"]:
        data, attempts = fetch(cohort, ident, protocol, gap, clock)
        return data, attempts, None
    size = rule["size"]
    start = rule["start_ordinal"] + ((ordinal - rule["start_ordinal"]) // size) * size
    if start not in batches:
        ids = [candidate(cohort, n, protocol) for n in range(start, start + size)]
        idlist = ",".join(("PMC" if cohort == "pmc" else "") + str(value) for value in ids)
        endpoint = "pubmed.cgi" if cohort == "pubmed" else "pmcoa.cgi"
        url = f"https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/{endpoint}/BioC_xml/{idlist}/unicode"
        batch_path = CACHE / "batches" / cohort / f"{start:09d}.xml"
        attempts = []
        if batch_path.exists():
            response = batch_path.read_bytes()
            attempts.append({"status": "cache", "url": url, "sha256": digest(response), "bytes": len(response)})
        else:
            response = None
            for attempt in range(1, 6):
                wait = gap - (time.monotonic() - clock[0])
                if wait > 0:
                    time.sleep(wait)
                clock[0] = time.monotonic()
                at = dt.datetime.now(dt.timezone.utc).isoformat()
                try:
                    request = urllib.request.Request(url, headers=HEADERS)
                    with urllib.request.urlopen(request, timeout=60) as result:
                        limit = 40_000_000 if cohort == "pmc" else 12_000_000
                        response = result.read(limit + 1)
                        if len(response) > limit:
                            raise ValueError(f"Batch exceeds {limit} byte bound")
                        if response.lstrip().startswith(b"<?xml"):
                            ET.fromstring(response)
                        elif not response.startswith(b"[Error] : No result can be found."):
                            raise ValueError("Unexpected non-XML batch response")
                        batch_path.parent.mkdir(parents=True, exist_ok=True)
                        tmp = batch_path.with_suffix(".tmp")
                        tmp.write_bytes(response)
                        tmp.replace(batch_path)
                        attempts.append({"at_utc": at, "attempt": attempt, "status": result.status,
                                         "url": url, "sha256": digest(response), "bytes": len(response)})
                        break
                except urllib.error.HTTPError as exc:
                    attempts.append({"at_utc": at, "attempt": attempt, "status": exc.code, "url": url})
                    if exc.code not in (429, 500, 502, 503, 504):
                        break
                    retry_after = exc.headers.get("Retry-After")
                    time.sleep(min(120, max(2 ** attempt, int(retry_after) if retry_after and retry_after.isdigit() else 0)))
                except (OSError, ValueError, ET.ParseError) as exc:
                    attempts.append({"at_utc": at, "attempt": attempt,
                                     "status": "error", "error": str(exc)[:200], "url": url})
                    time.sleep(min(60, 2 ** attempt))
        metadata = {"url": url, "start_ordinal": start, "ids": ids,
                    "raw_batch_sha256": digest(response) if response is not None else None,
                    "raw_batch_bytes": len(response) if response is not None else None,
                    "attempts": attempts}
        documents: dict[int, bytes] = {}
        if response is not None and response.lstrip().startswith(b"<?xml"):
            root = ET.fromstring(response)
            returned: dict[int, bytes] = {}
            duplicate_ids = []
            for doc in root.findall("document"):
                docid = doc.findtext("id", "")
                digits = docid.upper().removeprefix("PMC")
                if not digits.isdigit():
                    continue
                number = int(digits)
                if number not in ids:
                    raise RuntimeError(f"Unexpected BioC document ID {docid} in batch {start}")
                source_doc = ET.tostring(doc, encoding="utf-8")
                if number in returned:
                    if returned[number] != source_doc:
                        raise RuntimeError(f"Conflicting duplicate BioC document ID {docid} in batch {start}")
                    duplicate_ids.append(number)
                    continue
                returned[number] = source_doc
                one = ET.Element("collection")
                for field in ("source", "date", "key"):
                    ET.SubElement(one, field).text = root.findtext(field, "")
                one.append(doc)
                documents[number] = xml_bytes(one)
            metadata["duplicate_returned_ids"] = duplicate_ids
        batches[start] = (documents, metadata)
    documents, metadata = batches[start]
    for old_start in list(batches):
        if old_start != start:
            del batches[old_start]
    data = documents.get(ident)
    if data is not None:
        path = raw_path(cohort, ident)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(data)
            tmp.replace(path)
        elif digest(path.read_bytes()) != digest(data):
            raise RuntimeError(f"Cached derived document changed: {path}")
    return data, metadata["attempts"], {k: v for k, v in metadata.items() if k != "attempts"}


def parse_source(data: bytes, cohort: str, ident: int) -> tuple[ET.Element | None, dict]:
    if data.startswith(b"[Error] : No result can be found."):
        return None, {"status": "api_no_result"}
    try:
        root = ET.fromstring(data)
    except ET.ParseError as exc:
        return None, {"status": "invalid_xml", "detail": str(exc)}
    docs = root.findall("document")
    if root.tag != "collection" or len(docs) != 1:
        return None, {"status": "wrong_document_count", "count": len(docs)}
    doc = docs[0]
    ids = identifiers(doc)
    key = "pmid" if cohort == "pubmed" else "pmcid"
    expected = str(ident) if cohort == "pubmed" else "PMC" + str(ident)
    if ids.get(key) != expected:
        return None, {"status": "identifier_mismatch", "identifiers": ids}
    passages = doc.findall("passage")
    if any(p.findall("sentence") and p.find("text") is None for p in passages):
        return None, {"status": "sentence_only_passage_unsupported"}
    types = [infons(p).get("type", "").lower() for p in passages]
    texts = [p.findtext("text", "") for p in passages]
    if cohort == "pubmed" and not (any(t == "title" and text for t, text in zip(types, texts))
                                   and any(t == "abstract" and text for t, text in zip(types, texts))):
        return None, {"status": "missing_title_or_abstract"}
    if cohort == "pmc" and not any(text for typ, text in zip(types, texts)
                                   if typ in ("paragraph", "body") or typ.startswith("paragraph_")):
        return None, {"status": "missing_full_text"}
    license_values = [(infon.text or "") for x in [doc] + passages
                      for infon in x.findall("infon") if infon.get("key") == "license"]
    if cohort == "pmc" and not any(license_values):
        return None, {"status": "missing_reuse_metadata"}
    return doc, {"status": "eligible", "identifiers": ids,
                 "source_collection_date": root.findtext("date"),
                 "source_collection_name": root.findtext("source"),
                 "license": next((x for x in license_values if x), ""),
                 "license_statements": list(dict.fromkeys(x for x in license_values if x)),
                 "passage_types": types, "passage_count": len(passages),
                 "year": next((infons(p).get("year") for p in passages if infons(p).get("year")), None),
                 "publisher": next((infons(p).get("publisher") for p in passages if infons(p).get("publisher")), None)}


def family_keys(ids: dict[str, str]) -> set[str]:
    return {kind + ":" + value for kind, value in ids.items() if value}


def apply_cross_reference(selected: list[dict], excluded: set[str],
                          family_partition: dict[str, str], family_cohorts: set[tuple[str, str]]) -> None:
    """Link PMID/PMCID/DOI families from NCBI's documented bulk ID file."""
    try:
        from .family_index import links_for, DEST
    except ImportError:
        from family_index import links_for, DEST
    link_path = CACHE / "metadata/selected_family_links.jsonl"
    if link_path.exists():
        links: dict[str, list[dict]] = {}
        for record in load_log(link_path):
            links.setdefault(record["pmid"], []).append(record)
    else:
        selected_pmids = {r["identifiers"]["pmid"] for r in selected
                          if r["cohort"] == "pubmed" and r["identifiers"].get("pmid")}
        excluded_pmids = {x.split(":", 1)[1] for x in excluded if x.startswith("pmid:")}
        found = links_for(selected_pmids | excluded_pmids)
        source_hash = digest(DEST.read_bytes())
        links = {pmid: [{"pmid": pmid, "pmcid": data.get("pmcid", ""),
                        "doi": norm_doi(data.get("doi", "")), "source_url":
                        "https://ftp.ncbi.nlm.nih.gov/pub/pmc/PMC-ids.csv.gz",
                        "source_sha256": source_hash} for data in values]
                 for pmid, values in found.items()}
        flattened = [r for values in links.values() for r in values]
        link_path.write_text("".join(jd(r) + "\n" for r in sorted(flattened, key=lambda x: (int(x["pmid"]), x["pmcid"]))),
                             encoding="utf-8")
    for pmid_key in list(excluded):
        if not pmid_key.startswith("pmid:"):
            continue
        for link in links.get(pmid_key.split(":", 1)[1], []):
            for kind in ("pmcid", "doi"):
                if link.get(kind):
                    excluded.add(kind + ":" + link[kind])
    (CACHE / "metadata/excluded_family_keys.json").write_text(
        json.dumps({"keys": sorted(excluded), "source": "supplied examples and gold plus PMC-ids cross-reference"},
                   indent=2) + "\n", encoding="utf-8")
    for row in selected:
        if row["cohort"] != "pubmed":
            continue
        for link in links.get(row["identifiers"].get("pmid", ""), []):
            for kind in ("pmcid", "doi"):
                if not link.get(kind):
                    continue
                key = kind + ":" + link[kind]
                if key in excluded:
                    raise RuntimeError(f"Selected PubMed article linked to supplied family: {row['id']}")
                prior = family_partition.get(key)
                if prior and prior != row["partition"]:
                    raise RuntimeError(f"PubMed family split conflict for {key}: {prior}/{row['partition']}")
                family_partition[key] = row["partition"]
                family_cohorts.add((key, "pubmed"))


def collect(args: argparse.Namespace, protocol: dict) -> None:
    excluded = exclusion_ids()
    logpath = CACHE / "selection.jsonl"
    rows = load_log(logpath)
    selected = [r for r in rows if r["status"] == "selected"]
    family_partition = {key: r["partition"] for r in selected for key in family_keys(r["identifiers"])}
    family_cohorts = {(key, r["cohort"]) for r in selected for key in family_keys(r["identifiers"])}
    used = collections.Counter((r["cohort"], r["partition"]) for r in selected)
    counters = collections.Counter(r["cohort"] for r in rows)
    clock = [0.0]
    batches: dict = {}
    known_batch_hashes = {
        (r["cohort"], r["batch"]["start_ordinal"]): r["batch"]["raw_batch_sha256"]
        for r in rows if r.get("batch") and r["batch"].get("raw_batch_sha256")
    }
    draws = 0
    for cohort in ("pubmed", "pmc"):
        if cohort == "pmc":
            # PubMed selection is now fixed; add IDs absent from the BioC text
            # response before drawing any PMC article.
            apply_cross_reference([r for r in load_log(logpath) if r["status"] == "selected"],
                                  excluded, family_partition, family_cohorts)
        for quota in protocol["allocation"]:
            part = quota["partition"]
            target = quota[cohort]
            while used[cohort, part] < target:
                if args.limit_draws is not None and draws >= args.limit_draws:
                    print(f"Paused after {draws} new draws; selected={dict(used)}")
                    return
                ordinal = counters[cohort]
                ident = candidate(cohort, ordinal, protocol)
                counters[cohort] += 1
                draws += 1
                row: dict = {"cohort": cohort, "id": ident, "ordinal": ordinal,
                             "partition_requested": part,
                             "at_utc": dt.datetime.now(dt.timezone.utc).isoformat()}
                primary = ("pmid:" if cohort == "pubmed" else "pmcid:PMC") + str(ident)
                if primary in excluded:
                    row["status"] = "excluded_supplied"
                else:
                    data, attempts, batch = fetch_sample(cohort, ident, ordinal, protocol,
                                                         args.gap_seconds, clock, batches)
                    row["attempts"] = attempts
                    if batch is not None:
                        row["batch"] = batch
                        batch_key = (cohort, batch["start_ordinal"])
                        old_hash = known_batch_hashes.get(batch_key)
                        if old_hash and old_hash != batch["raw_batch_sha256"]:
                            raise RuntimeError(f"Raw BioC batch changed during resume: {batch_key}")
                        if batch["raw_batch_sha256"]:
                            known_batch_hashes[batch_key] = batch["raw_batch_sha256"]
                    if data is None:
                        row["status"] = "api_no_result" if batch and batch["raw_batch_sha256"] else "retrieval_failed"
                    else:
                        row["raw_sha256"] = digest(data)
                        row["raw_bytes"] = len(data)
                        doc, info = parse_source(data, cohort, ident)
                        row.update(info)
                        if doc is not None:
                            keys = family_keys(info["identifiers"])
                            if keys & excluded:
                                row["status"] = "excluded_supplied_family"
                            elif any((key, cohort) in family_cohorts for key in keys):
                                row["status"] = "duplicate_article_family"
                            else:
                                linked = {family_partition[k] for k in keys if k in family_partition}
                                if len(linked) > 1:
                                    row["status"] = "family_conflict"
                                    row["linked_partitions"] = sorted(linked)
                                elif linked:
                                    linked_part = next(iter(linked))
                                    if cohort == "pubmed" or used[cohort, linked_part] >= next(q[cohort] for q in protocol["allocation"] if q["partition"] == linked_part):
                                        row["status"] = "duplicate_or_full_linked_family"
                                    elif linked_part != part:
                                        # Fill its existing family partition without consuming the requested slot.
                                        row["status"] = "selected"
                                        row["partition"] = linked_part
                                    else:
                                        row["status"] = "selected"
                                        row["partition"] = part
                                else:
                                    row["status"] = "selected"
                                    row["partition"] = part
                                if row["status"] == "selected":
                                    used[cohort, row["partition"]] += 1
                                    for key in keys:
                                        family_partition[key] = row["partition"]
                                        family_cohorts.add((key, cohort))
                append_log(logpath, row)
                if draws % 100 == 0:
                    print(f"{cohort} draws={counters[cohort]} {part}={used[cohort, part]}/{target}", flush=True)
    print("All quotas filled. Run with --build to create frozen bundle.")


def canonical_document(source: ET.Element, cohort: str) -> tuple[ET.Element, list[dict]]:
    doc = ET.Element("document")
    ET.SubElement(doc, "id").text = source.findtext("id", "")
    for infon in source.findall("infon"):
        doc.append(ET.fromstring(ET.tostring(infon, encoding="utf-8")))
    base = 0
    provenance = []
    for index, source_passage in enumerate(source.findall("passage")):
        text = source_passage.findtext("text", "")
        passage = ET.SubElement(doc, "passage")
        for infon in source_passage.findall("infon"):
            passage.append(ET.fromstring(ET.tostring(infon, encoding="utf-8")))
        ET.SubElement(passage, "offset").text = str(base)
        ET.SubElement(passage, "text").text = text
        provenance.append({"index": index, "canonical_offset": base,
                           "source_offset": source_passage.findtext("offset"),
                           "source_offset_unit": "producer_unspecified",
                           "type": infons(source_passage).get("type"),
                           "section_type": infons(source_passage).get("section_type"),
                           "length_codepoints": len(text), "text_sha256": digest(text.encode("utf-8"))})
        base += len(text) + 1
    return doc, provenance


def write_xml(path: Path, docs: list[ET.Element]) -> str:
    root = ET.Element("collection")
    ET.SubElement(root, "source").text = "NCBI Unicode BioC; Ab3P representative_v1"
    ET.SubElement(root, "date").text = "20261007"
    ET.SubElement(root, "key").text = "collection.key"
    root.extend(docs)
    ET.indent(root, space="  ")
    data = xml_bytes(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return digest(data)


def build(protocol: dict) -> None:
    rows = load_log(CACHE / "selection.jsonl")
    selected = [r for r in rows if r["status"] == "selected"]
    counts = collections.Counter((r["cohort"], r["partition"]) for r in selected)
    for q in protocol["allocation"]:
        for cohort in ("pubmed", "pmc"):
            if counts[cohort, q["partition"]] != q[cohort]:
                raise RuntimeError(f"Incomplete {cohort}/{q['partition']}: {counts[cohort, q['partition']]}/{q[cohort]}")
    if BUNDLE.exists():
        raise RuntimeError("Frozen bundle already exists; version a revision instead of overwriting")
    staging = BUNDLE.with_name(BUNDLE.name + "_staging")
    if staging.exists():
        raise RuntimeError(f"Unfinished staging directory exists: {staging}")
    staging.mkdir(parents=True)
    shutil.copy2(PROTOCOL, staging / "protocol.json")
    (staging / "manifests").mkdir()
    (staging / "reports").mkdir()
    article_rows, input_rows = [], []
    for cohort in ("pubmed", "pmc"):
        for part in ORDER:
            subset = [r for r in selected if r["cohort"] == cohort and r["partition"] == part]
            size = protocol["shards"][cohort + "_documents"]
            for start in range(0, len(subset), size):
                shard = start // size + 1
                name = f"{cohort}_{'tiab' if cohort == 'pubmed' else 'full'}_{shard:05d}.xml"
                rel = f"input/{part}/{name}"
                docs = []
                local = []
                for row in subset[start:start + size]:
                    raw = raw_path(cohort, row["id"])
                    if not raw.exists():
                        raw = CACHE / "raw" / cohort / f"{row['id']}.xml"
                    data = raw.read_bytes()
                    if digest(data) != row["raw_sha256"]:
                        raise RuntimeError(f"Raw checksum mismatch {raw}")
                    source, info = parse_source(data, cohort, row["id"])
                    if source is None:
                        raise RuntimeError(f"Source changed {raw}: {info}")
                    doc, passages = canonical_document(source, cohort)
                    docs.append(doc)
                    local.append((row, passages, doc.findtext("id", ""), info))
                filehash = write_xml(staging / rel, docs)
                for idx, (row, passages, docid, info) in enumerate(local):
                    article_rows.append({"cohort": cohort, "partition": part, "id": row["id"],
                                         "document_id": docid, "identifiers": row["identifiers"],
                                         "family_keys": sorted(family_keys(row["identifiers"])),
                                         "license": info["license"], "year": info["year"],
                                         "license_statements": info.get("license_statements", []),
                                         "source_collection_date": info.get("source_collection_date"),
                                         "source_collection_name": info.get("source_collection_name"),
                                         "publisher": info["publisher"], "passage_types": info["passage_types"],
                                         "raw_url": protocol["sources"][cohort].format(id=row["id"]),
                                         "raw_sha256": row["raw_sha256"], "raw_bytes": row["raw_bytes"],
                                         "request_url": row.get("batch", {}).get("url")
                                         or protocol["sources"][cohort].format(id=row["id"]),
                                         "response_sha256": row.get("batch", {}).get("raw_batch_sha256")
                                         or row["raw_sha256"],
                                         "protocol_version": ("1.0.0" if row["ordinal"] < 184 else "1.1.0")
                                         if cohort == "pubmed" else protocol["protocol_version"],
                                         "raw_batch_sha256": row.get("batch", {}).get("raw_batch_sha256"),
                                         "draw_ordinal": row["ordinal"], "file": rel, "index": idx})
                    input_rows.append({"cohort": cohort, "partition": part, "document_id": docid,
                                       "file": rel, "file_sha256": filehash, "index": idx,
                                       "passages": passages})
    for filename, data in (("articles.jsonl", article_rows), ("inputs.jsonl", input_rows),
                           ("retrieval.jsonl", rows)):
        path = staging / "manifests" / filename
        path.write_text("".join(jd(row) + "\n" for row in data), encoding="utf-8", newline="\n")
    staging.replace(BUNDLE)
    print(f"Built {len(selected)} representative documents at {BUNDLE}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-draws", type=int, help="Stop after this many new candidate IDs")
    parser.add_argument("--gap-seconds", type=float, default=1.5)
    parser.add_argument("--build", action="store_true")
    args = parser.parse_args()
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    if args.build:
        build(protocol)
    else:
        collect(args, protocol)


if __name__ == "__main__":
    main()
