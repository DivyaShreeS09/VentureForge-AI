"""Tests for the survival-analysis dataset builder (ml/src/preprocessing/survival_data.py).

These operate on small inline fixtures (never the real 66k-row raw CSV) so they run fast and
without requiring the git-ignored raw data file to be present.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ml.src.preprocessing import survival_data


def _write_raw_csv(tmp_path, rows: list[dict]) -> Path:
    df = pd.DataFrame(rows)
    path = tmp_path / "startup_success_raw.csv"
    df.to_csv(path, index=False)
    return path


BASE_ROW = {
    "permalink": "/organization/a",
    "name": "A",
    "homepage_url": "",
    "category_list": "Software|Analytics",
    "funding_total_usd": "1000000",
    "status": "closed",
    "country_code": "USA",
    "state_code": "CA",
    "region": "SF Bay",
    "city": "SF",
    "funding_rounds": 2,
    "founded_at": "2010-01-01",
    "first_funding_at": "2011-01-01",
    "last_funding_at": "2012-01-01",
}


@pytest.fixture
def patched_raw_source(tmp_path, monkeypatch):
    def _patch(rows: list[dict]):
        path = _write_raw_csv(tmp_path, rows)
        monkeypatch.setattr(survival_data, "RAW_SOURCE", path)
        return path

    return _patch


def test_duration_is_non_negative(patched_raw_source):
    rows = [
        {**BASE_ROW, "permalink": "/organization/a", "status": "closed"},
        {**BASE_ROW, "permalink": "/organization/b", "status": "operating"},
    ]
    patched_raw_source(rows)
    df = survival_data.prepare_survival_dataset()
    assert (df["duration_years"] >= 0).all()


def test_event_flag_correct_for_resolved_and_operating(patched_raw_source):
    rows = [
        {**BASE_ROW, "permalink": "/organization/a", "status": "closed"},
        {**BASE_ROW, "permalink": "/organization/b", "status": "acquired"},
        {**BASE_ROW, "permalink": "/organization/c", "status": "ipo"},
        {**BASE_ROW, "permalink": "/organization/d", "status": "operating"},
    ]
    patched_raw_source(rows)
    df = survival_data.prepare_survival_dataset().set_index("permalink")
    assert df.loc["/organization/a", "event"] == 1
    assert df.loc["/organization/b", "event"] == 1
    assert df.loc["/organization/c", "event"] == 1
    assert df.loc["/organization/d", "event"] == 0


def test_operating_rows_are_retained_not_excluded(patched_raw_source):
    """Unlike the binary classifier's dataset, survival analysis must KEEP 'operating' rows —
    they are the censored observations the whole method exists to use."""
    rows = [
        {**BASE_ROW, "permalink": "/organization/a", "status": "operating"},
        {**BASE_ROW, "permalink": "/organization/b", "status": "closed"},
    ]
    patched_raw_source(rows)
    df = survival_data.prepare_survival_dataset()
    assert len(df) == 2
    assert (df["event"] == 0).sum() == 1


def test_missing_or_negative_duration_rows_dropped_without_crashing(patched_raw_source):
    rows = [
        {**BASE_ROW, "permalink": "/organization/a", "founded_at": None},  # missing -> dropped
        {
            **BASE_ROW,
            "permalink": "/organization/b",
            "founded_at": "2015-01-01",
            "last_funding_at": "2010-01-01",  # founded after last funding -> negative -> dropped
        },
        {**BASE_ROW, "permalink": "/organization/c"},  # valid
    ]
    patched_raw_source(rows)
    df = survival_data.prepare_survival_dataset()
    assert len(df) == 1
    assert df.iloc[0]["permalink"] == "/organization/c"


def test_zero_duration_nudged_to_small_positive_value(patched_raw_source):
    rows = [
        {
            **BASE_ROW,
            "permalink": "/organization/a",
            "founded_at": "2015-01-01",
            "last_funding_at": "2015-01-01",  # same day -> duration 0
        }
    ]
    patched_raw_source(rows)
    df = survival_data.prepare_survival_dataset()
    assert len(df) == 1
    assert df.iloc[0]["duration_years"] > 0


def test_duplicate_permalinks_dropped(patched_raw_source):
    rows = [
        {**BASE_ROW, "permalink": "/organization/a"},
        {**BASE_ROW, "permalink": "/organization/a"},
    ]
    patched_raw_source(rows)
    df = survival_data.prepare_survival_dataset()
    assert len(df) == 1
