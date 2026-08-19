"""Smoke test: fit the same pipeline shape used in success-classifier training on a tiny inline
fixture, without touching ml/models/ (the real artifact used by the running backend).
"""

import pandas as pd

from ml.src.evaluation.binary_classification_metrics import (
    check_no_leakage,
    evaluate_binary_classification,
)
from ml.src.features.success_features import ALL_FEATURES, build_preprocessor, engineer_features
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

_FIXTURE = engineer_features(
    pd.DataFrame(
        {
            "funding_total_usd": [1_000_000, 500_000, 20_000_000, 100_000, 15_000_000, 200_000],
            "funding_rounds": [2, 1, 4, 1, 5, 1],
            "company_age_years": [3.0, 1.0, 6.0, 0.5, 7.0, 1.0],
            "funding_span_years": [1.5, 0.5, 3.0, 0.2, 4.0, 0.5],
            "time_to_first_funding_years": [0.5, 0.2, 1.0, 0.1, 1.5, 0.3],
            "funding_recency_years": [0.2, 1.0, 0.0, 2.0, 0.5, 1.5],
            "primary_category": ["saas", "ecommerce", "saas", "ecommerce", "fintech", "fintech"],
            "category_count": [2, 1, 3, 1, 2, 1],
            "country_code": ["usa", "usa", "gbr", "usa", "gbr", "usa"],
        }
    )
)
_LABELS = [1, 0, 1, 0, 1, 0]


def test_pipeline_fits_and_predicts_proba():
    pipeline = Pipeline([("preprocess", build_preprocessor()), ("clf", LogisticRegression())])
    pipeline.fit(_FIXTURE[ALL_FEATURES], _LABELS)

    proba = pipeline.predict_proba(_FIXTURE[ALL_FEATURES].iloc[[0]])[0]
    assert abs(sum(proba) - 1.0) < 1e-6


def test_pipeline_handles_missing_values():
    import numpy as np

    row = _FIXTURE[ALL_FEATURES].iloc[[0]].copy()
    row["funding_total_usd"] = row["funding_total_usd"].astype(float)
    row.loc[:, "funding_total_usd"] = np.nan
    row.loc[:, "primary_category"] = None
    pipeline = Pipeline([("preprocess", build_preprocessor()), ("clf", LogisticRegression())])
    pipeline.fit(_FIXTURE[ALL_FEATURES], _LABELS)
    proba = pipeline.predict_proba(row)[0]
    assert 0.0 <= proba[1] <= 1.0


def test_evaluate_binary_classification_bounds():
    pipeline = Pipeline([("preprocess", build_preprocessor()), ("clf", LogisticRegression())])
    pipeline.fit(_FIXTURE[ALL_FEATURES], _LABELS)
    preds = pipeline.predict(_FIXTURE[ALL_FEATURES])
    proba = pipeline.predict_proba(_FIXTURE[ALL_FEATURES])[:, 1]
    metrics = evaluate_binary_classification(_LABELS, list(preds), proba)
    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert metrics["roc_auc"] is None or 0.0 <= metrics["roc_auc"] <= 1.0


def test_check_no_leakage_detects_overlap():
    overlap = check_no_leakage(["/organization/a", "/organization/b"], ["/organization/b", "/organization/c"])
    assert overlap == ["/organization/b"]


def test_check_no_leakage_empty_when_disjoint():
    overlap = check_no_leakage(["/organization/a"], ["/organization/b"])
    assert overlap == []
