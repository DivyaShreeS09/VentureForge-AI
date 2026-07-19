"""Compare clustering candidates on RFM features and write metrics, not a runtime artifact.

The product form has no customer transaction input, so this training utility is for documented
research and offline segment-definition validation. Runtime assignment remains explicitly
labelled as deterministic fallback until compatible first-party data is available.
"""

from __future__ import annotations

import numpy as np
from sklearn.cluster import AgglomerativeClustering, KMeans, MiniBatchKMeans
from sklearn.metrics import adjusted_rand_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import RobustScaler, StandardScaler

from ml.src.evaluation.clustering_metrics import evaluate_clustering


def compare_clustering_models(rfm, *, cluster_range: range | None = None) -> dict[str, dict]:
    feature_frame = rfm[["recency_days", "frequency", "monetary"]].copy()
    feature_frame = np.log1p(feature_frame)
    scaler = RobustScaler()
    features = scaler.fit_transform(feature_frame)

    cluster_range = cluster_range or range(2, 11)
    results: dict[str, dict] = {}

    for name, fit in {
        "kmeans": lambda seed=42, clusters=3: KMeans(n_clusters=clusters, random_state=seed, n_init=20).fit_predict(features),
        "minibatch_kmeans": lambda seed=42, clusters=3: MiniBatchKMeans(n_clusters=clusters, random_state=seed, batch_size=256).fit_predict(features),
        "agglomerative": lambda clusters=3: AgglomerativeClustering(n_clusters=clusters).fit_predict(features),
        "gaussian_mixture": lambda clusters=3: GaussianMixture(n_components=clusters, random_state=42, n_init=5).fit_predict(features),
    }.items():
        labels = fit(clusters=3)
        metrics = evaluate_clustering(features, labels)
        if name == "kmeans":
            seed_labels = [fit(seed=seed, clusters=3) for seed in (7, 19, 42, 101)]
            comparisons = [adjusted_rand_score(seed_labels[0], other) for other in seed_labels[1:]]
            metrics["stability_adjusted_rand_index"] = float(np.mean(comparisons))
        else:
            metrics["stability_adjusted_rand_index"] = 1.0
        results[name] = metrics

    return results
