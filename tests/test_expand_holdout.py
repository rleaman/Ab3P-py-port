import hashlib
import json

import pytest

from corpus import expand_holdout, prepare
from corpus.expand_holdout import family_status, link_keys, validate_selection_log


def test_cross_reference_keys_are_canonical():
    assert link_keys({"pmid": "000123", "pmcid": "PMC000456",
                      "doi": "https://doi.org/ABC.DEF"}) == {
        "pmid:123", "pmcid:PMC456", "doi:abc.def"}


def test_expansion_rejects_old_family_and_same_cohort_duplicate():
    old = {"pmid:123", "pmcid:PMC456"}
    seen_pubmed = {"doi:10/example"}
    assert family_status({"doi:10/new", "pmcid:PMC456"}, old, seen_pubmed) == (
        "existing_or_excluded_family")
    assert family_status({"doi:10/example"}, old, seen_pubmed) == "duplicate_new_family"
    assert family_status({"doi:10/example"}, old, set()) == "selected"


def test_expansion_draw_log_requires_exact_frozen_continuation():
    spec = json.loads(expand_holdout.ADDENDUM.read_text(encoding="utf-8"))
    fingerprint = hashlib.sha256(expand_holdout.ADDENDUM.read_bytes()).hexdigest()
    ordinal = spec["continuation"]["pubmed"]["first_ordinal"]
    first = {"cohort": "pubmed", "ordinal": ordinal,
             "id": prepare.candidate("pubmed", ordinal, spec),
             "protocol_sha256": fingerprint}
    validate_selection_log(spec, [first])
    with pytest.raises(RuntimeError, match="misordered"):
        validate_selection_log(spec, [first, first])
