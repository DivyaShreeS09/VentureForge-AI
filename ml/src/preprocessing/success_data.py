"""Raw -> cleaned dataset loader for the startup success-prediction classifier.

Loads from the real, prepared CSV if one has been produced (see
ml/src/preprocessing/prepare_success_dataset.py), otherwise falls back to the generated bootstrap
corpus (ml/src/preprocessing/bootstrap_success_data.py). This fallback is intentional and logged
loudly — it is not a silent substitution. See ml/DATASETS.md.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from ml.src.preprocessing.bootstrap_success_data import generate_bootstrap_success_dataset

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {
    "funding_total_usd",
    "funding_rounds",
    "company_age_years",
    "funding_span_years",
    "primary_category",
    "category_count",
    "country_code",
    "success",
}


def clean_success_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Validate schema and de-duplicate a raw success-prediction dataframe."""
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"dataset is missing required columns: {sorted(missing)}")

    df = df.copy()
    if "permalink" in df.columns:
        df = df.drop_duplicates(subset=["permalink"])
    df["success"] = df["success"].astype(int)
    df["primary_category"] = df["primary_category"].fillna("unknown").astype(str).str.strip().str.lower()
    df["country_code"] = df["country_code"].fillna("unknown").astype(str).str.strip().str.lower()
    df = df.reset_index(drop=True)
    return df


def load_success_dataset(raw_csv_path: Path | None = None) -> pd.DataFrame:
    """Load the approved success-prediction dataset, cleaned and ready for feature building."""
    if raw_csv_path is not None and raw_csv_path.exists():
        logger.info("Loading success-prediction dataset from %s", raw_csv_path)
        raw = pd.read_csv(raw_csv_path)
    else:
        logger.warning(
            "No prepared real dataset found at %s — falling back to the generated bootstrap "
            "corpus. See ml/DATASETS.md. Metrics computed from this run are NOT representative "
            "of production performance.",
            raw_csv_path,
        )
        raw = generate_bootstrap_success_dataset()

    return clean_success_dataset(raw)
