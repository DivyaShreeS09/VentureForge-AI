"""ML Data Acquisition & Corpus Expansion Sprint: merge a third real source --
ml/data/raw/yc_companies_full_directory_2005_2026_raw.csv (kaggle:
alibekmamyrbay/y-combinator-startups-full-directory-20052026, CC-BY-SA-4.0, 5,884 real YC
companies scraped 2026-05-07, spanning every batch Summer 2005 - Spring 2026) -- into the
2-source corpus already built by prepare_yc_expanded_dataset.py.

This is NOT a redundant third copy of the same data: name-overlap analysis (see ml/DATASETS.md
"ML Data Acquisition & Corpus Expansion Sprint") found 998 companies in this source with no
matching name in either existing source, concentrated in three genuinely new coverage windows this
project previously had zero or partial data for: 2005-2011 (pre-dates the oldest existing source
entirely), 2018-2023 (gaps in the existing 2012-2024 export's own coverage), and 2026 (post-dates
even the "2025" source). Deduplication is by exact description text, never by name -- a genuine
3.5% company-name collision rate was found between this source and the existing one (different
real companies sharing a common short name, e.g. "Blink", "Spade", "Atlas" -- the same phenomenon
already documented in this project's duplicate-name audits, not a labeling bug), so name-based
joins would silently miscount the same company or conflate two different ones.

This script only builds the merged corpus for measurement/reporting purposes. Per this sprint's
explicit instruction, no model is retrained on it here.

Run from the repo root: `python -m ml.src.preprocessing.prepare_yc_full_directory_merge`
Writes ml/data/raw/industry_dataset_expanded_v2.csv -- a new file; the production
ml/data/raw/industry_dataset.csv and the prior single-addition
ml/data/raw/industry_dataset_expanded.csv are both left untouched.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_2012_2024 = REPO_ROOT / "ml" / "data" / "raw" / "yc_companies_2012_2024_raw.csv"
RAW_2025 = REPO_ROOT / "ml" / "data" / "raw" / "yc_companies_2025_raw.csv"
RAW_FULL_DIRECTORY = REPO_ROOT / "ml" / "data" / "raw" / "yc_companies_full_directory_2005_2026_raw.csv"
OUTPUT_PATH = REPO_ROOT / "ml" / "data" / "raw" / "industry_dataset_expanded_v2.csv"

EXCLUDED_LABELS = {
    "unspecified": "Not a real industry -- reflects missing source data, not a company attribute.",
    "government": "Too few rows across all three sources combined for a reliable stratified "
    "5-fold split (minimum enforced: 50 rows/class).",
}
MIN_CLASS_SAMPLES = 50
MIN_DESCRIPTION_LENGTH = 10


def _load_2012_2024() -> pd.DataFrame:
    raw = pd.read_csv(RAW_2012_2024)
    one_liner = raw["one_liner"].fillna("").astype(str).str.strip()
    long_description = raw["long_description"].fillna("").astype(str).str.strip()
    description = (one_liner + ". " + long_description).str.strip(". ").str.strip()
    return pd.DataFrame(
        {
            "name": raw["name"].astype(str).str.strip(),
            "description": description,
            "industry": raw["industry"].astype(str).str.strip().str.lower(),
            "source": "yc_2012_2024",
        }
    )


def _load_2025() -> pd.DataFrame:
    raw = pd.read_csv(RAW_2025)
    description = raw["company_description"].fillna("").astype(str).str.strip()
    return pd.DataFrame(
        {
            "name": raw["company_name"].astype(str).str.strip(),
            "description": description,
            "industry": raw["industry_1_url.1"].astype(str).str.strip().str.lower(),
            "source": "yc_2025",
        }
    )


def _load_full_directory() -> pd.DataFrame:
    raw = pd.read_csv(RAW_FULL_DIRECTORY)
    one_liner = raw["one_liner"].fillna("").astype(str).str.strip()
    long_description = raw["long_description"].fillna("").astype(str).str.strip()
    description = (one_liner + ". " + long_description).str.strip(". ").str.strip()
    return pd.DataFrame(
        {
            "name": raw["name"].astype(str).str.strip(),
            "description": description,
            "industry": raw["industry"].astype(str).str.strip().str.lower(),
            "source": "yc_full_directory_2005_2026",
        }
    )


def prepare() -> pd.DataFrame:
    for p in (RAW_2012_2024, RAW_2025, RAW_FULL_DIRECTORY):
        if not p.exists():
            raise FileNotFoundError(f"{p} not found.")

    a, b, c = _load_2012_2024(), _load_2025(), _load_full_directory()
    logger.info("Loaded %d / %d / %d rows from the three sources", len(a), len(b), len(c))

    combined = pd.concat([a, b, c], ignore_index=True)
    combined = combined[combined["description"].str.len() >= MIN_DESCRIPTION_LENGTH]
    logger.info("After minimum-description-length filter: %d rows", len(combined))

    # Deduplicate on exact description text across ALL THREE sources together -- never on name,
    # per the 3.5% name-collision finding documented in the module docstring above. `keep="first"`
    # preserves source-priority order (2012-2024, then 2025, then full-directory) for provenance,
    # though which copy is kept has no effect on label content since true duplicates share identical
    # description text by construction.
    before_dedup = len(combined)
    combined = combined.drop_duplicates(subset=["description"], keep="first").reset_index(drop=True)
    logger.info("Dropped %d exact-text duplicate descriptions across all three sources", before_dedup - len(combined))

    before = len(combined)
    combined = combined[~combined["industry"].isin(EXCLUDED_LABELS.keys())]
    logger.info("Dropped %d rows in explicitly excluded labels %s", before - len(combined), list(EXCLUDED_LABELS))

    counts = combined["industry"].value_counts()
    small_classes = counts[counts < MIN_CLASS_SAMPLES]
    if len(small_classes):
        logger.warning("Dropping additional under-populated classes (< %d rows): %s", MIN_CLASS_SAMPLES, small_classes.to_dict())
        combined = combined[~combined["industry"].isin(small_classes.index)]

    combined = combined.reset_index(drop=True)
    logger.info(
        "Final 3-source merged taxonomy (%d classes, %d rows):\n%s",
        combined["industry"].nunique(), len(combined), combined["industry"].value_counts(),
    )
    logger.info("Rows by source:\n%s", combined["source"].value_counts())
    return combined


def main() -> None:
    df = prepare()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    logger.info("Wrote %d rows to %s", len(df), OUTPUT_PATH)


if __name__ == "__main__":
    main()
