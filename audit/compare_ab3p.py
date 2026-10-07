"""Reproduce the port audit without changing extraction code or saved outputs.

Run from the repository root: python audit/compare_ab3p.py
The comparison uses BioC relations, preserving repeated occurrences and spans.
"""

from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import sys
import time

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ab3p.algorithm import Ab3P


def documents(path):
    for _, doc in etree.iterparse(str(path), events=("end",), tag="document"):
        yield doc
        doc.clear()
        while doc.getprevious() is not None:
            del doc.getparent()[0]


def relations(passage):
    annotations = {a.get("id"): a for a in passage.findall("annotation")}
    out = []
    for relation in passage.findall("relation"):
        nodes = {n.get("role"): annotations[n.get("refid")]
                 for n in relation.findall("node")}
        if "ShortForm" not in nodes or "LongForm" not in nodes:
            continue
        sf, lf = nodes["ShortForm"], nodes["LongForm"]
        sl, ll = sf.find("location"), lf.find("location")
        out.append((sf.findtext("text", ""), lf.findtext("text", ""),
                    int(sl.get("offset")), int(ll.get("offset")),
                    int(sl.get("length")), int(ll.get("length"))))
    return out


def read_annotations(path):
    return {(di, doc.findtext("id"), pi): relations(p)
            for di, doc in enumerate(documents(path))
            for pi, p in enumerate(doc.findall("passage"))}


def predictions(detector, text, offset):
    return detector.find(text, offset)


def as_relation(a):
    return (a.sf, a.lf, a.sf_offset, a.lf_offset, len(a.sf), len(a.lf))


def metrics(ref, system):
    common = sum((ref & system).values())
    rn, sn = sum(ref.values()), sum(system.values())
    return dict(reference=rn, system=sn, common=common,
                reference_only=rn-common, system_only=sn-common,
                precision=common/sn if sn else 0,
                recall=common/rn if rn else 0,
                f1=2*common/(rn+sn) if rn+sn else 0)


def main():
    out = ROOT / "audit"
    detector = Ab3P()
    summary = {"files": {}, "source_sha256": {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [ROOT / "ab3p/algorithm.py", ROOT / "ab3p/data.py"]}}
    totals = defaultdict(lambda: [Counter(), Counter()])
    unique = [set(), set()]
    differences = []
    live_diffs = []
    strat = defaultdict(Counter)
    char_count = non_ascii = 0
    started = time.perf_counter()
    for path in sorted((ROOT / "examples/input").glob("*.xml")):
        ref = read_annotations(ROOT / "examples/reference_output" / path.name)
        saved = read_annotations(ROOT / "examples/system_output" / path.name)
        rc, sc, fresh = Counter(), Counter(), Counter()
        category = "full" if "_full_" in path.name else "tiab"
        for di, doc in enumerate(documents(path)):
            docid = doc.findtext("id")
            for pi, passage in enumerate(doc.findall("passage")):
                key = di, docid, pi
                text = passage.findtext("text", "")
                char_count += len(text)
                non_ascii += sum(ord(c) > 127 for c in text)
                offset = int(passage.findtext("offset", "0"))
                r, s = Counter(ref[key]), Counter(saved[key])
                for count, dest in [(r, rc), (s, sc)]:
                    dest.update({key + item: n for item, n in count.items()})
                for i, pairs in enumerate([r, s]):
                    unique[i].update((docid, x[0], x[1]) for x in pairs)
                # Re-run every passage, also checking that saved outputs are current.
                found = predictions(detector, text, offset)
                f = Counter(as_relation(a) for a in found)
                fresh.update({key + item: n for item, n in f.items()})
                for a in found:
                    strat[a.strategy]["predicted"] += 1
                    strat[a.strategy]["matches_reference"] += as_relation(a) in r
                    strat[a.strategy]["precision_sum"] += a.precision
                if s != f:
                    live_diffs.append(dict(file=path.name, doc=docid, passage=pi,
                                           saved=list((s-f).elements()),
                                           current=list((f-s).elements())))
                if r != s:
                    differences.append(dict(file=path.name, doc=docid, passage=pi,
                        offset=offset, text=text,
                        reference_only=list((r-s).elements()),
                        system_only=list((s-r).elements()),
                        current=[a.__dict__ for a in found]))
        summary["files"][path.name] = metrics(rc, sc)
        summary["files"][path.name]["fresh_vs_saved"] = metrics(sc, fresh)
        for name in [category, "all"]:
            totals[name][0].update({(path.name,) + k: v for k, v in rc.items()})
            totals[name][1].update({(path.name,) + k: v for k, v in sc.items()})
        print(path.name, summary["files"][path.name], flush=True)
    summary["exact_occurrences"] = {k: metrics(*v) for k, v in totals.items()}
    summary["unique_document_sf_lf"] = metrics(Counter(unique[0]), Counter(unique[1]))
    summary["input_characters"] = char_count
    summary["non_ascii_characters"] = non_ascii
    summary["strategies_vs_reference"] = dict(strat)
    summary["passages_differing_from_saved"] = len(live_diffs)
    summary["example_runtime_seconds"] = time.perf_counter()-started
    r, s = totals["all"]
    unmatched_r, unmatched_s = r-s, s-r
    # Same SF occurrence, ignoring the LF span and text.
    anchor = lambda k: k[:4] + (k[4], k[6], k[8])
    ar, ass = [Counter(anchor(k) for k in count.elements())
               for count in [unmatched_r, unmatched_s]]
    summary["changed_lf_same_sf_occurrence"] = sum((ar & ass).values())
    gold = read_annotations(ROOT / "Ab3P-BioC/Ab3P_bioc_gold.xml")
    gold_exact, gold_pairs = Counter(), set()
    predicted_exact, predicted_pairs = Counter(), set()
    gold_diff = []
    for di, doc in enumerate(documents(ROOT / "Ab3P-BioC/Ab3P_bioc_corpus.xml")):
        docid = doc.findtext("id")
        for pi, p in enumerate(doc.findall("passage")):
            key = di, docid, pi
            r = Counter(gold[key])
            found = detector.find(p.findtext("text", ""), int(p.findtext("offset", "0")))
            s = Counter(as_relation(a) for a in found)
            gold_exact.update({key + item: n for item, n in r.items()})
            predicted_exact.update({key + item: n for item, n in s.items()})
            gold_pairs.update((docid, a[0], a[1]) for a in r)
            predicted_pairs.update((docid, a[0], a[1]) for a in s)
            if r != s:
                gold_diff.append(dict(doc=docid, passage=pi, text=p.findtext("text", ""),
                    gold_only=list((r-s).elements()), system_only=list((s-r).elements()),
                    current=[a.__dict__ for a in found]))
    summary["gold_exact_occurrences"] = metrics(gold_exact, predicted_exact)
    summary["gold_unique_document_sf_lf"] = metrics(Counter(gold_pairs), Counter(predicted_pairs))
    for filename, value in [("summary.json", summary), ("example_differences.json", differences),
                            ("fresh_vs_saved.json", live_diffs), ("gold_differences.json", gold_diff)]:
        (out / filename).write_text(json.dumps(value, indent=2, ensure_ascii=True), encoding="utf-8")
    with (out / "example_differences.tsv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["file", "doc", "passage", "side", "sf", "lf", "sf_offset", "lf_offset", "sf_length", "lf_length"])
        for d in differences:
            for side in ["reference_only", "system_only"]:
                for row in d[side]:
                    writer.writerow([d["file"], d["doc"], d["passage"], side] + list(row))
    print(json.dumps({k: v for k, v in summary.items() if k != "files"}, indent=2), flush=True)


if __name__ == "__main__":
    main()
