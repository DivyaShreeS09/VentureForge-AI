"""Build a fixed, manually reviewable gold evaluation set for the industry classifier.

Procedure (deterministic, seeded, run once and committed as a static artifact):
1. Load the cleaned, deduplicated industry dataset (same cleaning as training uses).
2. Stratified-sample up to GOLD_PER_CLASS rows per class (fewer if a class has less available),
   using a fixed seed so the selection is reproducible.
3. Write the selected rows (name, description, industry) to ml/data/gold/industry_gold_set.csv.
   Redistribution is permitted: the source dataset is CC BY 4.0
   (kaggle:ibrahimqasimi/y-combinator-companies-2012-2024).

This set is excluded from BOTH the train and test splits in train_industry_classifier.py (by exact
description match) before any cross-validation or model selection happens, so it can never leak
into model choice. It exists purely as an independent, human-reviewable sanity check reported
alongside (never instead of) the held-out test metrics.

Run once from the repo root: `python -m ml.src.evaluation.build_gold_set`
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from ml.src.preprocessing.clean_data import load_industry_dataset

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
REAL_DATASET_PATH = REPO_ROOT / "ml" / "data" / "raw" / "industry_dataset.csv"
GOLD_SET_PATH = REPO_ROOT / "ml" / "data" / "gold" / "industry_gold_set.csv"

SEED = 42
GOLD_PER_CLASS = 20


def build_gold_set() -> pd.DataFrame:
    df = load_industry_dataset(raw_csv_path=REAL_DATASET_PATH)

    parts = []
    for industry, group in df.groupby("industry"):
        n = min(GOLD_PER_CLASS, len(group))
        parts.append(group.sample(n=n, random_state=SEED))
    gold = pd.concat(parts).reset_index(drop=True)

    logger.info(
        "Built gold set: %d rows across %d classes (target %d/class): %s",
        len(gold),
        gold["industry"].nunique(),
        GOLD_PER_CLASS,
        gold["industry"].value_counts().to_dict(),
    )
    return gold[["name", "description", "industry"]]


def main() -> None:
    gold = build_gold_set()
    GOLD_SET_PATH.parent.mkdir(parents=True, exist_ok=True)
    gold.to_csv(GOLD_SET_PATH, index=False)
    logger.info("Wrote %d gold rows to %s", len(gold), GOLD_SET_PATH)


if __name__ == "__main__":
    main()
