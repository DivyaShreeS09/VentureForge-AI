import sys

import pandas as pd

from app.ml.local_success_explainer import _try_shap_tree_explainer, explain_local_prediction
from app.ml.success_predictor import is_loaded, predict_success


class _FakePipeline:
    """Minimal stand-in with just enough shape for the finite-difference path — deliberately has
    no `named_steps`, so even if `shap` happened to be genuinely installed in this environment,
    `_try_shap_tree_explainer`'s own structural check would skip it too. This test forces the
    `ImportError` path specifically (see `local_success_explainer`'s module docstring, point 1),
    independent of whether the real `success_predictor` artifact is trained in this environment.
    """

    def predict_proba(self, row: pd.DataFrame):
        value = row.iloc[0]["funding_total_usd"]
        proba = 0.8 if value == 500_000 else 0.5
        return [[1 - proba, proba]]


def _identity_engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    return df


def test_shap_unavailable_is_caught_and_returns_none(monkeypatch):
    """Simulates `shap` not being installed (`import shap` raising `ImportError`) — the SHAP path
    must be skipped cleanly, never raise, and never be silently treated as available."""
    monkeypatch.setitem(sys.modules, "shap", None)
    result = _try_shap_tree_explainer(_FakePipeline(), pd.DataFrame([{"funding_total_usd": 500_000}]))
    assert result is None


def test_finite_difference_fallback_used_when_shap_is_unavailable(monkeypatch):
    monkeypatch.setitem(sys.modules, "shap", None)

    base_row = {
        "funding_total_usd": 500_000, "funding_rounds": 1, "company_age_years": 2,
        "primary_category": "b2b", "country_code": "usa",
    }
    engineered_row = pd.DataFrame([base_row])

    result = explain_local_prediction(
        _FakePipeline(), base_row, engineered_row, _identity_engineer_features, baseline_proba=0.8
    )

    assert result["method"] == "local_finite_difference"
    assert result["available"] is True
    assert "not SHAP" in result["note"]
    assert all(t["direction"] in ("supports", "opposes") for t in result["terms"])
    # funding_total_usd is the only field the fake model's probability actually depends on — it
    # must be the dominant (largest-magnitude) contribution.
    assert result["terms"][0]["feature"] == "funding_total_usd"


def test_local_explanation_is_present_and_distinct_from_global():
    if not is_loaded():
        import pytest

        pytest.skip("success predictor artifact not trained in this environment")

    result = predict_success(
        total_funding_usd=500_000, funding_rounds=1, founded_year=2022, country_code="usa", industry="b2b"
    )
    local = result["local_explanation"]
    assert local["method"] in ("shap_tree_explainer", "local_finite_difference")
    assert isinstance(local["terms"], list)
    for term in local["terms"]:
        assert term["direction"] in ("supports", "opposes")
    # Never the same object/shape as the global ranking — must always be independently present.
    assert local is not result["top_global_features"]
    assert "not a per-prediction explanation" in result["explanation_note"]


def test_local_explanation_never_labeled_as_global_when_finite_difference_used():
    if not is_loaded():
        import pytest

        pytest.skip("success predictor artifact not trained in this environment")

    result = predict_success(
        total_funding_usd=None, funding_rounds=None, founded_year=None, country_code=None, industry=None
    )
    local = result["local_explanation"]
    if local["method"] == "local_finite_difference":
        assert "not SHAP" in local["note"]
        assert "global" not in local["method"]


def test_all_missing_features_still_returns_a_safe_explanation_shape():
    if not is_loaded():
        import pytest

        pytest.skip("success predictor artifact not trained in this environment")

    result = predict_success(
        total_funding_usd=None, funding_rounds=None, founded_year=None, country_code=None, industry=None
    )
    local = result["local_explanation"]
    assert isinstance(local["terms"], list)
    assert isinstance(local["available"], bool)
