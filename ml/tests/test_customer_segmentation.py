import pandas as pd
import pytest

from ml.src.preprocessing.customer_segmentation import build_rfm_features
from ml.src.training.train_customer_segmentation import compare_clustering_models


def test_rfm_handles_missing_values_and_cancellations():
    frame = pd.DataFrame({"InvoiceNo": ["1", "2", "C3", "4"], "InvoiceDate": ["2024-01-01", "2024-01-02", "2024-01-03", None], "CustomerID": ["a", "a", "a", "b"], "Quantity": [2, 1, 5, 1], "UnitPrice": [3, 4, 2, 2]})
    result = build_rfm_features(frame, pd.Timestamp("2024-01-04"))
    assert result.to_dict("records") == [{"CustomerID": "a", "recency_days": 2.0, "frequency": 2, "monetary": 10}]


def test_rfm_rejects_unknown_schema():
    with pytest.raises(ValueError, match="missing required"):
        build_rfm_features(pd.DataFrame({"customer": ["a"]}))


def test_model_comparison_reports_unsupervised_metrics_and_stability():
    rfm = pd.DataFrame(
        {
            "recency_days": [1, 2, 3, 30, 31, 32, 90, 91, 92],
            "frequency": [20, 21, 19, 8, 7, 9, 1, 2, 1],
            "monetary": [1000, 1100, 900, 350, 320, 380, 30, 40, 25],
        }
    )
    metrics = compare_clustering_models(rfm)
    assert set(metrics) == {"kmeans", "minibatch_kmeans", "gaussian_mixture", "agglomerative"}
    assert "silhouette_score" in metrics["kmeans"]
    assert "davies_bouldin_index" in metrics["kmeans"]
    assert "calinski_harabasz_score" in metrics["kmeans"]
    assert 0 <= metrics["kmeans"]["stability_adjusted_rand_index"] <= 1
