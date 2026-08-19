"""Build the survival-analysis dataset for the startup success/failure question (Track 2 of the
Success Predictor V2 upgrade — see ml/DATASETS.md "Success Predictor V2 Upgrade").

Unlike the binary classifier (ml/src/preprocessing/prepare_success_dataset.py), which excludes
"operating" (unresolved) companies entirely, survival analysis is specifically designed to use
censored observations — a currently-operating company IS real information: "this company had not
failed or exited as of the last-observed date," which is exactly what right-censoring encodes.
Excluding operating rows here (as the binary classifier does) would throw away the very
observations survival analysis exists to model, and would reproduce the same survivorship-bias
concern that motivates trying survival analysis in the first place.

**Real, documented limitation**: there is no true exit/acquisition date or "as-of" observation
date in this dataset (see ml/DATASETS.md — confirmed, not assumed). `last_funding_at` is used as
the best available proxy for "last observed activity," not a true exit or observation-cutoff
date. This means duration is measured as time-to-last-funding-event, not time-to-actual-outcome,
which introduces **informative censoring risk**: a company that is quietly failing might also
stop raising funding rounds long before it formally closes, so its measured "duration" could
understate its true survival time, and a company's revealed outcome is correlated with how
recently it raised money — a real caveat that is reported here rather than hidden.
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
OUTPUT_PATH = REPO_ROOT / "ml" / "data" / "raw" / "survival_dataset.csv"

RESOLVED_STATUSES = {"closed", "acquired", "ipo"}


def _first_category(category_list: str | float) -> str:
    if not isinstance(category_list, str) or not category_list.strip():
        return "unknown"
    return category_list.split("|")[0].strip().lower() or "unknown"


def _category_count(category_list: str | float) -> int:
    if not isinstance(category_list, str) or not category_list.strip():
        return 0
    return len([c for c in category_list.split("|") if c.strip()])


def prepare_survival_dataset() -> pd.DataFrame:
    """Build duration/event + feature columns from ALL rows (including 'operating'), since
    censored observations are the entire point of a survival analysis. This is the correct,
    intentional use of the previously-excluded operating rows — not a fabrication of extra data.
    """
    if not RAW_SOURCE.exists():
        raise FileNotFoundError(
            f"{RAW_SOURCE} not found. Run `python scripts/download_datasets.py` first "
            "(requires Kaggle credentials — see ml/DATASETS.md)."
        )

    raw = pd.read_csv(RAW_SOURCE)
    before = len(raw)
    raw = raw.drop_duplicates(subset=["permalink"])
    logger.info("Dropped %d exact permalink duplicates", before - len(raw))

    raw["funding_total_usd"] = pd.to_numeric(raw["funding_total_usd"].replace("-", np.nan), errors="coerce")
    for col in ("founded_at", "first_funding_at", "last_funding_at"):
        raw[col] = pd.to_datetime(raw[col], errors="coerce")

    # duration: time from founding to the last recorded funding event, in years. This is a proxy
    # for "time observed" (see module docstring) — not a true exit/censoring date.
    duration_years = (raw["last_funding_at"] - raw["founded_at"]).dt.days / 365.25

    # event = 1 if the company reached a resolved historical outcome (closed/acquired/ipo);
    # event = 0 (censored) if still 'operating' as of this dataset snapshot.
    event = raw["status"].isin(RESOLVED_STATUSES).astype(int)

    raw["primary_category"] = raw["category_list"].apply(_first_category)
    raw["category_count"] = raw["category_list"].apply(_category_count)
    raw["country_code"] = raw["country_code"].fillna("unknown").astype(str).str.strip().str.lower()

    out = pd.DataFrame(
        {
            "permalink": raw["permalink"],
            "duration_years": duration_years,
            "event": event,
            "status": raw["status"],
            "funding_total_usd": raw["funding_total_usd"],
            "funding_rounds": raw["funding_rounds"],
            "category_count": raw["category_count"],
            "primary_category": raw["primary_category"],
            "country_code": raw["country_code"],
        }
    )

    # Duration must be non-negative and non-missing to be usable by CoxPH. Rows with a missing or
    # negative duration (missing founded_at/last_funding_at, or a data-entry error where
    # founded_at postdates last_funding_at) are dropped — reported explicitly, not silently kept
    # as a fabricated zero duration.
    n_before_duration_filter = len(out)
    out = out[out["duration_years"].notna() & (out["duration_years"] >= 0)].copy()
    n_dropped_bad_duration = n_before_duration_filter - len(out)
    logger.info(
        "Dropped %d/%d rows with missing/negative duration (missing founded_at or last_funding_at, "
        "or founded_at postdating last_funding_at)",
        n_dropped_bad_duration,
        n_before_duration_filter,
    )

    # CoxPH requires strictly positive durations for its log-time hazard formulation; a handful of
    # same-day founded_at/last_funding_at rows produce duration == 0. Rather than drop them (losing
    # real observations) or silently keep a zero that breaks the model, nudge them to a small
    # positive epsilon (1 day) — a standard, documented convention for tied zero-duration survival
    # data, not an invented data point.
    zero_duration = out["duration_years"] <= 0
    n_zero_duration = int(zero_duration.sum())
    out.loc[zero_duration, "duration_years"] = 1 / 365.25
    if n_zero_duration:
        logger.info(
            "%d rows had duration == 0 (same-day founded_at/last_funding_at); nudged to 1 day "
            "(a standard convention for tied zero-duration survival data)",
            n_zero_duration,
        )

    out = out.reset_index(drop=True)
    logger.info(
        "Final survival dataset: n=%d, events=%d (%.1f%%), censored=%d (%.1f%%)",
        len(out),
        out["event"].sum(),
        out["event"].mean() * 100,
        (1 - out["event"]).sum(),
        (1 - out["event"]).mean() * 100,
    )
    return out


def main() -> None:
    df = prepare_survival_dataset()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    logger.info("Wrote %d rows to %s", len(df), OUTPUT_PATH)


if __name__ == "__main__":
    main()
