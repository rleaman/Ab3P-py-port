import hashlib
import json

import pytest

from corpus import expand_reserve, prepare


def test_reserve_continuation_follows_inspected_expansion():
    spec = expand_reserve.load_addendum()
    prior = prepare.load_log(expand_reserve.PRIOR_CACHE / "selection.jsonl")
    fingerprint = hashlib.sha256(expand_reserve.ADDENDUM.read_bytes()).hexdigest()
    for cohort in ("pubmed", "pmc"):
        ordinal = spec["continuation"][cohort]["first_ordinal"]
        assert ordinal == max(row["ordinal"] for row in prior
                              if row["cohort"] == cohort) + 1
        first = {"cohort": cohort, "ordinal": ordinal,
                 "id": prepare.candidate(cohort, ordinal, spec),
                 "protocol_sha256": fingerprint}
        expand_reserve.validate_selection_log(spec, [first])
    with pytest.raises(RuntimeError, match="misordered"):
        expand_reserve.validate_selection_log(spec, [first, first])


def test_reserve_blocks_inspected_expansion_family():
    first = json.loads((expand_reserve.PRIOR / "manifests/articles.jsonl")
                       .open(encoding="utf-8").readline())
    assert set(first["family_keys"]) <= expand_reserve.existing_keys()
