"""Cache PubMed metadata for coverage audits without changing sampled text."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

try:
    from .prepare import BUNDLE, CACHE, digest, jd, norm_doi
    from .family_index import links_for_pmcids
except ImportError:  # direct: python corpus/enrich_metadata.py
    from prepare import BUNDLE, CACHE, digest, jd, norm_doi
    from family_index import links_for_pmcids

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"


def fetch_batch(ids: list[str], index: int) -> tuple[bytes | None, dict]:
    params = urllib.parse.urlencode({"db": "pubmed", "id": ",".join(ids),
                                     "retmode": "xml", "tool": "Ab3PPhase1"})
    url = BASE + "?" + params
    ids_sha256 = digest(",".join(ids).encode("ascii"))
    path = CACHE / "metadata" / f"pubmed_{index:05d}_{ids_sha256[:16]}.xml"
    entry = {"url": url, "batch_index": index, "ids": ids,
             "ids_sha256": ids_sha256, "cache_name": path.name}
    if path.exists():
        data = path.read_bytes()
        entry.update({"status": "cache", "sha256": digest(data), "bytes": len(data)})
        return data, entry
    attempts = []
    for n in range(1, 6):
        started = dt.datetime.now(dt.timezone.utc).isoformat()
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "Ab3P-representative-v1/1.0"})
            with urllib.request.urlopen(request, timeout=60) as response:
                data = response.read(10_000_001)
                if len(data) > 10_000_000:
                    raise ValueError("Metadata response exceeds 10 MB bound")
                parsed = ET.fromstring(data)
                if parsed.tag != "PubmedArticleSet":
                    raise ValueError(f"Unexpected metadata root: {parsed.tag}")
                path.parent.mkdir(parents=True, exist_ok=True)
                temporary = path.with_suffix(path.suffix + ".tmp")
                temporary.write_bytes(data)
                temporary.replace(path)
                entry.update({"status": "success", "sha256": digest(data), "bytes": len(data),
                              "attempts": attempts + [{"at_utc": started, "status": response.status}]})
                return data, entry
        except (OSError, ValueError, ET.ParseError) as exc:
            attempts.append({"at_utc": started, "attempt": n, "error": str(exc)[:200]})
            time.sleep(min(60, 2 ** n))
    entry.update({"status": "failed", "attempts": attempts})
    return None, entry


def article_metadata(article: ET.Element) -> dict:
    uid = article.findtext("./MedlineCitation/PMID", "")
    if not uid:
        return {}
    citation = article.find("./MedlineCitation")
    year = (citation.findtext("./Article/Journal/JournalIssue/PubDate/Year")
            or citation.findtext("./Article/ArticleDate/Year"))
    if not year:
        medline_date = citation.findtext("./Article/Journal/JournalIssue/PubDate/MedlineDate", "")
        match = re.search(r"\b(?:18|19|20)\d{2}\b", medline_date)
        year = match.group(0) if match else None
    article_ids = {x.get("IdType"): (x.text or "")
                   for x in article.findall("./PubmedData/ArticleIdList/ArticleId")}
    return {"pmid": uid, "pub_year": year or None,
            "article_types": sorted({x.text or "" for x in citation.findall("./Article/PublicationTypeList/PublicationType") if x.text}),
            "subjects": sorted({x.text or "" for x in citation.findall("./MeshHeadingList/MeshHeading/DescriptorName") if x.text}),
            "journal": citation.findtext("./Article/Journal/Title"),
            "publisher": citation.findtext("./Article/Journal/Publisher/PublisherName"),
            "doi": norm_doi(article_ids.get("doi", "")),
            "pmcid": article_ids.get("pmc", "")}


def enrich(bundle: Path = BUNDLE) -> None:
    articles_path = bundle / "manifests/articles.jsonl"
    articles = [json.loads(line) for line in articles_path.read_text(encoding="utf-8").splitlines()]
    pmcids = {r["identifiers"]["pmcid"] for r in articles
              if r["cohort"] == "pmc" and r["identifiers"].get("pmcid")}
    pmc_links = links_for_pmcids(pmcids)
    pmc_link_rows = []
    for row in articles:
        if row["cohort"] != "pmc":
            continue
        pmcid = row["identifiers"].get("pmcid", "")
        linked_pmids = []
        for link in pmc_links.get(pmcid, []):
            pmc_link_rows.append({"pmcid": pmcid, **link})
            if link.get("pmid"):
                linked_pmids.append(link["pmid"])
                row["identifiers"].setdefault("pmid", link["pmid"])
            if link.get("doi"):
                row["identifiers"].setdefault("doi", norm_doi(link["doi"]))
        row["linked_pmids"] = sorted(set(linked_pmids), key=int)
    (bundle / "manifests/pmc_links.jsonl").write_text(
        "".join(jd(r) + "\n" for r in pmc_link_rows), encoding="utf-8")
    pmids = sorted({r["identifiers"]["pmid"] for r in articles if r["identifiers"].get("pmid")}, key=int)
    if not pmids:
        raise RuntimeError("No PMIDs to enrich")
    metadata: dict[str, dict] = {}
    requests = []
    for batch_no, start in enumerate(range(0, len(pmids), 100), 1):
        ids = pmids[start:start + 100]
        data, request = fetch_batch(ids, batch_no)
        requests.append(request)
        if data is None:
            raise RuntimeError(f"Metadata request failed: batch {batch_no}")
        root = ET.fromstring(data)
        for item in root.findall("PubmedArticle") + root.findall("PubmedBookArticle"):
            record = article_metadata(item)
            if record:
                metadata[record["pmid"]] = record
        if batch_no % 25 == 0:
            print(f"Metadata batches {batch_no}/{(len(pmids) + 99) // 100}", flush=True)
        if request["status"] == "success":
            time.sleep(0.4)
    family_partition: dict[str, str] = {}
    conflicts = []
    for row in articles:
        record = metadata.get(row["identifiers"].get("pmid", ""))
        if record:
            row["metadata"] = record
            for kind in ("doi", "pmcid"):
                if record.get(kind):
                    value = record[kind]
                    if kind == "pmcid" and value.upper().startswith("PMC"):
                        value = "PMC" + str(int(value[3:])) if value[3:].isdigit() else value
                    row["identifiers"].setdefault(kind, value)
        else:
            row["metadata"] = {"status": "missing"}
        row["family_keys"] = sorted(
            {k + ":" + v for k, v in row["identifiers"].items() if v}
            | {"pmid:" + x for x in row.get("linked_pmids", [])})
        for key in row["family_keys"]:
            prior = family_partition.setdefault(key, row["partition"])
            if prior != row["partition"]:
                conflicts.append({"family_key": key, "partitions": sorted({prior, row["partition"]})})
    (bundle / "manifests/metadata_requests.jsonl").write_text(
        "".join(jd(r) + "\n" for r in requests), encoding="utf-8")
    (bundle / "manifests/metadata.jsonl").write_text(
        "".join(jd(metadata.get(id, {"pmid": id, "status": "missing"})) + "\n" for id in pmids),
        encoding="utf-8")
    articles_path.write_text("".join(jd(r) + "\n" for r in articles), encoding="utf-8")
    if conflicts:
        (bundle / "manifests/family_conflicts.json").write_text(
            json.dumps(conflicts, indent=2) + "\n", encoding="utf-8")
        raise RuntimeError(f"{len(conflicts)} linked article-family conflicts need explicit resolution")
    names = ("articles.jsonl", "metadata.jsonl", "metadata_requests.jsonl", "pmc_links.jsonl")
    marker = bundle / "manifests/metadata_complete.json"
    temporary = marker.with_suffix(marker.suffix + ".tmp")
    temporary.write_text(jd({"articles": len(articles),
                             "sha256": {name: digest((bundle / "manifests" / name).read_bytes())
                                        for name in names}}) + "\n", encoding="utf-8")
    temporary.replace(marker)
