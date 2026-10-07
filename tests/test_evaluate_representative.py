"""Coordinate and occurrence checks for the saved C++ reference evaluator."""

from collections import Counter
import hashlib
import json
import xml.etree.ElementTree as ET

import pytest

from audit.evaluate_representative import byte_boundaries, cpp_span, evaluate, reference_relations
from ab3p.algorithm import Ab3P, _sequence_indices, tokenize


def test_passage_local_utf8_conversion_with_nonzero_base():
    text = "α 😀 café (CF)"
    base = 37
    boundaries = byte_boundaries(text)
    sf_start = text.index("CF")
    byte_start = len(text[:sf_start].encode("utf-8"))
    assert cpp_span(text, base, base + byte_start, 2, boundaries) == (base + sf_start, 2)
    assert cpp_span(text, base, base, 2, boundaries) == (base, 1)
    with pytest.raises(ValueError, match="invalid UTF-8"):
        cpp_span(text, base, base + 1, 1, boundaries)


def test_relations_preserve_duplicate_occurrences_and_reject_bad_text():
    text = "α receptor (AR)"
    base = 20
    lf_length = len("α receptor".encode("utf-8"))
    sf_offset = base + len("α receptor (".encode("utf-8"))
    passage = ET.Element("passage")
    for aid, label, offset, length in (("lf", "α receptor", base, lf_length),
                                        ("sf", "AR", sf_offset, 2)):
        ann = ET.SubElement(passage, "annotation", id=aid)
        ET.SubElement(ann, "location", offset=str(offset), length=str(length))
        ET.SubElement(ann, "text").text = label
    for rid in ("r1", "r2"):
        relation = ET.SubElement(passage, "relation", id=rid)
        ET.SubElement(relation, "node", role="LongForm", refid="lf")
        ET.SubElement(relation, "node", role="ShortForm", refid="sf")
    expected = ("AR", "α receptor", base + text.index("AR"), base, 2, len("α receptor"))
    assert reference_relations(passage, text, base) == Counter({expected: 2})
    passage.find("annotation/text").text = "wrong"
    with pytest.raises(ValueError, match="disagrees"):
        reference_relations(passage, text, base)


def test_embedded_parentheses_are_one_token_and_match_saved_challenge():
    text = "poly(dimethylsiloxane) (PDMS); Pam(3)CysSK(4) (P3C)"
    tokens = tokenize(text)
    assert "poly(dimethylsiloxane)" in [token.text for token in tokens]
    assert "Pam(3)CysSK(4)" in [token.text for token in tokens]
    assert [(item.sf, item.lf) for item in Ab3P().find(text)] == [
        ("PDMS", "poly(dimethylsiloxane)"), ("P3C", "Pam(3)CysSK(4)")]


def test_reversed_one_letter_and_c_locale_case_match_saved_challenge():
    assert ("A", "alpha") in [(item.sf, item.lf) for item in
                               Ab3P().find("A (alpha), B (beta), C (cells)")]
    assert not Ab3P().find("İstanbul receptor (IR)")


def test_token2_only_splits_ascii_blank():
    assert [token.text for token in tokenize("one\u00a0two three\u2009four five\nsix")] == [
        "one\u00a0two", "three\u2009four", "five\nsix"]


def test_group_counts_only_ascii_blank_in_unicode_short_form():
    result = Ab3P().find("the combination of CU and PTX (CU\u2009+\u2009PTX)")
    assert [(item.sf, item.lf) for item in result] == [
        ("CU\u2009+\u2009PTX", "CU and PTX")]


def test_token2_keeps_parenthetical_suffix_attached():
    for text in ("Medical Research Council (MRC)through",
                 "A kinase-anchoring protein (AKAP)95"):
        assert not Ab3P().find(text)
        assert tokenize(text)[-1].text.startswith("(")


def test_original_short_form_is_screened_before_swapped_orientation():
    assert not Ab3P().find("N+ (425 mg/L of yeast assimilable nitrogen)")
    assert not Ab3P().find("P5 (P<0.05)")


def test_sequence_run_must_start_at_first_marker():
    assert _sequence_indices(["a", "b", "c"]) == {0, 1, 2}
    assert _sequence_indices(["b", "c"]) == set()


def test_medpost_abbreviation_and_nbsp_sentence_boundaries():
    detector = Ab3P()
    cases = [
        ("across the contiguous U.S. (CONUS)", "CONUS", "contiguous U.S."),
        ("i.e. the activation energy (Ea)", "Ea", "i.e. the activation energy"),
        ("G.P. (Gaio Paradossi)", "G.P.", "Gaio Paradossi"),
        ("fluoroquinolones.\u00a0Methicillin-resistant Staphylococcus aureus (MRSA)",
         "MRSA", "fluoroquinolones.\u00a0Methicillin-resistant Staphylococcus aureus"),
    ]
    for text, sf, lf in cases:
        assert (sf, lf) in [(item.sf, item.lf) for item in detector.find(text)]


def test_source_span_can_cross_a_line_break():
    found = Ab3P().find("gamma\r delta (GD)")
    assert [(item.sf, item.lf) for item in found] == [("GD", "gamma\r delta")]


def test_manifest_pairs_recovered_shards_and_reports_missing_status(tmp_path):
    corpus = tmp_path
    for directory in ("manifests", "input/development", "reference_cpp/outputs/development"):
        (corpus / directory).mkdir(parents=True)
    source = ET.Element("collection")
    for docid, text in (("d1", "α receptor (AR)"), ("d2", "empty")):
        doc = ET.SubElement(source, "document")
        ET.SubElement(doc, "id").text = docid
        passage = ET.SubElement(doc, "passage")
        ET.SubElement(passage, "offset").text = "17"
        ET.SubElement(passage, "text").text = text
    input_rel = "input/development/shard.xml"
    input_path = corpus / input_rel
    ET.ElementTree(source).write(input_path, encoding="utf-8")
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    rows = [dict(file=input_rel, file_sha256=digest(input_path), index=i,
                 document_id=docid, partition="development", cohort="pubmed")
            for i, docid in enumerate(("d1", "d2"))]
    manifest = corpus / "manifests/inputs.jsonl"
    manifest.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    run = dict(input_manifest_sha256=digest(manifest), fingerprint="test")
    (corpus / "reference_cpp/run.json").write_text(json.dumps(run), encoding="utf-8")
    statuses = []
    for i, docid in enumerate(("d1", "d2")):
        output = ET.Element("collection")
        output_doc = ET.SubElement(output, "document")
        ET.SubElement(output_doc, "id").text = docid
        passage = ET.SubElement(output_doc, "passage")
        ET.SubElement(passage, "offset").text = "17"
        if i == 0:
            for aid, label, offset, length in (("l", "α receptor", 17, 11),
                                               ("s", "AR", 30, 2)):
                ann = ET.SubElement(passage, "annotation", id=aid)
                ET.SubElement(ann, "location", offset=str(offset), length=str(length))
                ET.SubElement(ann, "text").text = label
            relation = ET.SubElement(passage, "relation")
            ET.SubElement(relation, "node", role="LongForm", refid="l")
            ET.SubElement(relation, "node", role="ShortForm", refid="s")
        output_rel = f"reference_cpp/outputs/development/recovered_{i}.xml"
        output_path = corpus / output_rel
        ET.ElementTree(output).write(output_path, encoding="utf-8")
        statuses.append(dict(input_path=input_rel, input_index=i, document_id=docid,
                             input_sha256=digest(input_path), status="success",
                             output_path=output_rel, output_index=0,
                             output_sha256=digest(output_path)))
    status_path = corpus / "reference_cpp/documents.jsonl"
    status_path.write_text("".join(json.dumps(row) + "\n" for row in statuses), encoding="utf-8")
    result = evaluate(corpus, "development", None)
    assert result["failures"] == []
    assert result["counts"]["all"]["reference"] == 1
    assert result["counts"]["all"]["documents"] == 2
    status_path.write_text(json.dumps(statuses[0]) + "\n", encoding="utf-8")
    result = evaluate(corpus, "development", None)
    assert result["counts"]["all"]["documents"] == 1
    assert result["failures"][0]["reason"] == "missing status"
