import json

import pytest

from audit import evaluate_final_reserve
from audit.freeze_reserve import INPUT_FREEZE, check_input_freeze
from audit.evaluate_representative import sha


def test_reserve_input_package_matches_precomparison_freeze():
    assert check_input_freeze() == sha(INPUT_FREEZE)


def test_reserve_expansion_cannot_reuse_inspected_family(tmp_path, monkeypatch):
    bundles = [tmp_path / name for name in ("parent", "inspected", "new")]
    for path in bundles:
        (path / "manifests").mkdir(parents=True)
    for path, key in zip(bundles, ("pmid:1", "pmid:2", "pmid:2")):
        (path / "manifests/articles.jsonl").write_text(
            json.dumps({"document_id": key, "family_keys": [key]}) + "\n",
            encoding="utf-8")
    monkeypatch.setattr(evaluate_final_reserve, "PARENT", bundles[0])
    monkeypatch.setattr(evaluate_final_reserve, "PRIOR", bundles[1])
    monkeypatch.setattr(evaluate_final_reserve, "EXPANSION", bundles[2])
    with pytest.raises(ValueError, match="reuses inspected or parent family"):
        evaluate_final_reserve.validate_family_separation()
