"""Restore source identifiers after an incomplete metadata enrichment.

This only operates on an unsealed representative_v1 bundle. It retains the
previous manifests in the ignored cache before resetting derived metadata.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil

try:
    from .prepare import BUNDLE, CACHE, digest, jd, load_log, family_keys
except ImportError:
    from prepare import BUNDLE, CACHE, digest, jd, load_log, family_keys


def main() -> None:
    bundle = BUNDLE
    manifests = bundle / "manifests"
    if (manifests / "files.sha256").exists() or (bundle.parent / "representative_v1.input.tar.gz").exists():
        raise RuntimeError("Bundle is frozen; a revision is required")
    diagnostic = CACHE / "diagnostics/metadata_reference_leak_20261007"
    if diagnostic.exists():
        raise RuntimeError(f"Diagnostic backup already exists: {diagnostic}")
    selected = {(row["cohort"], row["ordinal"]): row
                for row in load_log(CACHE / "selection.jsonl") if row["status"] == "selected"}
    article_path = manifests / "articles.jsonl"
    articles = load_log(article_path)
    if len(articles) != len(selected):
        raise RuntimeError("Selected/article count mismatch")
    for article in articles:
        key = (article["cohort"], article["draw_ordinal"])
        source = selected.get(key)
        if source is None or source["id"] != article["id"] or source["partition"] != article["partition"]:
            raise RuntimeError(f"Article/selection mismatch: {key}")
    names = ("articles.jsonl", "metadata.jsonl", "metadata_requests.jsonl",
             "pmc_links.jsonl", "family_conflicts.json")
    diagnostic.mkdir(parents=True)
    saved = {}
    for name in names:
        source = manifests / name
        if source.exists():
            shutil.copy2(source, diagnostic / name)
            saved[name] = digest(source.read_bytes())
    (diagnostic / "reason.json").write_text(jd({
        "reason": "PubMed XML ArticleIdList search included cited-reference IDs; restore BioC source identifiers before corrected article-scoped enrichment",
        "backed_up_sha256": saved,
    }) + "\n", encoding="utf-8")
    for article in articles:
        key = (article["cohort"], article["draw_ordinal"])
        source = selected[key]
        article["identifiers"] = dict(source["identifiers"])
        article["family_keys"] = sorted(family_keys(article["identifiers"]))
        article.pop("metadata", None)
        article.pop("linked_pmids", None)
    temporary = article_path.with_suffix(".jsonl.tmp")
    temporary.write_text("".join(jd(row) + "\n" for row in articles), encoding="utf-8", newline="\n")
    temporary.replace(article_path)
    for name in names[1:]:
        (manifests / name).unlink(missing_ok=True)
    (manifests / "metadata_complete.json").unlink(missing_ok=True)
    print(f"Restored {len(articles)} article source identifiers; backup: {diagnostic}")


if __name__ == "__main__":
    main()
