"""Strategy contracts and reduced regressions from the C++ comparison."""

from types import SimpleNamespace

import pytest

from ab3p.algorithm import Ab3P, Token
from ab3p.data import load_precisions
from ab3p.matching import match_strategy


@pytest.fixture(scope="module")
def detector():
    return Ab3P()


@pytest.mark.parametrize("text,sf,lf,strategy", [
    ("transactivator of transcription (Tat)", "Tat", "transactivator of transcription", "WithinWrdFWrdSkp"),
    ("cortex (ctx)", "ctx", "cortex", "WithinWrdFLet"),
    ("interleukin (IL)", "IL", "interleukin", "WithinWrdFLet"),
    ("ionized calcium binding adaptor molecule-1 (ibal)", "ibal",
     "ionized calcium binding adaptor molecule-1", "AnyLet"),
    ("supraoptic nucleus, retrochiasmatic (SOR)", "SOR",
     "supraoptic nucleus, retrochiasmatic", "WithinWrdFWrdSkp"),
])
def test_repaired_expansions_and_offsets(detector, text, sf, lf, strategy):
    [result] = detector.find(text, offset=73)
    assert (result.sf, result.lf, result.strategy) == (sf, lf, strategy)
    assert result.sf_offset == 73 + text.index(sf)
    assert result.lf_offset == 73 + text.index(lf)


@pytest.mark.parametrize("text", [
    "alpha beta completely unrelated tail (ABC)",
    "Nuclei were analyzed and counted using a fluorescence microscope (Zeiss).",
])
def test_rejects_spurious_expansions(detector, text):
    assert detector.find(text) == []


def test_low_scoring_cpp_match_is_kept_by_default(detector):
    text = "channel1 (C1)"
    [result] = detector.find(text)
    assert result.precision == 0.493922
    assert Ab3P(min_precision=0.9).find(text) == []
    # A definition cue must not bypass an explicitly requested cutoff.
    assert Ab3P(min_precision=0.9).find("This stands for " + text) == []


@pytest.mark.parametrize("cutoff", [-0.1, 1.1, float("nan")])
def test_invalid_precision_cutoff(cutoff):
    with pytest.raises(ValueError, match="min_precision"):
        Ab3P(min_precision=cutoff)


# These minimal cases exercise the distinct C++ predicates, including trailing
# skipped words. The word list makes the dictionary conditions explicit.
STRATEGY_CASES = [
    ("FirstLetOneChSF", "C", "cells", True),
    ("FirstLet", "AB", "alpha beta", True),
    ("FirstLetGen", "AB", "alpha-beta", True),
    ("FirstLetGen2", "A2", "alpha 2", True),
    ("FirstLetGenS", "ABs", "alpha betas", True),
    ("FirstLetGenStp", "AB", "alpha of beta", True),
    ("FirstLetGenStp2", "AB", "alpha of the beta", True),
    ("FirstLetGenSkp", "AB", "alpha big beta", True),
    ("WithinWrdWrd", "AC", "alpha microcell", True),
    ("WithinWrdFWrd", "MC", "microcell", True),
    ("WithinWrdFWrdSkp", "MCA", "microcell big alpha", True),
    ("WithinWrdLet", "AR", "alpha tryptophan", True),
    ("WithinWrdFLet", "CTX", "cortex", True),
    ("WithinWrdFLetSkp", "CTXA", "cortex big alpha", True),
    ("ContLet", "AL", "alpha", True),
    ("ContLetSkp", "ALB", "alpha big beta", True),
    ("AnyLet", "AR", "alpha tryptophan", True),
    ("FirstLetGen", "AB", "alpha beta", False),
    ("FirstLet", "AB", "alpha-beta", False),
    ("FirstLetGenS", "Abs", "alpha betas", False),
    ("FirstLetGenS", "ABs", "alpha betas extra", False),
    ("FirstLetGenStp", "AB", "alpha big beta", False),
    ("FirstLetGenStp2", "AB", "alpha of beta", False),
    ("FirstLetGenSkp", "AB", "alpha beta", False),
    ("FirstLetGenStp", "AB", "alpha beta of", True),
    ("WithinWrdFWrd", "AC", "alpha microcell", False),
    ("WithinWrdFWrd", "TNF", "tumor necrosis factor", False),
    ("WithinWrdWrd", "AR", "alpha tryptophan", False),
    ("WithinWrdWrd", "ar", "alpha tryptophan", False),
    ("WithinWrdFLet", "AR", "alpha tryptophan", False),
    ("WithinWrdLet", "CTX", "cortex tail", False),
    ("ContLet", "CTX", "cortex", False),
    ("ContLet", "TNF", "tumor necrosis factor", False),
    ("ContLetSkp", "AL", "alpha extra", True),
    ("AnyLet", "ABC", "alpha beta completely extra tail", False),
    ("AnyLet", "Z", "analyzed", False),
]


@pytest.mark.parametrize("strategy,sf,lf,accepted", STRATEGY_CASES)
def test_strategy_contract(strategy, sf, lf, accepted):
    data = SimpleNamespace(words={"cell"}, stopwords={"of", "the"}, one_char_lfs={"cells"})
    tokens = [Token(word, i) for i, word in enumerate(lf.split())]
    result = match_strategy(strategy, sf, tokens, data)
    assert (result is not None) == accepted
    if accepted:
        assert result == 0


def test_every_configured_strategy_has_a_positive_contract_case():
    _, groups = load_precisions()
    configured = {strategy for strategies in groups.values() for strategy in strategies}
    assert configured == {strategy for strategy, _, _, accepted in STRATEGY_CASES if accepted}


def test_search_backtracks_when_nearest_alignment_fails():
    data = SimpleNamespace(words=set(), stopwords=set(), one_char_lfs=set())
    # The nearest b is internal to "bob"; retrying it at the word's beginning
    # is necessary for FirstLet to succeed.
    tokens = [Token("alpha", 0), Token("bob", 6)]
    assert match_strategy("FirstLet", "AB", tokens, data) == 0


def test_subword_dictionary_is_used_for_uppercase_and_lowercase():
    data = SimpleNamespace(words=set(), stopwords=set(), one_char_lfs=set())
    tokens = [Token("microcell", 0)]
    for sf in ["MC", "mc", "mC"]:
        assert match_strategy("WithinWrdFWrd", sf, tokens, data) is None
    data.words.add("cell")
    for sf in ["MC", "mc", "mC"]:
        assert match_strategy("WithinWrdFWrd", sf, tokens, data) == 0
