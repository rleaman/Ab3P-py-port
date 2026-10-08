"""Draw reproducible agent-review samples from the supplied gold corpus."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from ab3p.algorithm import Ab3P
from audit.compare_ab3p import as_relation, documents, read_annotations


def draw(seed: int, per_class: int, random_passages: int) -> dict:
    inp = ROOT / "Ab3P-BioC/Ab3P_bioc_corpus.xml"
    gold_path = ROOT / "Ab3P-BioC/Ab3P_bioc_gold.xml"
    gold = read_annotations(gold_path)
    detector = Ab3P()
    pools = {"gold_only": [], "python_only": [], "shared": [],
             "source_passage": [], "abstract_passage": []}
    for di, doc in enumerate(documents(inp)):
        docid = doc.findtext("id")
        for pi, passage in enumerate(doc.findall("passage")):
            source = passage.findtext("text", "")
            base = int(passage.findtext("offset", "0"))
            reference = Counter(gold[di, docid, pi])
            predicted = Counter(as_relation(a) for a in detector.find(source, base))
            identity = dict(document_index=di, document_id=docid, passage_index=pi,
                            passage_offset=base)
            pools["source_passage"].append(dict(identity, text=source))
            if pi == 1:
                pools["abstract_passage"].append(dict(identity, text=source))
            for kind, occurrences in (("gold_only", reference - predicted),
                                      ("python_only", predicted - reference),
                                      ("shared", reference & predicted)):
                for sf, lf, sf_offset, lf_offset, sf_length, lf_length in occurrences.elements():
                    left = max(0, min(sf_offset, lf_offset) - base - 100)
                    right = min(len(source), max(sf_offset + sf_length,
                                                 lf_offset + lf_length) - base + 100)
                    pools[kind].append(dict(identity, sf=sf, lf=lf,
                                            sf_offset=sf_offset, lf_offset=lf_offset,
                                            sf_length=sf_length, lf_length=lf_length,
                                            context=source[left:right]))
    rng = random.Random(seed)
    selections = {}
    for kind, number in (("gold_only", per_class), ("python_only", per_class),
                         ("shared", per_class), ("source_passage", random_passages),
                         ("abstract_passage", random_passages)):
        selections[kind] = rng.sample(pools[kind], min(number, len(pools[kind])))
    return dict(seed=seed, per_class=per_class, random_passages=random_passages,
                input_sha256=hashlib.sha256(inp.read_bytes()).hexdigest(),
                gold_sha256=hashlib.sha256(gold_path.read_bytes()).hexdigest(),
                algorithm_sha256=hashlib.sha256((ROOT / "ab3p/algorithm.py").read_bytes()).hexdigest(),
                pool_sizes={kind: len(items) for kind, items in pools.items()},
                selections=selections)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20261007)
    parser.add_argument("--per-class", type=int, default=8)
    parser.add_argument("--random-passages", type=int, default=10)
    parser.add_argument("--output", type=Path, default=ROOT / "audit/gold_review_sample.json")
    args = parser.parse_args()
    if args.per_class < 1 or args.random_passages < 1:
        parser.error("sample sizes must be positive")
    report = draw(args.seed, args.per_class, args.random_passages)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=True, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(dict(seed=report["seed"], pool_sizes=report["pool_sizes"],
                          sample_sizes={key: len(value) for key, value in
                                        report["selections"].items()}), indent=2))


if __name__ == "__main__":
    main()
