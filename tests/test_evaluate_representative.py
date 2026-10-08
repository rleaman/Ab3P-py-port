"""Coordinate and occurrence checks for the saved C++ reference evaluator."""

from collections import Counter
import hashlib
import json
import xml.etree.ElementTree as ET

import pytest

from audit.evaluate_representative import (article_cluster_uncertainty, byte_boundaries,
                                           cpp_span, evaluate, family_clusters, reference_relations,
                                           uncertainty_from_sufficient_stats)
from ab3p.algorithm import Ab3P, _c_has_upper, _candidate_ok, _lf_ok, _sequence_indices, tokenize


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


def test_utf8_conversion_uses_each_passages_own_base_and_text():
    first, second = "α receptor (AR)", "😀 café receptor (CR)"
    first_base, second_base = 0, 100
    for source, base, form in ((first, first_base, "AR"),
                               (second, second_base, "CR")):
        local = source.index(form)
        byte_start = len(source[:local].encode("utf-8"))
        assert cpp_span(source, base, base + byte_start, len(form)) == (
            base + local, len(form))
        with pytest.raises(ValueError, match="invalid UTF-8"):
            cpp_span(source, base, base + 1, 1)


def test_article_cluster_uncertainty_preserves_ratio_denominators():
    report = article_cluster_uncertainty([
        Counter(reference=2, python=1, shared=1),
        Counter(reference=1, python=2, shared=1),
    ])
    assert report["clusters"] == 2
    assert report["prediction_agreement"]["point"] == 2 / 3
    assert report["recovery"]["point"] == 2 / 3
    assert report["prediction_agreement"]["standard_error"] > 0
    pieces = [article_cluster_uncertainty([row])["sufficient_stats"] for row in
              (Counter(reference=2, python=1, shared=1),
               Counter(reference=1, python=2, shared=1))]
    assert uncertainty_from_sufficient_stats(Counter(pieces[0]) + Counter(pieces[1]))[
        "prediction_agreement"]["standard_error"] == report[
            "prediction_agreement"]["standard_error"]


def test_linked_pubmed_pmc_records_form_one_article_family_cluster():
    articles = [
        dict(file="pubmed.xml", index=0, partition="development",
             family_keys=["pmid:1", "doi:shared"]),
        dict(file="pmc.xml", index=0, partition="development",
             family_keys=["doi:shared", "pmcid:PMC1"]),
        dict(file="pmc.xml", index=1, partition="development",
             family_keys=["pmcid:PMC1", "pmid:2"]),
        dict(file="pubmed.xml", index=1, partition="development",
             family_keys=["pmid:3"]),
        dict(file="holdout.xml", index=0, partition="holdout",
             family_keys=["doi:shared"]),
    ]
    clusters = family_clusters(articles, "development")
    assert len(set(clusters.values())) == 2
    assert clusters[("pubmed.xml", 0)] == clusters[("pmc.xml", 0)]
    assert clusters[("pmc.xml", 0)] == clusters[("pmc.xml", 1)]
    assert clusters[("pubmed.xml", 1)] != clusters[("pmc.xml", 1)]
    with pytest.raises(ValueError, match="duplicate article manifest"):
        family_clusters([articles[0], articles[0]], "development")


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


def test_token2_keeps_leading_bracket_attached_to_first_word():
    # Saved PubMed development 2257799 and 22623039: C++ emits neither pair.
    titles = (
        "[Transcutaneous electric nerve stimulation (TENS) in chronic neuralgiform facial pain].",
        "[Cardiopulmonary Exercise Testing (CPET) in severe COPD--a multicentre comparison of two test protocols].",
    )
    detector = Ab3P()
    for title in titles:
        assert tokenize(title)[0].text.startswith("[")
        assert tokenize(title)[0].text != "["
        assert detector.find(title) == []


def test_candidate_test_rejects_three_leading_digits_before_a_letter():
    # Source: AbbrvE.C::Test early prefix rejection. Saved development C++
    # includes 54d but excludes 135d and 145d in PMC11266307.
    assert _candidate_ok("54d")
    assert not _candidate_ok("135d")
    assert not _candidate_ok("145d")


def test_nested_short_form_requires_isolated_outer_opener():
    # PubMed development 21895015 has Co(CH(3))(2)I and no CH(3) reference
    # pair; the outer group is embedded in a chemical token in token2.
    chemical = "cobalt(III) dimethyl complex, cis,mer-(PMe(3))(3)Co(CH(3))(2)I"
    assert not any(item.sf == "CH(3)" for item in Ab3P().find(chemical))
    # PubMed development 16785555 does contain this nested short form.
    valid = "secretory group V phospholipase A(2) (gVPLA(2))"
    assert any(item.sf == "gVPLA(2)" for item in Ab3P().find(valid))


def test_lf_ok_uses_c_locale_byte_case_rules():
    # Source-derived from AbbrStra.C::lf_ok; no live C++ probe was run.
    assert not _lf_ok("Ab", "ab")
    assert _lf_ok("AÄ", "aä")
    assert _lf_ok("Iİ", "ii")


def test_swapped_orientation_uses_c_locale_uppercase_bytes():
    # Source-derived from StratUtil::exist_upperal; no live C++ probe was run.
    assert _c_has_upper("aÉ") is False
    assert _c_has_upper("aΔ") is False
    assert _c_has_upper("aZÉ") is True


@pytest.mark.parametrize("prefix", [
    "β", "é", "e\u0301", "\u00a0", "\u2011", "⁺", "₂", "“”", "😀",
    "İ", "Straße", "αβ αβ",
])
def test_generated_unicode_prefixes_keep_two_exact_occurrence_spans(prefix):
    # Deterministic Python and coordinate contract test; no C++ run is implied.
    text = f"{prefix} alpha beta (AB) {prefix} alpha beta (AB)"
    base = 37
    found = Ab3P().find(text, base)
    assert len(found) == 2
    for item in found:
        assert item.sf == "AB" and item.lf == "alpha beta"
        for value, offset in ((item.sf, item.sf_offset), (item.lf, item.lf_offset)):
            local = offset - base
            assert text[local:local + len(value)] == value
            byte_start = len(text[:local].encode("utf-8"))
            byte_length = len(value.encode("utf-8"))
            assert cpp_span(text, base, base + byte_start, byte_length) == (
                offset, len(value))


@pytest.mark.parametrize("surface", [
    "β", "café", "cafe\u0301", "non\u00a0break", "non\u2011break",
    "x⁺", "H₂O", "“quoted”", "😀", "İstanbul", "Straße",
])
def test_local_utf8_span_conversion_preserves_unicode_surface(surface):
    text = f"before {surface} after"
    base = 211
    local = text.index(surface)
    byte_start = len(text[:local].encode("utf-8"))
    byte_length = len(surface.encode("utf-8"))
    offset, length = cpp_span(text, base, base + byte_start, byte_length)
    assert (offset, length) == (base + local, len(surface))
    assert text[offset - base:offset - base + length] == surface


def test_original_short_form_is_screened_before_swapped_orientation():
    assert not Ab3P().find("N+ (425 mg/L of yeast assimilable nitrogen)")
    assert not Ab3P().find("P5 (P<0.05)")


def test_sequence_run_must_start_at_first_marker():
    assert _sequence_indices(["a", "b", "c"]) == {0, 1, 2}
    assert _sequence_indices(["b", "c"]) == set()


def test_dotted_initial_and_nbsp_sentence_boundaries():
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


def test_saved_reference_splits_at_unavailable_medpost_abbreviations():
    # Development 23732584, 36175452 and 25395434: these Python extras
    # disappear when the unverified MedPost ABB list is not applied. The
    # returned Linux run records that app.parent/MedPost was absent.
    detector = Ab3P()
    assert not detector.find("St. George's Respiratory Questionnaire (SGRQ)")
    assert not detector.find("Treponema pallidum subsp. pallidum (TPA)")
    assert not any(item.sf == "LafC" for item in detector.find(
        "'Candidatus Liberibacter africanus subsp. capensis' (LafC)"))


def test_single_dotted_initial_before_parenthesis_is_sentence_boundary():
    # Saved PubMed development 20645769 has no L. / Labiatae pair. MPtok.C
    # tok_14 does not attach a single-letter period before an opening paren.
    detector = Ab3P()
    assert not any(item.sf == "L." for item in detector.find(
        "Chenopodium murale L. (Chenopodiaceae), Prunus serotina L. (Labiatae)"))
    assert ("G.P.", "Gaio Paradossi") in [
        (item.sf, item.lf) for item in detector.find("G.P. (Gaio Paradossi)")]
    assert ("HibID", "H. influenzae type b invasive disease") in [
        (item.sf, item.lf) for item in detector.find(
            "H. influenzae type b invasive disease (HibID)")]
    # Saved example 41580393 includes this unusual C++ pair after an initial.
    assert ("M.", "https://BioRender.com/mls61se") in [
        (item.sf, item.lf) for item in detector.find(
            "Muhlhofer, M. (https://BioRender.com/mls61se)")]


def test_source_span_can_cross_a_line_break():
    found = Ab3P().find("gamma\r delta (GD)")
    assert [(item.sf, item.lf) for item in found] == [("GD", "gamma\r delta")]


def test_saved_holdout_newlines_are_sentence_boundaries():
    # The first frozen holdout is now a regression corpus. C++ has no AEC
    # pair spanning the source newline, and its EGF LF starts after it.
    detector = Ab3P()
    assert not any(item.sf == "AEC" for item in detector.find(
        "absolute\neosinophil count (AEC)"))
    found = detector.find("(eos/hpf),\nepidermal growth factor (EGF)")
    assert ("EGF", "epidermal growth factor") in [
        (item.sf, item.lf) for item in found]


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
    assert result["full_manifest_missing_statuses"] == 0
    assert result["full_manifest_failure_statuses"] == 0
    assert "ab3p/algorithm.py" in result["implementation_sha256"]
    assert result["target_met"] is None
    failed = dict(statuses[1], status="failed", reason="crash")
    status_path.write_text("".join(json.dumps(row) + "\n" for row in
                                   [statuses[0], failed]), encoding="utf-8")
    result = evaluate(corpus, "development", Ab3P(), target=0.999)
    assert result["full_manifest_failure_statuses"] == 1
    assert result["target_met"] is False
    status_path.write_text(json.dumps(statuses[0]) + "\n", encoding="utf-8")
    result = evaluate(corpus, "development", None, target=0.999)
    assert result["counts"]["all"]["documents"] == 1
    assert result["failures"][0]["reason"] == "missing status"
    assert result["full_manifest_missing_statuses"] == 1
    assert result["target_met"] is False
    extra = dict(statuses[0], input_index=99)
    status_path.write_text("".join(json.dumps(row) + "\n" for row in
                                   [*statuses, extra]), encoding="utf-8")
    with pytest.raises(ValueError, match="absent from manifest"):
        evaluate(corpus, "development", None)
