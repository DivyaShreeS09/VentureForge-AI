"""Real customer-segmentation artifact loading and runtime fallback logic (Phase 5 / Student 3).

This module provides a safe, version-checked loader for the trained clustering artifact.
It never fabricates output: if the artifact is missing or incompatible, the runtime uses a
clear degraded state that is explicitly labelled as non-ML.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import joblib

from app.core.config import settings

ARTIFACT_PATH = Path(settings.model_dir) / "customer_segmentation" / "artifact.joblib"
SCHEMA_VERSION = "1.0"
MODEL_VERSION = "v1"


class SegmentationArtifactUnavailable(RuntimeError):
    """Raised when no compatible segmentation artifact can be used."""


@functools.lru_cache(maxsize=1)
def load_segmentation_artifact(path: Path | None = None) -> dict[str, Any]:
    """Load a segmentation artifact from disk after validating its schema and version."""
    artifact_path = Path(path) if path is not None else ARTIFACT_PATH
    if not artifact_path.exists():
        raise SegmentationArtifactUnavailable(f"segmentation artifact not found at {artifact_path}")

    payload = joblib.load(artifact_path)
    if not isinstance(payload, dict):
        raise SegmentationArtifactUnavailable("segmentation artifact payload must be a dictionary")

    schema_version = payload.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        raise SegmentationArtifactUnavailable(
            f"unsupported segmentation artifact schema version {schema_version!r}; expected {SCHEMA_VERSION}"
        )

    model_version = payload.get("model_version")
    if not model_version:
        raise SegmentationArtifactUnavailable("segmentation artifact missing model_version")

    feature_order = payload.get("feature_order")
    if not isinstance(feature_order, list) or not feature_order:
        raise SegmentationArtifactUnavailable("segmentation artifact missing feature_order")

    required_keys = {
        "feature_order",
        "selected_model_name",
        "selected_n_clusters",
        "segment_label_mapping",
        "schema_version",
        "model_version",
        "scaler",
        "clustering_model",
        "cluster_profiles",
    }
    missing = sorted(required_keys - set(payload))
    if missing:
        raise SegmentationArtifactUnavailable(f"segmentation artifact missing required keys: {missing}")

    return payload


def predict_customer_segment(rfm: dict[str, float], path: Path | None = None) -> dict[str, Any]:
    """Assign one customer RFM vector using the trained artifact only.

    This function deliberately raises ``SegmentationArtifactUnavailable`` rather than emitting a
    heuristic segment if the artifact or feature schema is unavailable.
    """
    artifact = load_segmentation_artifact(path)
    feature_order = artifact["feature_order"]
    missing = [feature for feature in feature_order if feature not in rfm]
    if missing:
        raise SegmentationArtifactUnavailable(f"customer RFM input missing required feature(s): {missing}")
    values = [[float(rfm[feature]) for feature in feature_order]]
    if any(value < 0 for value in values[0]):
        raise SegmentationArtifactUnavailable("customer RFM features must be non-negative")
    import numpy as np

    transformed = artifact["scaler"].transform(np.log1p(values))
    cluster_id = int(artifact["clustering_model"].predict(transformed)[0])
    name = artifact["segment_label_mapping"].get(cluster_id) or artifact["segment_label_mapping"].get(str(cluster_id))
    if not name:
        raise SegmentationArtifactUnavailable(f"artifact has no segment label for cluster {cluster_id}")
    profile = next((item for item in artifact["cluster_profiles"] if int(item["cluster_id"]) == cluster_id), None)
    if profile is None:
        raise SegmentationArtifactUnavailable(f"artifact has no profile for cluster {cluster_id}")
    return {"cluster_id": cluster_id, "segment_name": name, "profile": profile, "model_version": artifact["model_version"], "dataset_version": artifact["dataset_version"], "selected_model_name": artifact["selected_model_name"]}
