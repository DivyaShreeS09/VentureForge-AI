import numpy as np
import pandas as pd
import pytest

from ml.src.features.success_features import ALL_FEATURES, NUMERIC_FEATURES, engineer_features
from ml.src.preprocessing.bootstrap_success_data import generate_bootstrap_success_dataset
from ml.src.preprocessing.success_data import clean_success_dataset


def test_drops_duplicate_permalinks():
    df = pd.DataFrame(
        {
            "permalink": ["/organization/a", "/organization/a"],
            "funding_total_usd": [1000, 1000],
            "funding_rounds": [1, 1],
            "company_age_years": [2.0, 2.0],
            "funding_span_years": [1.0, 1.0],
            "primary_category": ["saas", "saas"],
            "category_count": [1, 1],
            "country_code": ["usa", "usa"],
            "success": [1, 1],
        }
    )
    cleaned = clean_success_dataset(df)
    assert len(cleaned) == 1


def test_normalizes_category_and_country_case():
    df = pd.DataFrame(
        {
            "permalink": ["/organization/a"],
            "funding_total_usd": [1000],
            "funding_rounds": [1],
            "company_age_years": [2.0],
            "funding_span_years": [1.0],
            "primary_category": ["  SaaS  "],
            "category_count": [1],
            "country_code": [" USA "],
            "success": [1],
        }
    )
    cleaned = clean_success_dataset(df)
    assert cleaned.iloc[0]["primary_category"] == "saas"
    assert cleaned.iloc[0]["country_code"] == "usa"


def test_missing_required_column_raises():
    df = pd.DataFrame({"funding_total_usd": [1000]})
    with pytest.raises(ValueError):
        clean_success_dataset(df)


def test_bootstrap_dataset_generates_both_classes_deterministically():
    df1 = generate_bootstrap_success_dataset()
    df2 = generate_bootstrap_success_dataset()
    assert df1.equals(df2)  # fixed seed -> deterministic
    assert set(df1["success"].unique()) == {0, 1}
    assert len(df1) > 0


# --- engineer_features -----------------------------------------------------------------------


def test_engineer_features_adds_expected_columns():
    df = pd.DataFrame(
        {
            "funding_total_usd": [1_000_000],
            "funding_rounds": [2],
            "company_age_years": [4.0],
            "funding_span_years": [1.0],
            "category_count": [1],
        }
    )
    out = engineer_features(df)
    assert "funding_per_round" in NUMERIC_FEATURES
    assert "funding_velocity" in NUMERIC_FEATURES
    assert out.loc[0, "funding_per_round"] == 500_000
    assert out.loc[0, "funding_velocity"] == 0.5


def test_engineer_features_handles_zero_funding_rounds_without_crashing():
    df = pd.DataFrame(
        {
            "funding_total_usd": [1_000_000],
            "funding_rounds": [0],
            "company_age_years": [4.0],
            "funding_span_years": [1.0],
            "category_count": [1],
        }
    )
    out = engineer_features(df)
    assert np.isnan(out.loc[0, "funding_per_round"])


def test_engineer_features_handles_missing_or_non_positive_age_without_crashing():
    df = pd.DataFrame(
        {
            "funding_total_usd": [1_000_000],
            "funding_rounds": [2],
            "company_age_years": [None, ],
            "funding_span_years": [1.0],
            "category_count": [1],
        }
    )
    out = engineer_features(df)
    assert np.isnan(out.loc[0, "funding_velocity"])

    df2 = df.copy()
    df2["company_age_years"] = [0.0]
    out2 = engineer_features(df2)
    assert np.isnan(out2.loc[0, "funding_velocity"])


def test_all_features_list_matches_engineered_columns():
    df = pd.DataFrame(
        {
            "funding_total_usd": [1_000_000],
            "funding_rounds": [2],
            "company_age_years": [4.0],
            "funding_span_years": [1.0],
            "category_count": [1],
            "time_to_first_funding_years": [0.5],
            "funding_recency_years": [1.0],
            "primary_category": ["saas"],
            "country_code": ["usa"],
        }
    )
    out = engineer_features(df)
    for feature in ALL_FEATURES:
        assert feature in out.columns


# --- new v2 date-derived + interaction features -----------------------------------------------


def test_engineer_features_adds_funding_per_category():
    df = pd.DataFrame(
        {
            "funding_total_usd": [1_000_000],
            "funding_rounds": [2],
            "company_age_years": [4.0],
            "funding_span_years": [1.0],
            "category_count": [3],
        }
    )
    out = engineer_features(df)
    assert out.loc[0, "funding_per_category"] == 250_000  # 1_000_000 / (3 + 1)


def test_engineer_features_funding_per_category_handles_missing_category_count():
    df = pd.DataFrame(
        {
            "funding_total_usd": [1_000_000],
            "funding_rounds": [2],
            "company_age_years": [4.0],
            "funding_span_years": [1.0],
            "category_count": [None],
        }
    )
    out = engineer_features(df)
    assert out.loc[0, "funding_per_category"] == 1_000_000  # 1_000_000 / (0 + 1)


def test_time_to_first_funding_and_funding_recency_survive_missing_dates():
    """Mirrors what prepare_success_dataset.py does with missing founded_at/first_funding_at/
    last_funding_at — must not crash, and negative (data-entry-error) durations become NaN."""
    import numpy as np

    founded_at = pd.to_datetime(pd.Series([None, "2020-01-01", "2019-06-01"]))
    first_funding_at = pd.to_datetime(pd.Series(["2021-01-01", None, "2018-01-01"]))
    last_funding_at = pd.to_datetime(pd.Series(["2022-01-01", "2021-01-01", None]))

    time_to_first_funding = (first_funding_at - founded_at).dt.days / 365.25
    time_to_first_funding = time_to_first_funding.where(time_to_first_funding >= 0)

    reference_date = last_funding_at.max()
    funding_recency = (reference_date - last_funding_at).dt.days / 365.25
    funding_recency = funding_recency.where(funding_recency >= 0)

    # Row 0: founded_at missing -> NaN, not a crash.
    assert np.isnan(time_to_first_funding.iloc[0])
    # Row 1: first_funding_at missing -> NaN.
    assert np.isnan(time_to_first_funding.iloc[1])
    # Row 2: first_funding_at (2018) predates founded_at (2019) -> negative duration -> NaN,
    # matching the existing company_age_years convention (data-entry errors treated as missing).
    assert np.isnan(time_to_first_funding.iloc[2])
    # Row 2: last_funding_at missing -> funding_recency NaN, not a crash.
    assert np.isnan(funding_recency.iloc[2])
    # Row 1 last_funding_at (2021) is earlier than the max (2022, row 0) -> positive recency.
    assert funding_recency.iloc[1] > 0
