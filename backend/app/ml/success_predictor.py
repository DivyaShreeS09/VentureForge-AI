"""Loads the trained startup success-prediction model once at process startup and serves
predictions.

The artifact is produced by `python -m ml.src.training.train_success_classifier` (see
ml/DATASETS.md) and read from `settings.model_dir`. If no artifact exists, `is_loaded()` returns
False and callers get a clear, honest error instead of a fabricated prediction.

Unlike the industry classifier, this model's features (funding history, company age, category,
country) are not all guaranteed to be present on every submission — the startup form only
collects them optionally (see app.schemas.startup.CompanyMetrics). Missing fields are imputed by
the trained pipeline itself (median/most-frequent, matching training — see
ml/src/features/success_features.py) and reported back as `missing_features` so the result is
never presented as more informed than it actually is.
"""

from __future__ import annotations

import json
import logging
import sys
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline

from app.core.config import settings

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from ml.src.features.success_features import engineer_features  # noqa: E402

from app.ml.local_success_explainer import explain_local_prediction  # noqa: E402

MODEL_NAME = "success_predictor"
MODEL_VERSION = "v1"
# Final ML Excellence Sprint, Phase 4 (Version Cleanup): the artifact metadata's own
# `dataset_version` field is an internal experiment-tracking label (e.g.
# "v2-crunchbase-2013-date-features") -- useful for engineers reading metadata.json directly, but
# must never surface in the API/frontend per this sprint's rule. This product has never shipped,
# so there is nothing for "v2" to be a version bump FROM from a founder's perspective.
PUBLIC_DATASET_LABEL = "Historical Pattern Dataset"

# Below this top-1 probability margin from 0.5, the prediction is reported as uncertain rather
# than a confident fact — a coin-flip-adjacent probability carries little decision value.
MIN_MARGIN_FROM_CHANCE = 0.10


class SuccessPredictorUnavailable(RuntimeError):
    """Raised when the trained artifact has not been produced yet."""


def _model_dir() -> Path:
    return Path(settings.model_dir) / MODEL_NAME / MODEL_VERSION


@lru_cache(maxsize=1)
def _load_artifact() -> tuple[Pipeline, dict]:
    model_dir = _model_dir()
    model_path = model_dir / "model.joblib"
    metadata_path = model_dir / "metadata.json"
    if not model_path.exists() or not metadata_path.exists():
        raise SuccessPredictorUnavailable(
            f"No trained artifact at {model_dir}. Run "
            "`python -m ml.src.training.train_success_classifier` from the repo root first."
        )
    pipeline: Pipeline = joblib.load(model_path)
    metadata = json.loads(metadata_path.read_text())
    logger.info("Loaded success predictor %s (trained_at=%s)", MODEL_VERSION, metadata.get("trained_at"))
    return pipeline, metadata


def is_loaded() -> bool:
    try:
        _load_artifact()
        return True
    except SuccessPredictorUnavailable:
        return False


def model_metadata() -> dict | None:
    try:
        _, metadata = _load_artifact()
        return metadata
    except SuccessPredictorUnavailable:
        return None


def predict_success(
    total_funding_usd: float | None,
    funding_rounds: int | None,
    founded_year: int | None,
    country_code: str | None,
    industry: str | None,
) -> dict:
    """Predict a historical-pattern success likelihood. Raises SuccessPredictorUnavailable if
    untrained. Any feature not supplied is imputed by the trained pipeline and listed in
    `missing_features` — the caller must surface this, never present the result as fully informed.
    """
    pipeline, metadata = _load_artifact()

    missing_features: list[str] = []
    if total_funding_usd is None:
        missing_features.append("total_funding_usd")
    if funding_rounds is None:
        missing_features.append("funding_rounds")

    company_age_years: float | None = None
    if founded_year is not None:
        from datetime import datetime, timezone

        company_age_years = max(0.0, datetime.now(timezone.utc).year - founded_year)
    else:
        missing_features.append("founded_year")

    if not country_code:
        missing_features.append("country_code")

    # v3 fix (ML Excellence Sprint, Priority 1): funding_span_years / time_to_first_funding_years /
    # funding_recency_years were removed from the trained feature set entirely — this endpoint
    # never had real dates to supply for them (CompanyMetrics collects no funding-round dates),
    # and a controlled experiment proved training on those permanently-fabricated fields degraded
    # real serving-condition accuracy relative to a model that never expects them. See
    # ml/src/features/success_features.py for the full experiment writeup.
    base_row = {
        "funding_total_usd": total_funding_usd,
        "funding_rounds": funding_rounds,
        "company_age_years": company_age_years,
        "primary_category": (industry or "unknown").lower(),
        "category_count": 1,
        "country_code": (country_code or "unknown").lower(),
    }
    row = engineer_features(pd.DataFrame([base_row]))

    proba = float(pipeline.predict_proba(row)[0][1])

    # v2: use the training-time-recommended operating threshold (F1-optimal on the held-out test
    # set — see ml/src/training/train_success_classifier.py) if metadata provides one, falling
    # back to the original 0.5 default for an older artifact that predates this field. This is an
    # additive change: `recommended_threshold` is surfaced in the response so callers can see
    # exactly which cutoff was applied and why, never silently swapped in.
    recommended_threshold_info = metadata.get("recommended_threshold")
    operating_threshold = (
        recommended_threshold_info["threshold"] if recommended_threshold_info else 0.5
    )
    predicted_label = "success" if proba >= operating_threshold else "failure"
    margin_from_chance = abs(proba - 0.5)
    is_uncertain = margin_from_chance < MIN_MARGIN_FROM_CHANCE or len(missing_features) >= 3

    uncertainty_reasons = []
    if margin_from_chance < MIN_MARGIN_FROM_CHANCE:
        uncertainty_reasons.append(
            f"Predicted probability ({proba:.2f}) is close to chance (0.50) — this pattern estimate "
            "is not strongly differentiated."
        )
    if len(missing_features) >= 3:
        uncertainty_reasons.append(
            f"{len(missing_features)} of the model's input features were not provided and were "
            "imputed with training-set medians/modes — treat this estimate with low confidence."
        )

    # Global permutation-importance ranking (computed once at training time on held-out test data
    # — see ml/src/training/train_success_classifier.py), not a per-prediction SHAP explanation.
    # Honestly labeled as such: it tells the caller which features matter to the model in general,
    # not which features drove this specific prediction.
    top_features = [
        item["feature"] for item in metadata.get("permutation_importance", [])[:3]
    ]

    local_explanation = explain_local_prediction(pipeline, base_row, row, engineer_features, proba)

    # Founder-facing band (Phase 1 correction): never render "success"/"failure" as a verdict on
    # the idea itself — this model was trained exclusively on companies that had already raised
    # funding (see ml/DATASETS.md), so a binary label reads as a false verdict on a raw idea. This
    # band is the only historical-pattern-signal field the default founder view may show;
    # `predicted_label`/`success_probability` remain below only for backward compatibility and the
    # Advanced/technical view. See app.agents.judge / app.agents.mentor_synthesis: an
    # "insufficient_input_reliability" signal must never become a biggest_risk or top action, and
    # must never lower the founder-facing readiness presentation.
    if is_uncertain:
        pattern_signal_label = "insufficient_input_reliability"
    elif proba >= 0.6:
        pattern_signal_label = "stronger_comparison"
    elif proba >= 0.4:
        pattern_signal_label = "mixed_comparison"
    else:
        pattern_signal_label = "limited_comparison"

    pattern_signal_display = {
        "insufficient_input_reliability": "Insufficient input reliability",
        "stronger_comparison": "Stronger comparison",
        "mixed_comparison": "Mixed comparison",
        "limited_comparison": "Limited comparison",
    }[pattern_signal_label]

    pattern_signal_sentence = (
        "Not enough information was supplied to compare this idea reliably against historical "
        "company patterns yet."
        if pattern_signal_label == "insufficient_input_reliability"
        else (
            f"Compared to historical company outcome patterns, this idea shows a {pattern_signal_display.lower()} "
            "— this describes how this input compares to past companies, not whether this idea will succeed."
        )
    )

    return {
        "pattern_signal_label": pattern_signal_label,
        "pattern_signal_display": pattern_signal_display,
        "pattern_signal_sentence": pattern_signal_sentence,
        "predicted_label": predicted_label,
        "success_probability": round(proba, 4),
        "model_version": MODEL_VERSION,
        "model_pipeline": metadata.get("selected_algorithm", metadata.get("selected_pipeline", "unknown")),
        "calibration_method": metadata.get("calibration_method", "unknown"),
        "dataset_version": PUBLIC_DATASET_LABEL,
        "missing_features": missing_features,
        "is_uncertain": is_uncertain,
        "uncertainty_reasons": uncertainty_reasons,
        "top_global_features": top_features,
        "explanation_note": (
            "top_global_features reflects which features matter most to the model overall "
            "(permutation importance on held-out test data), not a per-prediction explanation for "
            "this specific input."
        ),
        # Phase 0.5: a genuinely local (per-input) explanation — see
        # app.ml.local_success_explainer. Always distinct from top_global_features above; never
        # presented as global importance and vice versa.
        "local_explanation": local_explanation,
        # v2 additive fields — never replace any field above, only extend the response shape.
        "operating_threshold": operating_threshold,
        "recommended_threshold_info": recommended_threshold_info,
        "subgroup_metrics_summary": metadata.get("subgroup_metrics"),
        "disclaimer": (
            "Historical pattern estimate derived from resolved Crunchbase outcomes (acquisitions, "
            "IPOs, shutdowns) — not a guarantee of this startup's success and not investment advice."
        ),
    }
