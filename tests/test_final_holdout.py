from audit.evaluate_final_holdout import combined_counts, oracle_key


def test_combined_holdout_counts_keep_occurrence_denominators():
    reports = [
        {"counts": {"all": {"reference": 3, "python": 2, "shared": 2,
                             "documents": 1, "passages": 2}}},
        {"counts": {"all": {"reference": 2, "python": 3, "shared": 1,
                             "documents": 1, "passages": 1}}},
    ]
    result = combined_counts(reports, "all")
    assert result["reference"] == 5
    assert result["python"] == 5
    assert result["shared"] == 3
    assert result["reference_only"] == 2
    assert result["python_only"] == 2
    assert result["prediction_agreement"] == 3 / 5
    assert result["recovery"] == 3 / 5
    assert result["documents"] == 2


def test_reference_only_count_does_not_invent_python_zeroes():
    reports = [{"reference_count_only": True,
                "counts": {"all": {"reference": 3, "documents": 1}}},
               {"reference_count_only": True,
                "counts": {"all": {"reference": 4, "documents": 1}}}]
    result = combined_counts(reports, "all")
    assert result["reference"] == 7
    assert "python" not in result and "recovery" not in result


def test_oracle_compatibility_key_ignores_input_specific_fingerprint():
    common = {"executable_sha256": "same", "source": {"files": {"a": "x"}},
              "word_data": {"files": {"b": "y"}}, "medpost": {"status": "unknown"},
              "path_Ab3P_sha256": "z", "locale": "C"}
    assert oracle_key(dict(common, fingerprint="first", input_manifest_sha256="one")) == (
        oracle_key(dict(common, fingerprint="second", input_manifest_sha256="two")))
    assert oracle_key(common) != oracle_key(dict(common, executable_sha256="different"))
    assert oracle_key(common) != oracle_key(dict(common, runtime_data_paths={"MedPost": "elsewhere"}))
