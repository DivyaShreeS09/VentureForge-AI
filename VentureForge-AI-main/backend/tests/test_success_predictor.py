"""Tests against whatever trained artifact is present in ml/models/success_predictor/v1/ (produced
by `python -m ml.src.training.train_success_classifier`). Skipped if untrained, mirroring
test_predictor.py's pattern — training is a separate, explicit step.
"""

import pytest

from app.ml import success_predictor


@pytest.fixture(autouse=True)
def _skip_if_untrained():
    if not success_predictor.is_loaded():
        pytest.skip("success_predictor artifact not trained — run ml/src/training first")


def test_predicts_reasonable_structure():
    result = success_predictor.predict_success(
        total_funding_usd=2_000_000,
        funding_rounds=2,
        founded_year=2023,
        country_code="usa",
        industry="fintech",
    )
    assert result["predicted_label"] in ("success", "failure")
    assert 0.0 <= result["success_probability"] <= 1.0
    assert "is_uncertain" in result and "uncertainty_reasons" in result
    assert result["missing_features"] == []


def test_all_fields_missing_flags_uncertain_and_lists_missing_features():
    result = success_predictor.predict_success(
        total_funding_usd=None,
        funding_rounds=None,
        founded_year=None,
        country_code=None,
        industry=None,
    )
    assert "predicted_label" in result
    assert len(result["missing_features"]) >= 3
    assert result["is_uncertain"] is True


def test_probability_bounds_hold_for_extreme_inputs():
    result = success_predictor.predict_success(
        total_funding_usd=1,
        funding_rounds=0,
        founded_year=2026,
        country_code="unknown",
        industry="unknown",
    )
    assert 0.0 <= result["success_probability"] <= 1.0


def test_result_is_json_serializable():
    import json

    result = success_predictor.predict_success(
        total_funding_usd=500_000,
        funding_rounds=1,
        founded_year=2022,
        country_code="gbr",
        industry="saas",
    )
    json.dumps(result)


def test_prediction_is_deterministic_for_identical_input():
    args = dict(total_funding_usd=3_000_000, funding_rounds=3, founded_year=2020, country_code="usa", industry="b2b")
    first = success_predictor.predict_success(**args)
    second = success_predictor.predict_success(**args)
    assert first["success_probability"] == second["success_probability"]
    assert first["predicted_label"] == second["predicted_label"]


def test_unrecognized_category_and_country_do_not_crash():
    # OneHotEncoder(handle_unknown="ignore") must degrade gracefully to an all-zero encoding for
    # a category/country never seen during training, not raise.
    result = success_predictor.predict_success(
        total_funding_usd=1_000_000,
        funding_rounds=1,
        founded_year=2021,
        country_code="zzz-not-a-real-country",
        industry="not-a-real-industry-xyz",
    )
    assert 0.0 <= result["success_probability"] <= 1.0


def test_top_global_features_are_reported_from_known_feature_set():
    from ml.src.features.success_features import ALL_FEATURES

    result = success_predictor.predict_success(
        total_funding_usd=1_000_000, funding_rounds=1, founded_year=2021, country_code="usa", industry="saas"
    )
    assert "top_global_features" in result
    for feature in result["top_global_features"]:
        assert feature in ALL_FEATURES


def test_calibration_method_is_reported():
    result = success_predictor.predict_success(
        total_funding_usd=1_000_000, funding_rounds=1, founded_year=2021, country_code="usa", industry="saas"
    )
    assert result["calibration_method"] in ("raw", "sigmoid", "isotonic")


def test_zero_funding_rounds_does_not_crash_the_engineered_ratio_feature():
    # funding_per_round = funding_total_usd / funding_rounds — funding_rounds=0 must not raise
    # ZeroDivisionError or produce a non-finite probability.
    result = success_predictor.predict_success(
        total_funding_usd=1_000_000, funding_rounds=0, founded_year=2021, country_code="usa", industry="saas"
    )
    assert 0.0 <= result["success_probability"] <= 1.0


# --- v2 additive fields: operating_threshold / recommended_threshold_info / subgroup summary ---


def test_operating_threshold_is_present_and_in_bounds():
    result = success_predictor.predict_success(
        total_funding_usd=1_000_000, funding_rounds=1, founded_year=2021, country_code="usa", industry="saas"
    )
    assert "operating_threshold" in result
    assert 0.0 <= result["operating_threshold"] <= 1.0


def test_predicted_label_is_consistent_with_operating_threshold():
    result = success_predictor.predict_success(
        total_funding_usd=1_000_000, funding_rounds=1, founded_year=2021, country_code="usa", industry="saas"
    )
    expected_label = "success" if result["success_probability"] >= result["operating_threshold"] else "failure"
    assert result["predicted_label"] == expected_label


def test_recommended_threshold_info_matches_metadata_when_present():
    metadata = success_predictor.model_metadata()
    result = success_predictor.predict_success(
        total_funding_usd=1_000_000, funding_rounds=1, founded_year=2021, country_code="usa", industry="saas"
    )
    if metadata and metadata.get("recommended_threshold"):
        assert result["recommended_threshold_info"] == metadata["recommended_threshold"]
        assert result["operating_threshold"] == metadata["recommended_threshold"]["threshold"]
    else:
        # Older artifact without a recommended_threshold — falls back to the original 0.5 default,
        # never silently applying an undocumented cutoff.
        assert result["operating_threshold"] == 0.5


def test_subgroup_metrics_summary_is_present_and_json_serializable():
    import json

    result = success_predictor.predict_success(
        total_funding_usd=1_000_000, funding_rounds=1, founded_year=2021, country_code="usa", industry="saas"
    )
    assert "subgroup_metrics_summary" in result
    json.dumps(result)  # must not raise — additive fields must not break serialization


# --- Phase 1 correction: Historical Pattern Signal founder-facing band (never "success"/"failure") --


def test_pattern_signal_label_is_one_of_the_four_allowed_bands():
    result = success_predictor.predict_success(
        total_funding_usd=1_000_000, funding_rounds=1, founded_year=2021, country_code="usa", industry="saas"
    )
    assert result["pattern_signal_label"] in (
        "insufficient_input_reliability", "stronger_comparison", "mixed_comparison", "limited_comparison",
    )
    assert result["pattern_signal_display"] in (
        "Insufficient input reliability", "Stronger comparison", "Mixed comparison", "Limited comparison",
    )
    assert "success" not in result["pattern_signal_display"].lower()
    assert "failure" not in result["pattern_signal_display"].lower()


def test_uncertain_prediction_is_always_insufficient_input_reliability():
    result = success_predictor.predict_success(
        total_funding_usd=None, funding_rounds=None, founded_year=None, country_code=None, industry=None,
    )
    assert result["is_uncertain"] is True
    assert result["pattern_signal_label"] == "insufficient_input_reliability"


def test_pattern_signal_sentence_never_predicts_success_or_failure():
    result = success_predictor.predict_success(
        total_funding_usd=1_000_000, funding_rounds=1, founded_year=2021, country_code="usa", industry="saas"
    )
    sentence = result["pattern_signal_sentence"].lower()
    assert "will succeed" not in sentence
    assert "will fail" not in sentence


def test_response_shape_is_additive_only_existing_fields_unchanged():
    """v2 must only ADD fields to the response — every field the original API contract promised
    must still be present with the same meaning."""
    result = success_predictor.predict_success(
        total_funding_usd=2_000_000, funding_rounds=2, founded_year=2023, country_code="usa", industry="fintech"
    )
    original_contract_fields = {
        "predicted_label",
        "success_probability",
        "model_version",
        "model_pipeline",
        "calibration_method",
        "dataset_version",
        "missing_features",
        "is_uncertain",
        "uncertainty_reasons",
        "top_global_features",
        "explanation_note",
        "disclaimer",
    }
    assert original_contract_fields.issubset(result.keys())
