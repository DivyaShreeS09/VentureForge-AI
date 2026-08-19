"""One-time transform: raw YC Kaggle export -> canonical name/description/industry schema.

Source: ml/data/raw/yc_companies_2012_2024_raw.csv (4,522 YC-backed companies, 2012-2024,
CC BY 4.0, kaggle:ibrahimqasimi/y-combinator-companies-2012-2024 — see ml/DATASETS.md for the
full schema profile, license, and exclusion reasoning behind every decision made here).

Run once from the repo root after `python scripts/download_datasets.py`:
    python -m ml.src.preprocessing.prepare_yc_dataset

Writes ml/data/raw/industry_dataset.csv, which ml/src/training/train_industry_classifier.py loads
directly. Both files are git-ignored; this script is what makes the transform reproducible.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_SOURCE = REPO_ROOT / "ml" / "data" / "raw" / "yc_companies_2012_2024_raw.csv"
OUTPUT_PATH = REPO_ROOT / "ml" / "data" / "raw" / "industry_dataset.csv"

# Labels excluded from the canonical taxonomy, and why (see ml/DATASETS.md "Final Taxonomy").
EXCLUDED_LABELS = {
    "unspecified": "Not a real industry — reflects missing source data, not a company attribute.",
    "government": "Only 32 of 4,522 rows — too few for a reliable stratified 5-fold split "
    "(minimum enforced: 50 rows/class). Excluded rather than reported with false confidence.",
}
MIN_CLASS_SAMPLES = 50


def prepare() -> pd.DataFrame:
    if not RAW_SOURCE.exists():
        raise FileNotFoundError(
            f"{RAW_SOURCE} not found. Run `python scripts/download_datasets.py` first "
            "(requires Kaggle credentials — see ml/DATASETS.md)."
        )

    raw = pd.read_csv(RAW_SOURCE)

    one_liner = raw["one_liner"].fillna("").astype(str).str.strip()
    long_description = raw["long_description"].fillna("").astype(str).str.strip()
    description = (one_liner + ". " + long_description).str.strip(". ").str.strip()

    out = pd.DataFrame(
        {
            "name": raw["name"].astype(str).str.strip(),
            "description": description,
            "industry": raw["industry"].astype(str).str.strip().str.lower(),
        }
    )

    before = len(out)
    out = out[~out["industry"].isin(EXCLUDED_LABELS.keys())]
    logger.info("Dropped %d rows in explicitly excluded labels %s", before - len(out), list(EXCLUDED_LABELS))

    counts = out["industry"].value_counts()
    small_classes = counts[counts < MIN_CLASS_SAMPLES]
    if len(small_classes):
        logger.warning(
            "Dropping additional under-populated classes (< %d rows): %s",
            MIN_CLASS_SAMPLES,
            small_classes.to_dict(),
        )
        out = out[~out["industry"].isin(small_classes.index)]

    out = out.reset_index(drop=True)
    logger.info("Final taxonomy (%d classes):\n%s", out["industry"].nunique(), out["industry"].value_counts())
    return out


def main() -> None:
    df = prepare()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    logger.info("Wrote %d rows to %s", len(df), OUTPUT_PATH)


if __name__ == "__main__":
    main()
