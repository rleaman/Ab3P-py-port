"""Deterministic synthetic BioC cases; no C++ expectations are asserted."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

CASES = [
    ("FirstLetOneChSF", "cells (C)", "single-character short form"),
    ("FirstLet", "alpha beta (AB)", "first letters"),
    ("FirstLetGen", "alpha-beta (AB)", "punctuated first letters"),
    ("FirstLetGen2", "alpha 2 (A2)", "number-containing definition"),
    ("FirstLetGenS", "alpha betas (ABs)", "plural ending"),
    ("FirstLetGenStp", "alpha of beta (AB)", "stop word"),
    ("FirstLetGenStp2", "alpha of the beta (AB)", "two stop words"),
    ("FirstLetGenSkp", "alpha big beta (AB)", "skipped word"),
    ("WithinWrdWrd", "alpha microcell (AC)", "internal letter in later word"),
    ("WithinWrdFWrd", "microcell (MC)", "internal letter in first word"),
    ("WithinWrdFWrdSkp", "microcell big alpha (MCA)", "internal letter plus skipped word"),
    ("WithinWrdLet", "alpha tryptophan (AR)", "internal letter"),
    ("WithinWrdFLet", "cortex (CTX)", "letters in first word"),
    ("WithinWrdFLetSkp", "cortex big alpha (CTXA)", "letters plus skipped word"),
    ("ContLet", "alpha (AL)", "consecutive letters"),
    ("ContLetSkp", "alpha big beta (ALB)", "consecutive letters with skip"),
    ("AnyLet", "alpha tryptophan (AR)", "general letter matching"),
    ("FirstLetGen_fail", "alpha beta (XZ)", "failing definition"),
    ("ambiguous_backtrack", "alpha alpha beta (AAB)", "ambiguous repeated initial"),
    ("reverse_orientation", "AB (alpha beta)", "short form first"),
    ("nested_chemical", "poly(dimethylsiloxane) (PDMS); Pam(3)CysSK(4) (P3C)", "nested chemical parentheses"),
    ("sequence_list", "A (alpha), B (beta), C (cells)", "sequence suppression candidate"),
    ("initial_break", "J. R. Smith described alpha beta (AB).", "initials and sentence boundaries"),
    ("window", "alpha beta (AB), alpha gamma (AG); beta gamma (BG)", "candidate window interaction"),
    ("repeat", "tumor necrosis factor (TNF) and tumor necrosis factor (TNF)", "repeated occurrence"),
    ("greek", "β-cell receptor (BCR) and α-synuclein (AS)", "Greek letters"),
    ("combining", "cafe\u0301 receptor (CR) and café receptor (CR)", "decomposed and composed forms"),
    ("nbsp", "alpha\u00a0beta (AB)", "non-breaking space"),
    ("punctuation", "alpha–beta (AB); alpha—beta (AB); alpha‘beta’ (AB)", "punctuation variants"),
    ("superscript", "interleukin² receptor (IR)", "superscript"),
    ("astral", "🧬 alpha beta (AB)", "astral prefix"),
    ("case_mapping", "İstanbul receptor (IR); straße protein (SP)", "length-changing case mappings"),
    ("xml_controls", "alpha\t beta (AB)\n gamma\r delta (GD)", "XML-valid tab, newline and carriage return"),
    ("passage_types", "Table: alpha beta (AB)", "table, caption, reference and supplement passage handling"),
]


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def xml_bytes(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True,
                       short_empty_elements=False).replace(b"\r", b"&#13;")


def generate(bundle: Path) -> tuple[list[dict], list[dict]]:
    root = ET.Element("collection")
    ET.SubElement(root, "source").text = "Synthetic Ab3P phase 1 challenge"
    ET.SubElement(root, "date").text = "20261007"
    ET.SubElement(root, "key").text = "collection.key"
    intents = []
    inputs = []
    for index, (name, value, intent) in enumerate(CASES):
        docid = f"CHALLENGE_{index + 1:03d}"
        doc = ET.SubElement(root, "document")
        ET.SubElement(doc, "id").text = docid
        passages = []
        base = 0
        values = [("title", "Challenge case: " + name + "."), ("abstract", value)]
        if name == "passage_types":
            values += [("table", "Table: gamma delta (GD)"),
                       ("fig_caption", "Caption: epsilon zeta (EZ)"),
                       ("ref", "Reference: eta theta (ET)"),
                       ("supplement", "Supplement: iota kappa (IK)")]
        for pindex, (typ, text) in enumerate(values):
            passage = ET.SubElement(doc, "passage")
            ET.SubElement(passage, "infon", key="type").text = typ
            ET.SubElement(passage, "offset").text = str(base)
            ET.SubElement(passage, "text").text = text
            passages.append({"index": pindex, "canonical_offset": base, "source_offset": None,
                             "source_offset_unit": "synthetic", "type": typ,
                             "length_codepoints": len(text), "text_sha256": digest(text.encode("utf-8"))})
            base += len(text) + 1
        intents.append({"document_id": docid, "case": name, "intent": intent,
                        "provenance": "synthetic from corpus/make_challenge.py and tests/test_matching.py",
                        "cpp_expectation": "unknown"})
        inputs.append({"cohort": "challenge", "partition": "challenge", "document_id": docid,
                       "file": "input/challenge/challenge_00001.xml", "index": index,
                       "passages": passages})
    path = bundle / "input/challenge/challenge_00001.xml"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = xml_bytes(root)
    path.write_bytes(data)
    for row in inputs:
        row["file_sha256"] = digest(data)
    (bundle / "manifests/challenge_intent.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in intents), encoding="utf-8")
    return inputs, intents
