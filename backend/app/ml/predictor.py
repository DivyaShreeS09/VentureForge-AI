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
import numpy as np

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
# Internal artifact folder actually loaded from disk (ml/models/industry_classifier/<MODEL_VERSION>)
# -- this product has never shipped, so there is nothing for "v3" to be a version bump FROM. Kept
# as-is purely so the training/experiment history (v1/v2/v3 artifacts, each a real, superseded
# benchmark step -- see ml/DATASETS.md) stays on disk for engineering rollback; never surfaced
# past this module. See PUBLIC_MODEL_VERSION below for what callers/API/frontend actually see.
MODEL_VERSION = "v3"
# Final ML Excellence Sprint, Phase 4 (Version Cleanup): the ONE production-facing version label.
# Internal experiment/artifact versioning (v1/v2/v3, "experiment_*" names) must never leak into the
# API, frontend, or reports -- there is exactly one production model from a founder's perspective.
PUBLIC_MODEL_VERSION = "v1"
TOP_N_ALTERNATIVES = 3

# Below this top-1 probability, or when the top-2 classes are within this margin of each other,
# the prediction is reported as uncertain rather than presented as a confident fact. With 7
# real-data classes a uniform-random guess scores ~0.14, so 0.35 requires meaningfully more
# signal than chance while still accepting confident real predictions (see ml/DATASETS.md test
# metrics: median correct-class confidence is well above this bar).
MIN_CONFIDENCE = 0.35
AMBIGUITY_MARGIN = 0.10

# Fallback abstention threshold if the trained artifact's metadata does not record one (e.g. an
# artifact trained before this field existed) — see ml/DATASETS.md "Abstention" for how the
# recommended default was chosen from the coverage/accuracy trade-off table.
DEFAULT_ABSTENTION_THRESHOLD = 0.5

# Fields every valid metadata.json must contain — used only to raise a clear, explicit error on a
# corrupt/incompatible artifact rather than silently mispredicting with a mismatched schema. Does
# NOT change the happy-path response shape.
_REQUIRED_METADATA_FIELDS = {"version", "labels", "selected_pipeline"}


class IndustryClassifierUnavailable(RuntimeError):
    """Raised when the trained artifact has not been produced yet."""


class IndustryClassifierArtifactError(RuntimeError):
    """Raised when a trained artifact exists on disk but is corrupt or schema-incompatible —
    distinct from IndustryClassifierUnavailable (which means "not trained yet"). Callers should
    treat this as a hard failure, never as a signal to silently fall back to a guess."""


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


def _validate_metadata_schema(metadata: dict, model_dir: Path) -> None:
    """Raise IndustryClassifierArtifactError with a clear message if metadata.json is missing
    required fields or its label schema is internally inconsistent — a corrupt/incompatible
    artifact must fail loudly, not silently mispredict with the wrong label set."""
    missing = _REQUIRED_METADATA_FIELDS - set(metadata.keys())
    if missing:
        raise IndustryClassifierArtifactError(
            f"Artifact metadata at {model_dir / 'metadata.json'} is missing required field(s) "
            f"{sorted(missing)} — this artifact is corrupt or was produced by an incompatible "
            "version of the training script. Retrain via "
            "`python -m ml.src.training.train_industry_classifier`."
        )
    labels = metadata.get("labels")
    if not isinstance(labels, list) or not labels:
        raise IndustryClassifierArtifactError(
            f"Artifact metadata at {model_dir / 'metadata.json'} has an invalid or empty "
            f"'labels' field ({labels!r}) — cannot serve predictions with no known label schema."
        )
    label_schema = metadata.get("label_schema")
    if label_schema is not None and label_schema.get("n_classes") != len(labels):
        raise IndustryClassifierArtifactError(
            f"Artifact metadata at {model_dir / 'metadata.json'} is internally inconsistent: "
            f"label_schema.n_classes={label_schema.get('n_classes')} does not match "
            f"len(labels)={len(labels)}. This artifact is corrupt — retrain."
        )


@lru_cache(maxsize=1)
def _load_artifact() -> tuple[object, dict]:
    model_dir = _model_dir()
    model_path = model_dir / "model.joblib"
    metadata_path = model_dir / "metadata.json"
    if not model_path.exists() or not metadata_path.exists():
        raise IndustryClassifierUnavailable(
            f"No trained artifact at {model_dir}. Run "
            "`python -m ml.src.training.train_industry_classifier` from the repo root first."
        )
    try:
        metadata = json.loads(metadata_path.read_text())
    except json.JSONDecodeError as exc:
        raise IndustryClassifierArtifactError(
            f"Artifact metadata at {metadata_path} is not valid JSON ({exc}) — this artifact is "
            "corrupt. Retrain via `python -m ml.src.training.train_industry_classifier`."
        ) from exc
    _validate_metadata_schema(metadata, model_dir)

    pipeline = joblib.load(model_path)
    model_classes = list(getattr(pipeline, "classes_", []))
    if model_classes and set(model_classes) != set(metadata["labels"]):
        raise IndustryClassifierArtifactError(
            f"Artifact at {model_dir} is inconsistent: model.joblib's classes_ "
            f"({sorted(model_classes)}) do not match metadata.json's 'labels' "
            f"({sorted(metadata['labels'])}). This artifact is corrupt — retrain."
        )
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

    model, metadata = _load_artifact()
    text = _build_text_feature(name, description)
    is_embedding_model = bool(metadata.get("is_embedding_model"))

    proba = model.predict_proba([text])[0]
    classes = list(model.classifier.classes_) if is_embedding_model else list(model.named_steps["clf"].classes_)
    ranked = sorted(zip(classes, proba), key=lambda p: p[1], reverse=True)

    predicted_label, confidence = ranked[0]
    confidence = float(confidence)
    runner_up_confidence = float(ranked[1][1]) if len(ranked) > 1 else 0.0
    alternatives = [{"industry": label, "confidence": float(p)} for label, p in ranked[1:TOP_N_ALTERNATIVES + 1]]

    # Primary/secondary prediction: the top-2 predicted classes with their probabilities, additive
    # to the existing `predicted_industry`/`alternatives` fields. This is NOT multi-label
    # classification — the source dataset (see ml/DATASETS.md) has exactly one ground-truth
    # industry per row, so there is no legitimate multi-label signal to train against. Presenting
    # a second most-likely class alongside its own probability is honest (it is exactly what the
    # model computed) and useful for genuinely cross-domain pitches, without claiming the startup
    # truly belongs to two industries at once.
    primary_industry, primary_confidence = predicted_label, confidence
    secondary_industry = ranked[1][0] if len(ranked) > 1 else None
    secondary_confidence = runner_up_confidence if len(ranked) > 1 else None

    if is_embedding_model:
        explanation = _embedding_explanation(model, metadata, text)
    else:
        explanation = explain_prediction(model, text, predicted_label)

    # No recognized vocabulary means the vectorizer produced an all-zero vector, so the
    # prediction reflects only the training class prior — not any signal from this input. Under
    # class imbalance (see ml/DATASETS.md — 'b2b' is ~49% of training data), that prior alone can
    # still clear the confidence/margin thresholds below, so this check is independent of them.
    # This check is only meaningful for the TF-IDF vectorizer path — embedding models always
    # produce a dense, non-zero vector even for out-of-domain text, so "no vocabulary" isn't a
    # concept that applies to them (their uncertainty is still caught by the confidence/ambiguity
    # checks below).
    if is_embedding_model:
        has_no_vocabulary = False
    else:
        vectorizer = model.named_steps.get("tfidf")
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

    # Confidence-threshold abstention layer (see ml/DATASETS.md "Abstention" for the coverage/
    # accuracy trade-off this threshold was chosen from). Additive fields — `is_uncertain`/
    # `uncertainty_reasons` above are unchanged and still reflect the original three heuristics;
    # `is_low_confidence`/`abstention_reason` are a distinct, threshold-only signal a caller can
    # use to decide whether to withhold the prediction entirely rather than show it with caveats.
    abstention_threshold = metadata.get("abstention", {}).get(
        "recommended_default_threshold", DEFAULT_ABSTENTION_THRESHOLD
    ) if isinstance(metadata.get("abstention"), dict) else DEFAULT_ABSTENTION_THRESHOLD
    is_below_abstention_threshold = bool(confidence < abstention_threshold)
    abstention_reason = (
        f"Top prediction confidence ({confidence:.2f}) is below the recommended abstention "
        f"threshold ({abstention_threshold}) — consider withholding this prediction or asking "
        "for more detail rather than presenting it as reliable."
        if is_below_abstention_threshold
        else None
    )

    return {
        "predicted_industry": predicted_label,
        "confidence": float(confidence),
        "alternatives": alternatives,
        "model_version": PUBLIC_MODEL_VERSION,
        "model_pipeline": metadata.get("selected_pipeline", "unknown"),
        "explanation": explanation,
        "is_uncertain": has_no_vocabulary or is_low_confidence or is_ambiguous,
        "uncertainty_reasons": uncertainty_reasons,
        # --- additive fields below (Industry Classifier V2 upgrade) ---
        "primary_industry": primary_industry,
        "primary_confidence": primary_confidence,
        "secondary_industry": secondary_industry,
        "secondary_confidence": secondary_confidence,
        "is_low_confidence": is_below_abstention_threshold,
        "abstention_threshold": abstention_threshold,
        "abstention_reason": abstention_reason,
    }


def _embedding_explanation(model, metadata: dict, text: str) -> dict:
    """Nearest-training-example explanation for an embedding-based winner (see
    ml/src/explainability/nearest_neighbors.py for why per-dimension importance is not meaningful
    here). Honestly reports unavailable if the training embeddings/texts artifact wasn't saved
    (e.g. an older artifact trained before this feature existed)."""
    from ml.src.explainability.nearest_neighbors import nearest_training_examples

    model_dir = _model_dir()
    train_embeddings_path = model_dir / "train_embeddings.npy"
    train_texts_labels_path = model_dir / "train_texts_labels.json"
    if not train_embeddings_path.exists() or not train_texts_labels_path.exists():
        return {
            "method": "unavailable",
            "available": False,
            "terms": [],
            "note": "Training embeddings/texts artifact not found — cannot compute nearest-neighbor evidence.",
        }

    train_embeddings = np.load(train_embeddings_path)
    train_data = json.loads(train_texts_labels_path.read_text())
    query_embedding = model._embed([text], persist=False)[0]
    return nearest_training_examples(
        query_embedding, train_embeddings, train_data["texts"], train_data["labels"]
    )
