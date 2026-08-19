"""Tests that the gold evaluation set is genuinely excluded from the train/test pool before any
cross-validation or model selection happens (ml/src/training/train_industry_classifier.py,
`_exclude_gold_rows`). This is the leakage guard required before the gold set can be trusted as an
independent, final report.
"""

from __future__ import annotations

import pandas as pd

from ml.src.training import train_industry_classifier as train_mod


def test_exclude_gold_rows_removes_matching_descriptions(tmp_path, monkeypatch):
    gold_csv = tmp_path / "gold.csv"
    gold_df = pd.DataFrame(
        {
            "name": ["GoldCo", "GoldCo2"],
            "description": ["A gold set description about payments.", "A gold set description about clinics."],
            "industry": ["fintech", "healthcare"],
        }
    )
    gold_df.to_csv(gold_csv, index=False)
    monkeypatch.setattr(train_mod, "GOLD_SET_PATH", gold_csv)

    df = pd.DataFrame(
        {
            "name": ["A", "B", "C"],
            "description": [
                "A gold set description about payments.",  # matches gold row 1 exactly
                "A totally different training row about logistics software.",
                "A gold set description about clinics.",  # matches gold row 2 exactly
            ],
            "industry": ["fintech", "b2b", "healthcare"],
        }
    )

    filtered, n_removed = train_mod._exclude_gold_rows(df)

    assert n_removed == 2
    assert len(filtered) == 1
    assert filtered.iloc[0]["description"] == "A totally different training row about logistics software."
    # Explicit, direct assertion per the required leakage guard: no gold description remains.
    gold_descriptions = set(gold_df["description"])
    assert not any(d in gold_descriptions for d in filtered["description"])


def test_exclude_gold_rows_is_noop_when_no_gold_set_present(tmp_path, monkeypatch):
    monkeypatch.setattr(train_mod, "GOLD_SET_PATH", tmp_path / "does_not_exist.csv")

    df = pd.DataFrame(
        {
            "name": ["A"],
            "description": ["Some training description."],
            "industry": ["b2b"],
        }
    )
    filtered, n_removed = train_mod._exclude_gold_rows(df)
    assert n_removed == 0
    assert len(filtered) == 1


def test_real_gold_set_fully_excluded_from_real_training_pool():
    """If the real dataset + real gold set are present on disk (not guaranteed in every
    environment, e.g. CI without the gitignored raw CSV), verify none of the actual committed
    gold-set descriptions survive into the cleaned training pool."""
    import pytest

    from ml.src.preprocessing.clean_data import load_industry_dataset

    if not train_mod.REAL_DATASET_PATH.exists() or not train_mod.GOLD_SET_PATH.exists():
        pytest.skip("Real dataset or gold set not present in this environment.")

    df = load_industry_dataset(raw_csv_path=train_mod.REAL_DATASET_PATH)
    filtered, n_removed = train_mod._exclude_gold_rows(df)

    gold_df = pd.read_csv(train_mod.GOLD_SET_PATH)
    gold_descriptions = set(gold_df["description"].astype(str).str.strip())
    assert n_removed > 0
    assert not any(d in gold_descriptions for d in filtered["description"])
