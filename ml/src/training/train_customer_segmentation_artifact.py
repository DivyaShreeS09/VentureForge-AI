"""Offline training for the versioned UCI Online Retail segmentation artifact.

Raw data is supplied by a caller or downloaded to a caller-owned temporary location; neither raw
data nor model artifacts are committed to the repository.
"""

from __future__ import annotations

import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering, KMeans, MiniBatchKMeans
from sklearn.metrics import adjusted_rand_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import RobustScaler

from ml.src.evaluation.clustering_metrics import evaluate_clustering
from ml.src.preprocessing.customer_segmentation import build_rfm_features, winsorize_rfm

FEATURE_ORDER = ["recency_days", "frequency", "monetary"]
SCHEMA_VERSION = "1.0"
MODEL_VERSION = "v1"
RANDOM_SEEDS = (7, 19, 42, 101)


def _transformed_features(rfm: pd.DataFrame) -> tuple[np.ndarray, RobustScaler]:
    logged = np.log1p(rfm[FEATURE_ORDER].to_numpy(dtype=float))
    scaler = RobustScaler()
    return scaler.fit_transform(logged), scaler


def _factory(name: str, clusters: int, seed: int):
    if name == "kmeans":
        return KMeans(n_clusters=clusters, random_state=seed, n_init=20)
    if name == "minibatch_kmeans":
        return MiniBatchKMeans(n_clusters=clusters, random_state=seed, n_init=20, batch_size=512)
    if name == "agglomerative":
        return AgglomerativeClustering(n_clusters=clusters, linkage="ward")
    if name == "gaussian_mixture":
        return GaussianMixture(n_components=clusters, random_state=seed, n_init=5, covariance_type="full")
    raise ValueError(f"unknown clustering candidate: {name}")


def _fit_labels(name: str, clusters: int, features: np.ndarray, seed: int) -> np.ndarray:
    model = _factory(name, clusters, seed)
    return model.fit_predict(features)


def _stability(name: str, clusters: int, features: np.ndarray) -> float:
    """Mean adjusted Rand agreement on overlapping 80% resamples."""
    rng = np.random.default_rng(42)
    runs: list[tuple[np.ndarray, np.ndarray]] = []
    sample_size = max(clusters * 3, int(len(features) * 0.8))
    for seed in RANDOM_SEEDS:
        indices = np.sort(rng.choice(len(features), size=sample_size, replace=False))
        runs.append((indices, _fit_labels(name, clusters, features[indices], seed)))
    scores: list[float] = []
    for index, (left_indices, left_labels) in enumerate(runs[:-1]):
        right_indices, right_labels = runs[index + 1]
        common, left_pos, right_pos = np.intersect1d(left_indices, right_indices, return_indices=True)
        if len(common) > clusters:
            scores.append(float(adjusted_rand_score(left_labels[left_pos], right_labels[right_pos])))
    return float(np.mean(scores)) if scores else 0.0


def compare_candidates(rfm: pd.DataFrame, cluster_values: range = range(2, 9)) -> list[dict[str, Any]]:
    features, _ = _transformed_features(rfm)
    candidates: list[dict[str, Any]] = []
    for name in ("kmeans", "minibatch_kmeans", "agglomerative", "gaussian_mixture"):
        for clusters in cluster_values:
            labels = _fit_labels(name, clusters, features, 42)
            metrics = evaluate_clustering(features, labels)
            metrics["stability_adjusted_rand_index"] = _stability(name, clusters, features)
            candidates.append({"model_name": name, "n_clusters": clusters, "metrics": metrics})
    return candidates


def _select_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    viable = [candidate for candidate in candidates if candidate["metrics"]["tiny_cluster_count"] == 0]
    if not viable:
        viable = candidates
    ranking_specs = (
        ("silhouette_score", True),
        ("davies_bouldin_index", False),
        ("calinski_harabasz_score", True),
        ("stability_adjusted_rand_index", True),
    )
    for metric, descending in ranking_specs:
        ordered = sorted(viable, key=lambda item: item["metrics"][metric], reverse=descending)
        for rank, candidate in enumerate(ordered, start=1):
            candidate.setdefault("selection_rank_sum", 0)
            candidate["selection_rank_sum"] += rank
    return min(viable, key=lambda item: (item["selection_rank_sum"], item["n_clusters"], item["model_name"]))


def _segment_labels(rfm: pd.DataFrame, labels: np.ndarray) -> tuple[dict[int, str], list[dict[str, Any]]]:
    profiles: list[dict[str, Any]] = []
    for cluster_id in sorted(np.unique(labels)):
        subset = rfm.iloc[np.flatnonzero(labels == cluster_id)]
        profiles.append({
            "cluster_id": int(cluster_id), "customer_count": int(len(subset)),
            "customer_percentage": float(len(subset) / len(rfm)),
            "median_recency_days": float(subset["recency_days"].median()),
            "mean_recency_days": float(subset["recency_days"].mean()),
            "median_frequency": float(subset["frequency"].median()),
            "mean_frequency": float(subset["frequency"].mean()),
            "median_monetary": float(subset["monetary"].median()),
            "mean_monetary": float(subset["monetary"].mean()),
        })
    recency = pd.Series([p["median_recency_days"] for p in profiles])
    value = pd.Series([p["median_frequency"] * p["median_monetary"] for p in profiles])
    low_r, high_r = recency.quantile([1 / 3, 2 / 3])
    low_v, high_v = value.quantile([1 / 3, 2 / 3])
    mapping: dict[int, str] = {}
    for profile, value_score in zip(profiles, value, strict=True):
        recent, high_value = profile["median_recency_days"] <= low_r, value_score >= high_v
        dormant = profile["median_recency_days"] >= high_r and value_score <= low_v
        at_risk = profile["median_recency_days"] >= high_r
        base = "High-Value Loyal Customers" if recent and high_value else "Recent Buyers" if recent else "Dormant Customers" if dormant else "At-Risk Customers" if at_risk else "Occasional Buyers"
        mapping[profile["cluster_id"]] = f"{base} (Cluster {profile['cluster_id']})"
        profile["segment_name"] = mapping[profile["cluster_id"]]
    return mapping, profiles


def train_customer_segmentation_artifact(dataset_path: Path, artifact_path: Path) -> dict[str, Any]:
    """Train the selected candidate and write a self-describing joblib artifact."""
    frame = pd.read_excel(dataset_path) if dataset_path.suffix.lower() == ".xlsx" else pd.read_csv(dataset_path)
    snapshot = pd.Timestamp("2011-12-10")
    rfm = build_rfm_features(frame, reference_date=snapshot)
    bounded_rfm, outlier_bounds = winsorize_rfm(rfm)
    candidates = compare_candidates(bounded_rfm)
    selected = _select_candidate(candidates)
    features, scaler = _transformed_features(bounded_rfm)
    model = _factory(selected["model_name"], selected["n_clusters"], 42)
    labels = model.fit_predict(features)
    mapping, profiles = _segment_labels(bounded_rfm, labels)
    artifact = {
        "schema_version": SCHEMA_VERSION, "model_version": MODEL_VERSION,
        "feature_order": FEATURE_ORDER, "scaler": scaler, "clustering_model": model,
        "selected_model_name": selected["model_name"], "selected_n_clusters": selected["n_clusters"],
        "segment_label_mapping": mapping, "cluster_profiles": profiles,
        "training_date": datetime.now(timezone.utc).isoformat(), "dataset_name": "uci-online-retail",
        "dataset_version": "uci-online-retail-2010-2011", "dataset_license": "CC BY 4.0",
        "snapshot_date": snapshot.isoformat(), "cleaning_audit": rfm.attrs["cleaning_audit"],
        "outlier_method": "customer-level 1st/99th percentile winsorization", "outlier_bounds": outlier_bounds,
        "evaluation_candidates": candidates, "selected_metrics": selected["metrics"], "random_seed": 42,
        "library_versions": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "sklearn": __import__("sklearn").__version__, "joblib": joblib.__version__},
    }
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, artifact_path)
    return artifact
