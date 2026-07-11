"""Loads the trained industry classifier once at process startup and serves predictions.

The artifact is produced by `python -m ml.src.training.train_industry_classifier` (see
ml/README.md) and read from `settings.model_dir`. If no artifact exists, `is_loaded()` returns
False and callers get a clear, honest error instead of a fabricated prediction.
"""

from __future__ import annotations

import json
import logging
import sys
from functools import lru_cache
from pathlib import Path

import joblib
from sklearn.pipeline import Pipeline

from app.core.config import settings

logger = logging.getLogger(__name__)

# The `ml` package (training + explainability code) lives as a sibling of `backend/` at the repo
# root. Add it to sys.path once so `ml.src.explainability...` can be imported regardless of the
# backend's working directory (mirrors how ml/dataset_manifest.json + ml/DATASETS.md describe the
# repo layout). This is the only cross-package import between backend/ and ml/.
_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

MODEL_NAME = "industry_classifier"
MODEL_VERSION = "v2"
TOP_N_ALTERNATIVES = 3

# Below this top-1 probability, or when the top-2 classes are within this margin of each other,
# the prediction is reported as uncertain rather than presented as a confident fact. With 7
# real-data classes a uniform-random guess scores ~0.14, so 0.35 requires meaningfully more
# signal than chance while still accepting confident real predictions (see ml/DATASETS.md test
# metrics: median correct-class confidence is well above this bar).
MIN_CONFIDENCE = 0.35
AMBIGUITY_MARGIN = 0.10


class IndustryClassifierUnavailable(RuntimeError):
    """Raised when the trained artifact has not been produced yet."""


def _model_dir() -> Path:
    return Path(settings.model_dir) / MODEL_NAME / MODEL_VERSION


def _build_text_feature(name: str, description: str) -> str:
    """Must mirror ml/src/features/build_features.py exactly — see that module's docstring."""
    name = (name or "").strip()
    description = (description or "").strip()
    if not name:
        return description
    if not description:
        return name
    return f"{name}. {description}"


@lru_cache(maxsize=1)
def _load_artifact() -> tuple[Pipeline, dict]:
    model_dir = _model_dir()
    model_path = model_dir / "model.joblib"
    metadata_path = model_dir / "metadata.json"
    if not model_path.exists() or not metadata_path.exists():
        raise IndustryClassifierUnavailable(
            f"No trained artifact at {model_dir}. Run "
            "`python -m ml.src.training.train_industry_classifier` from the repo root first."
        )
    pipeline: Pipeline = joblib.load(model_path)
    metadata = json.loads(metadata_path.read_text())
    logger.info("Loaded industry classifier %s (trained_at=%s)", MODEL_VERSION, metadata.get("trained_at"))
    return pipeline, metadata


def is_loaded() -> bool:
    try:
        _load_artifact()
        return True
    except IndustryClassifierUnavailable:
        return False


def model_metadata() -> dict | None:
    try:
        _, metadata = _load_artifact()
        return metadata
    except IndustryClassifierUnavailable:
        return None


def predict_industry(name: str, description: str) -> dict:
    """Predict industry for a startup. Raises IndustryClassifierUnavailable if untrained."""
    from ml.src.explainability.term_contributions import explain_prediction

    pipeline, metadata = _load_artifact()
    text = _build_text_feature(name, description)

    proba = pipeline.predict_proba([text])[0]
    classes = list(pipeline.named_steps["clf"].classes_)
    ranked = sorted(zip(classes, proba), key=lambda p: p[1], reverse=True)

    predicted_label, confidence = ranked[0]
    confidence = float(confidence)
    runner_up_confidence = float(ranked[1][1]) if len(ranked) > 1 else 0.0
    alternatives = [{"industry": label, "confidence": float(p)} for label, p in ranked[1:TOP_N_ALTERNATIVES + 1]]
    explanation = explain_prediction(pipeline, text, predicted_label)

    # No recognized vocabulary means the vectorizer produced an all-zero vector, so the
    # prediction reflects only the training class prior — not any signal from this input. Under
    # class imbalance (see ml/DATASETS.md — 'b2b' is ~49% of training data), that prior alone can
    # still clear the confidence/margin thresholds below, so this check is independent of them.
    vectorizer = pipeline.named_steps.get("tfidf")
    has_no_vocabulary = bool(vectorizer is not None and vectorizer.transform([text]).nnz == 0)

    is_low_confidence = bool(confidence < MIN_CONFIDENCE)
    is_ambiguous = bool((confidence - runner_up_confidence) < AMBIGUITY_MARGIN)
    uncertainty_reasons = []
    if has_no_vocabulary:
        uncertainty_reasons.append(
            "Input contains no terms the model recognizes — this prediction reflects only the "
            "training data's class distribution, not the input's content."
        )
    if is_low_confidence:
        uncertainty_reasons.append(
            f"Top prediction confidence ({confidence:.2f}) is below the minimum reporting "
            f"threshold ({MIN_CONFIDENCE})."
        )
    if is_ambiguous:
        uncertainty_reasons.append(
            f"Top two industries are within {AMBIGUITY_MARGIN} confidence of each other "
            "(the description may span multiple domains)."
        )

    return {
        "predicted_industry": predicted_label,
        "confidence": float(confidence),
        "alternatives": alternatives,
        "model_version": metadata["version"],
        "model_pipeline": metadata.get("selected_pipeline", "unknown"),
        "explanation": explanation,
        "is_uncertain": has_no_vocabulary or is_low_confidence or is_ambiguous,
        "uncertainty_reasons": uncertainty_reasons,
    }
