from ab3p.algorithm import Ab3P, candidates, tokenize


def test_tokenize_offsets():
    ts = tokenize("alpha beta (AB)")
    assert [(x.text, x.start) for x in ts] == [("alpha", 0), ("beta", 6), ("(", 11), ("AB", 12), (")", 14)]


def test_common_pair():
    found = Ab3P().find("central nervous system (CNS)")
    assert len(found) == 1
    assert found[0].lf == "central nervous system"
    assert found[0].sf == "CNS"
    assert found[0].lf_offset == 0
    assert found[0].sf_offset == 24


def test_nested_parenthetical_pair():
    found = Ab3P().find("heat-induced antigen (epitope) retrieval (HIER)")
    assert [(item.sf, item.lf) for item in found] == [
        ("HIER", "heat-induced antigen (epitope) retrieval")
    ]


def test_reversed_url_pair():
    found = Ab3P().find("Gene ontology analysis used METASCAPE (https://metascape.org/)")
    assert [(item.sf, item.lf) for item in found] == [
        ("METASCAPE", "https://metascape.org/")
    ]


def test_parenthesized_citation_is_not_reversed_pair():
    found = Ab3P().find(
        "metabolic alterations are frequent in AD "
        "(Gonzalez-Dominguez et al., )"
    )
    assert not any(
        item.sf == "AD" and "Gonzalez-Dominguez" in item.lf
        for item in found
    )
