"""Metrics and sanity checks for unsupervised clustering; no classification accuracy."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import calinski_harabasz_score, davies_bouldin_score, silhouette_score


def evaluate_clustering(features: np.ndarray, labels: np.ndarray) -> dict[str, float | int]:
    labels = np.asarray(labels)
    non_noise = labels != -1
    values, assigned = features[non_noise], labels[non_noise]
    unique, counts = np.unique(assigned, return_counts=True)
    if len(unique) < 2 or len(values) <= len(unique):
        raise ValueError("at least two non-noise clusters with sufficient samples are required")
    tiny_threshold = max(20, int(len(values) * 0.01))
    return {
        "silhouette_score": float(silhouette_score(values, assigned)),
        "davies_bouldin_index": float(davies_bouldin_score(values, assigned)),
        "calinski_harabasz_score": float(calinski_harabasz_score(values, assigned)),
        "cluster_count": int(len(unique)),
        "smallest_cluster_size": int(counts.min()),
        "tiny_cluster_count": int((counts < tiny_threshold).sum()),
        "tiny_cluster_threshold": tiny_threshold,
    }
