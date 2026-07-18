"""Tests for the temporal-split diagnostic in ml/src/training/train_success_classifier.py
(`_temporal_split_diagnostic`): reproducibility (same input -> same output, since SEED is fixed)
and correct, non-crashing handling of missing `last_funding_at` values.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ml.src.training.train_success_classifier import _temporal_split_diagnostic


def _make_df(n_per_class: int = 60) -> pd.DataFrame:
    rng = np.random.default_rng(0)
    rows = []
    dates = pd.date_range("2010-01-01", periods=n_per_class * 2, freq="7D")
    for i, success in enumerate([0, 1] * n_per_class):
        funding = rng.uniform(1e5, 5e6) * (1.5 if success else 1.0)
        rows.append(
            {
                "permalink": f"/organization/{i}",
                "funding_total_usd": funding,
                "funding_rounds": rng.integers(1, 5),
                "company_age_years": rng.uniform(1, 8),
                "funding_span_years": rng.uniform(0, 4),
                "time_to_first_funding_years": rng.uniform(0, 2),
                "funding_recency_years": rng.uniform(0, 3),
                "funding_per_round": funding / max(1, rng.integers(1, 5)),
                "funding_velocity": rng.uniform(0, 2),
                "funding_per_category": funding / 2,
                "primary_category": rng.choice(["saas", "fintech", "ecommerce"]),
                "category_count": rng.integers(1, 4),
                "country_code": rng.choice(["usa", "gbr"]),
                "success": success,
                "last_funding_at": dates[i],
            }
        )
    return pd.DataFrame(rows)


def test_temporal_split_is_deterministic():
    df = _make_df()
    result1 = _temporal_split_diagnostic(df)
    result2 = _temporal_split_diagnostic(df)
    assert result1["ran"] is True
    assert result1 == result2


def test_temporal_split_reports_missing_dates_without_crashing():
    df = _make_df()
    df.loc[df.index[:10], "last_funding_at"] = pd.NaT
    result = _temporal_split_diagnostic(df)
    assert result["ran"] is True
    assert result["excluded_rows_missing_last_funding_at"] == 10


def test_temporal_split_handles_missing_column_gracefully():
    df = _make_df().drop(columns=["last_funding_at"])
    result = _temporal_split_diagnostic(df)
    assert result["ran"] is False
    assert "reason" in result


def test_temporal_split_train_before_test_in_time():
    df = _make_df()
    result = _temporal_split_diagnostic(df)
    assert result["ran"] is True
    train_end = pd.Timestamp(result["train_date_range"][1])
    test_start = pd.Timestamp(result["test_date_range"][0])
    assert train_end <= test_start
