"""One-time transform: raw Crunchbase Kaggle export -> canonical success-prediction schema.

Source: ml/data/raw/startup_success_raw.csv (66,368 companies, Community Data License Agreement -
Sharing 1.0, kaggle:yanmaksi/big-startup-secsees-fail-dataset-from-crunchbase — see ml/DATASETS.md
"Startup Success Prediction — Datasets Evaluated" for the full schema profile, license, and
rejection reasoning for the other candidates inspected).

Only rows with a *resolved* historical outcome are kept for training: `status in
{acquired, ipo, closed}`. Rows with `status == "operating"` are excluded entirely — they have not
yet reached a resolved outcome, so labeling them success or failure would be a fabricated label,
not an observed one. This mirrors the dataset's own stated objective (train on resolved outcomes,
predict on currently-operating companies).

Run once from the repo root after `python scripts/download_datasets.py`:
    python -m ml.src.preprocessing.prepare_success_dataset

Writes ml/data/raw/success_dataset.csv, which
ml/src/training/train_success_classifier.py loads directly. Both the raw export and this output
are git-ignored; this script is what makes the transform reproducible.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_SOURCE = REPO_ROOT / "ml" / "data" / "raw" / "startup_success_raw.csv"
OUTPUT_PATH = REPO_ROOT / "ml" / "data" / "raw" / "success_dataset.csv"

# See ml/DATASETS.md: success = the company reached an M&A exit or IPO; failure = it shut down.
# "operating" is not a resolved outcome and is excluded, not labeled as failure.
SUCCESS_STATUSES = {"acquired", "ipo"}
FAILURE_STATUSES = {"closed"}


def _first_category(category_list: str | float) -> str:
    if not isinstance(category_list, str) or not category_list.strip():
        return "unknown"
    return category_list.split("|")[0].strip().lower() or "unknown"


def _category_count(category_list: str | float) -> int:
    if not isinstance(category_list, str) or not category_list.strip():
        return 0
    return len([c for c in category_list.split("|") if c.strip()])


def prepare() -> pd.DataFrame:
    if not RAW_SOURCE.exists():
        raise FileNotFoundError(
            f"{RAW_SOURCE} not found. Run `python scripts/download_datasets.py` first "
            "(requires Kaggle credentials — see ml/DATASETS.md)."
        )

    raw = pd.read_csv(RAW_SOURCE)
    before = len(raw)

    raw = raw.drop_duplicates(subset=["permalink"])
    logger.info("Dropped %d exact permalink duplicates", before - len(raw))

    resolved = raw[raw["status"].isin(SUCCESS_STATUSES | FAILURE_STATUSES)].copy()
    logger.info(
        "Kept %d/%d rows with a resolved outcome (excluded %d 'operating' rows as unresolved, "
        "not fabricated failures)",
        len(resolved),
        len(raw),
        (raw["status"] == "operating").sum(),
    )

    resolved["funding_total_usd"] = pd.to_numeric(
        resolved["funding_total_usd"].replace("-", np.nan), errors="coerce"
    )

    for col in ("founded_at", "first_funding_at", "last_funding_at"):
        resolved[col] = pd.to_datetime(resolved[col], errors="coerce")

    # Data-entry error guard: a handful of source rows have a date past the real-world present
    # (e.g. one row has last_funding_at = 2105-05-01 — a plain typo in the raw export, not a
    # forecast). A future-dated event is never legitimate, so treat it as missing rather than let
    # it silently become the reference point for any date-derived feature (found via manual
    # verification after the V2 temporal-split diagnostic reported a suspiciously high AUC — see
    # ml/DATASETS.md "Temporal-split diagnostic" for the full investigation).
    now = pd.Timestamp.now()
    for col in ("founded_at", "first_funding_at", "last_funding_at"):
        n_future = (resolved[col] > now).sum()
        if n_future:
            logger.warning("%d row(s) have a future %s (data-entry error) — treated as missing", n_future, col)
        resolved[col] = resolved[col].where(resolved[col] <= now)

    # Company age at last recorded funding event, in years. Negative values (a handful of rows
    # where founded_at postdates last_funding_at — a data-entry error in the source, not our bug)
    # are treated as missing rather than silently kept.
    age_years = (resolved["last_funding_at"] - resolved["founded_at"]).dt.days / 365.25
    resolved["company_age_years"] = age_years.where(age_years >= 0)

    funding_span_years = (resolved["last_funding_at"] - resolved["first_funding_at"]).dt.days / 365.25
    resolved["funding_span_years"] = funding_span_years.where(funding_span_years >= 0, 0.0)

    # New leakage-safe date-derived features (v2). Both are computed purely from funding/founding
    # dates that were already used above (not from the outcome), so neither leaks the target.
    # time_to_first_funding_years: how long the company took to land its first funding event after
    # founding — a real "time to traction" signal. Negative values (data-entry errors where
    # founded_at postdates first_funding_at) are treated as missing, matching the existing
    # company_age_years convention.
    time_to_first_funding = (resolved["first_funding_at"] - resolved["founded_at"]).dt.days / 365.25
    resolved["time_to_first_funding_years"] = time_to_first_funding.where(time_to_first_funding >= 0)

    # funding_recency_years: years between this company's last recorded funding event and the
    # dataset's own maximum last_funding_at (i.e. the most recent funding activity observed across
    # the whole resolved dataset). This is NOT a leak: it is derived only from last_funding_at
    # (already used for company_age_years/funding_span_years above), not from the outcome itself.
    # It is a "how stale is this record" signal, not a forward-looking one.
    reference_date = resolved["last_funding_at"].max()
    funding_recency = (reference_date - resolved["last_funding_at"]).dt.days / 365.25
    resolved["funding_recency_years"] = funding_recency.where(funding_recency >= 0)

    resolved["primary_category"] = resolved["category_list"].apply(_first_category)
    resolved["category_count"] = resolved["category_list"].apply(_category_count)
    resolved["country_code"] = resolved["country_code"].fillna("unknown").astype(str).str.strip()

    out = pd.DataFrame(
        {
            "permalink": resolved["permalink"],
            "name": resolved["name"],
            "funding_total_usd": resolved["funding_total_usd"],
            "funding_rounds": resolved["funding_rounds"],
            "company_age_years": resolved["company_age_years"],
            "funding_span_years": resolved["funding_span_years"],
            "time_to_first_funding_years": resolved["time_to_first_funding_years"],
            "funding_recency_years": resolved["funding_recency_years"],
            "primary_category": resolved["primary_category"],
            "category_count": resolved["category_count"],
            "country_code": resolved["country_code"],
            "success": resolved["status"].isin(SUCCESS_STATUSES).astype(int),
            # Kept for temporal-split diagnostics / survival dataset construction only — never
            # used as a model input feature (see ml/src/features/success_features.py ALL_FEATURES,
            # which deliberately excludes it).
            "last_funding_at": resolved["last_funding_at"],
            "founded_at": resolved["founded_at"],
        }
    )
    out = out.reset_index(drop=True)

    logger.info(
        "Final label distribution (n=%d): success=%d (%.1f%%), failure=%d (%.1f%%)",
        len(out),
        out["success"].sum(),
        out["success"].mean() * 100,
        (1 - out["success"]).sum(),
        (1 - out["success"]).mean() * 100,
    )
    return out


def main() -> None:
    df = prepare()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    logger.info("Wrote %d rows to %s", len(df), OUTPUT_PATH)


if __name__ == "__main__":
    main()
