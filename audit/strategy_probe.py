"""Isolated experiment: translate AbbrStra.C matching semantics directly.

This is diagnostic code, not a completed or C++-validated port. It deliberately
keeps the production candidate extractor, segmentation, and other heuristics.
Run: python audit/strategy_probe.py
Run all example collections with the C++ acceptance cutoff:
    python audit/strategy_probe.py --all
"""

from collections import Counter
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit.compare_ab3p import ROOT, documents, read_annotations, as_relation, metrics
import ab3p.algorithm as algorithm


def source_match(strategy, sf, long_tokens, data, word_set_allowed=True):
    """Translate search_backward, search_backward_adv, and strategy predicates."""
    if not sf or not long_tokens:
        return None
    original = [t.text for t in long_tokens]
    words = [w.lower() for w in original]
    wanted = sf.lower()
    general = strategy not in ("FirstLet", "FirstLetOneChSF")
    if strategy == "FirstLetOneChSF":
        last = original[-1]
        if (sum(c.isalpha() for c in last) == 1
                or all(not c.isalpha() or c.isupper() for c in last)
                or last.lower() in data.stopwords or last.lower() not in data.one_char_lfs):
            return None
    if strategy == "FirstLetGenS":
        if not sf.endswith("s") or not sf[:-1].isalpha() or not sf[:-1].isupper():
            return None
    mod = [None] * len(wanted)

    def backward(sloc, ti, ci):
        while sloc >= 0:
            while ci >= 0 and words[ti][ci] != wanted[sloc]:
                ci -= 1
            if ci < 0:
                ti -= 1
                if ti < 0:
                    return False
                ci = len(words[ti])-1
            else:
                if sloc == 0 and ci != 0:
                    if not general or words[ti][ci-1].isalnum():
                        ci -= 1
                        continue
                mod[sloc] = ti, ci
                sloc -= 1
                ci -= 1
        return True

    def advance():
        for i in range(len(wanted)):
            ti, ci = mod[i]
            if backward(i, ti, ci-1):
                return True
        return False

    def accepts():
        gaps = [mod[i+1][0]-mod[i][0]-1 for i in range(len(mod)-1)]
        gaps.append(len(words)-mod[-1][0]-1)
        boundary = [ci == 0 or (general and not words[ti][ci-1].isalnum())
                    for ti, ci in mod]
        if strategy == "FirstLetGenStp2":
            if max(gaps) != 2:
                return False
        elif max(gaps) > (1 if "Skp" in strategy or strategy in ("AnyLet", "FirstLetGenStp") else 0):
            return False
        if "Skp" in strategy or strategy == "FirstLetGenStp":
            if not any(g > 0 for g in gaps):
                return False
        if strategy in ("FirstLetGenStp", "FirstLetGenStp2"):
            for (ti, _), gap in zip(mod, gaps):
                if any(words[ti+j] not in data.stopwords for j in range(1, gap+1)):
                    return False
        if strategy.startswith("FirstLet"):
            if strategy == "FirstLetGenS":
                ti, ci = mod[-1]
                return (all(boundary[:-1]) and words[ti][ci] == "s"
                        and ci == len(words[ti])-1 and ti == mod[-2][0])
            if not all(boundary):
                return False
            if strategy == "FirstLetGen" and not any(ci > 0 for _, ci in mod):
                return False
        if strategy in ("WithinWrdWrd", "WithinWrdFWrd", "WithinWrdFWrdSkp"):
            if any(ci > 0 and words[ti][ci:] not in data.words for ti, ci in mod):
                return False
        if strategy.startswith("WithinWrd") and all(boundary):
            return False
        if strategy.startswith("WithinWrdF") or strategy.startswith("ContLet"):
            begins = {ti for (ti, _), b in zip(mod, boundary) if b}
            if any(ti not in begins for ti, _ in mod):
                return False
        if strategy.startswith("ContLet"):
            if not any(a[0] == b[0] and a[1]+1 == b[1] for a, b in zip(mod, mod[1:])):
                return False
        return True

    if not backward(len(wanted)-1, len(words)-1, len(words[-1])-1):
        return None
    while True:
        if accepts():
            return mod[0][0]
        if not advance():
            return None


def evaluate(path, ref_path, detector):
    reference = read_annotations(ref_path)
    r, s = Counter(), Counter()
    differences = []
    for di, doc in enumerate(documents(path)):
        docid = doc.findtext("id")
        for pi, p in enumerate(doc.findall("passage")):
            key = di, docid, pi
            r.update(key+a for a in reference[key])
            found = detector.find(p.findtext("text", ""), int(p.findtext("offset", "0")))
            s.update(key+as_relation(a) for a in found)
            rp = Counter(reference[key])
            sp = Counter(as_relation(a) for a in found)
            if rp != sp:
                differences.append(dict(file=path.name, doc=docid, passage=pi,
                    offset=int(p.findtext("offset", "0")), text=p.findtext("text", ""),
                    reference_only=list((rp-sp).elements()),
                    system_only=list((sp-rp).elements()),
                    current=[a.__dict__ for a in found]))
    pair_r = Counter({(k[1], k[3], k[4]): 1 for k in r})
    pair_s = Counter({(k[1], k[3], k[4]): 1 for k in s})
    return {"exact_occurrences": metrics(r, s), "document_pairs": metrics(pair_r, pair_s)}, differences


def main():
    algorithm._match = source_match
    cases = [
        (ROOT / "Ab3P-BioC/Ab3P_bioc_corpus.xml", ROOT / "Ab3P-BioC/Ab3P_bioc_gold.xml"),
        (ROOT / "examples/input/collection_full_00001.xml", ROOT / "examples/reference_output/collection_full_00001.xml"),
        (ROOT / "examples/input/collection_tiab_00001.xml", ROOT / "examples/reference_output/collection_tiab_00001.xml"),
    ]
    results = {}
    all_cases = "--all" in sys.argv
    if all_cases:
        cases = [(p, ROOT / "examples/reference_output" / p.name)
                 for p in sorted((ROOT / "examples/input").glob("*.xml"))]
    differences = []
    for threshold in ([0.0] if all_cases else [0.696532, 0.0]):
        detector = algorithm.Ab3P(min_precision=threshold)
        for path, ref_path in cases:
            name = f"{path.name}; min_precision={threshold}"
            results[name], diff = evaluate(path, ref_path, detector)
            differences.extend(dict(d, min_precision=threshold) for d in diff)
            print(name, results[name], flush=True)
    stem = "strategy_probe_all" if all_cases else "strategy_probe"
    if all_cases:
        results["aggregate"] = aggregate_results(results)
    (ROOT / f"audit/{stem}.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    (ROOT / f"audit/{stem}_differences.json").write_text(json.dumps(differences, indent=2), encoding="utf-8")


def aggregate_results(results):
    aggregate = {}
    for category in ["all", "full", "tiab"]:
        rows = [value["exact_occurrences"] for name, value in results.items()
                if name != "aggregate" and (category == "all" or f"_{category}_" in name)]
        counts = {field: sum(row[field] for row in rows)
                  for field in ["reference", "system", "common", "reference_only", "system_only"]}
        counts.update(precision=counts["common"]/counts["system"],
                      recall=counts["common"]/counts["reference"],
                      f1=2*counts["common"]/(counts["system"]+counts["reference"]))
        aggregate[category] = counts
    return aggregate


if __name__ == "__main__":
    main()
