"""Guard against inflated compatibility scores from lost duplicates or spans."""

from collections import Counter
from types import SimpleNamespace

import pytest
from lxml import etree

from ab3p.algorithm import Abbreviation
from audit.compare_ab3p import metrics
from audit.evaluate_current import evaluate_file


def test_metrics_preserve_multiplicity_and_offsets():
    first = ("AB", "alpha beta", 12, 0, 2, 10)
    shifted = ("AB", "alpha beta", 13, 0, 2, 10)
    result = metrics(Counter({first: 2}), Counter({first: 1, shifted: 1}))
    assert result["common"] == 1
    assert result["reference_only"] == result["system_only"] == 1
    assert result["precision"] == result["recall"] == 0.5


def test_empty_predictions_cannot_pass_a_target():
    assert metrics(Counter(), Counter())["precision"] == 0
    assert metrics(Counter(), Counter())["recall"] == 0


def test_evaluation_uses_current_detector_and_checks_reference_coverage(tmp_path):
    source = tmp_path / "input.xml"
    reference = tmp_path / "reference.xml"
    source.write_text("<collection><document><id>doc</id><passage><offset>0</offset>"
                      "<text>alpha beta (AB)</text></passage></document></collection>", encoding="utf-8")
    tree = etree.parse(str(source))
    passage = tree.find(".//passage")
    for aid, role, value, offset in [("S", "ShortForm", "AB", 12), ("L", "LongForm", "alpha beta", 0)]:
        a = etree.SubElement(passage, "annotation", id=aid)
        etree.SubElement(a, "location", offset=str(offset), length=str(len(value)))
        etree.SubElement(a, "text").text = value
    relation = etree.SubElement(passage, "relation", id="R")
    etree.SubElement(relation, "node", refid="S", role="ShortForm")
    etree.SubElement(relation, "node", refid="L", role="LongForm")
    tree.write(str(reference), encoding="utf-8")
    detector = SimpleNamespace(find=lambda text, offset: [
        Abbreviation("AB", "alpha beta", 12, 0, "FirstLet", 0.99818)])
    result, counts, differences = evaluate_file(source, reference, detector)
    assert result["common"] == result["reference"] == result["system"] == 1
    assert counts["documents"] == 1
    assert differences == []
    extra = etree.SubElement(tree.find("document"), "passage")
    etree.SubElement(extra, "offset").text = "100"
    tree.write(str(reference), encoding="utf-8")
    with pytest.raises(ValueError, match="absent from input"):
        evaluate_file(source, reference, detector)
