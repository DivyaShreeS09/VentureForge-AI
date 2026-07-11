"""Raw -> cleaned dataset for the industry classifier.

Loads from the real Kaggle-sourced CSV if one has been approved and downloaded (see
ml/DATASETS.md), otherwise falls back to the generated bootstrap corpus
(ml/src/preprocessing/bootstrap_data.py). This fallback is intentional and logged loudly — it is
not a silent substitution.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from ml.src.preprocessing.bootstrap_data import generate_bootstrap_dataset

logger = logging.getLogger(__name__)

MIN_DESCRIPTION_LENGTH = 10
REQUIRED_COLUMNS = {"name", "description", "industry"}


def clean_industry_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Deduplicate, validate, and normalize a raw industry-classification dataframe."""
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"dataset is missing required columns: {sorted(missing)}")

    df = df.copy()
    df["description"] = df["description"].astype(str).str.strip()
    df["name"] = df["name"].astype(str).str.strip()
    df["industry"] = df["industry"].astype(str).str.strip().str.lower()

    df = df[df["description"].str.len() >= MIN_DESCRIPTION_LENGTH]
    df = df[df["industry"] != ""]
    df = df.drop_duplicates(subset=["description"])
    df = df.reset_index(drop=True)
    return df


def load_industry_dataset(raw_csv_path: Path | None = None) -> pd.DataFrame:
    """Load the approved industry-classification dataset, cleaned and ready for feature building."""
    if raw_csv_path is not None and raw_csv_path.exists():
        logger.info("Loading industry dataset from %s", raw_csv_path)
        raw = pd.read_csv(raw_csv_path)
    else:
        logger.warning(
            "No approved real dataset found at %s — falling back to the generated bootstrap "
            "corpus. See ml/DATASETS.md. Metrics computed from this run are NOT representative "
            "of production performance.",
            raw_csv_path,
        )
        raw = generate_bootstrap_dataset()

    return clean_industry_dataset(raw)
