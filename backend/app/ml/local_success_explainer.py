"""Prediction-specific (local) explainability for the success predictor (Phase 0.5, mandatory
correction #7).

`app.ml.success_predictor`'s `top_global_features` is honest but explicitly a *global*
permutation-importance ranking (computed once at training time on held-out data) — it is never a
per-prediction explanation, and must never be presented as one. This module computes a genuinely
local (per-input) attribution instead:

  1. Attempt `shap.TreeExplainer` on the underlying tree model. In practice this repo's trained
     artifact is a `CalibratedClassifierCV`-wrapped `HistGradientBoostingClassifier` (see
     app.ml.success_predictor._load_artifact) — SHAP would explain the pre-calibration booster's
     raw margin output, not the calibrated probability actually shown to users, and would need to
     be computed per-fold and reconciled through the calibration curve to be faithful. That
     mismatch is treated as "unsupported" here, not silently glossed over: this function only
     takes the SHAP path when it can attach a `TreeExplainer` directly to an *uncalibrated*
     tree estimator; otherwise it falls back deterministically.
  2. Otherwise, fall back to a documented local finite-difference method: for each perturbable
     input field, hold every other field at its actual submitted value and reset just that one
     field to "unknown" (triggering the trained pipeline's own median/most-frequent imputation —
     the same neutral baseline it already uses for genuinely missing data). The resulting change
     in predicted probability, relative to the real prediction, is that field's local contribution
     for this specific input. Explicitly labeled `"local approximate contribution (not SHAP)"`
     whenever this path is used.

Global permutation importance (`top_global_features`) is never touched by this module and stays
available separately, clearly labeled global — see app.ml.success_predictor.predict_success.
"""

from __future__ import annotations

import logging

import pandas as pd
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)

_PERTURBABLE_FIELDS = (
    "funding_total_usd",
    "funding_rounds",
    "company_age_years",
    "primary_category",
    "country_code",
)
_CATEGORICAL_NEUTRAL = {"primary_category": "unknown", "country_code": "unknown"}


def _try_shap_tree_explainer(pipeline: Pipeline, row: pd.DataFrame) -> list[dict] | None:
    """Return a SHAP-based local explanation, or None if SHAP is unavailable or this pipeline's
    tree estimator isn't reachable in a form TreeExplainer can attach to directly (e.g. it's
    wrapped in cross-validated calibration — see this module's docstring for why that case is
    treated as unsupported rather than approximated)."""
    try:
        import shap  # noqa: F401
    except ImportError:
        logger.info("shap is not installed; using the local finite-difference fallback instead")
        return None

    # CalibratedClassifierCV (this repo's actual trained artifact) has no single uncalibrated
    # tree estimator to attach a TreeExplainer to without misrepresenting the calibrated
    # probability — see module docstring. Only an uncalibrated Pipeline(..., HistGradientBoosting)
    # is supported here.
    if not (hasattr(pipeline, "named_steps") and "clf" in getattr(pipeline, "named_steps", {})):
        return None

    try:
        from sklearn.ensemble import HistGradientBoostingClassifier

        clf = pipeline.named_steps["clf"]
        if not isinstance(clf, HistGradientBoostingClassifier):
            return None
        preprocess = pipeline.named_steps["preprocess"]
        transformed = preprocess.transform(row)
        feature_names = list(preprocess.get_feature_names_out())
        explainer = shap.TreeExplainer(clf)
        shap_values = explainer.shap_values(transformed)
        values = shap_values[0] if hasattr(shap_values, "__len__") else shap_values
        contributions = [
            {
                "feature": name,
                "contribution": round(float(value), 4),
                "direction": "supports" if value > 0 else "opposes",
            }
            for name, value in zip(feature_names, values[0])
        ]
        contributions.sort(key=lambda c: abs(c["contribution"]), reverse=True)
        return contributions
    except Exception:
        logger.exception("SHAP TreeExplainer failed unexpectedly; using the finite-difference fallback")
        return None


def _finite_difference_explanation(
    pipeline: Pipeline, base_row: dict, engineer_features, baseline_proba: float
) -> list[dict]:
    contributions = []
    for field in _PERTURBABLE_FIELDS:
        if base_row.get(field) is None:
            # Already missing/imputed in the real prediction — there is no "actual value" whose
            # local contribution can be measured against the neutral baseline.
            continue
        variant = dict(base_row)
        variant[field] = _CATEGORICAL_NEUTRAL.get(field)
        variant_row = engineer_features(pd.DataFrame([variant]))
        variant_proba = float(pipeline.predict_proba(variant_row)[0][1])
        contribution = baseline_proba - variant_proba
        contributions.append(
            {
                "feature": field,
                "contribution": round(contribution, 4),
                "direction": "supports" if contribution > 0 else "opposes",
            }
        )
    contributions.sort(key=lambda c: abs(c["contribution"]), reverse=True)
    return contributions


def explain_local_prediction(
    pipeline: Pipeline, base_row: dict, engineered_row: pd.DataFrame, engineer_features, baseline_proba: float
) -> dict:
    """Return `{method, available, terms, note}` — a per-prediction explanation for this exact
    input, never global permutation importance."""
    shap_terms = _try_shap_tree_explainer(pipeline, engineered_row)
    if shap_terms is not None:
        return {
            "method": "shap_tree_explainer",
            "available": True,
            "terms": shap_terms,
            "note": "SHAP TreeExplainer contribution for this specific input.",
        }

    terms = _finite_difference_explanation(pipeline, base_row, engineer_features, baseline_proba)
    return {
        "method": "local_finite_difference",
        "available": len(terms) > 0,
        "terms": terms,
        "note": (
            "local approximate contribution (not SHAP) — each feature's actual value is compared "
            "against the trained pipeline's own median/most-frequent imputation for this same "
            "input, holding every other field fixed. Never global permutation importance."
        ),
    }
