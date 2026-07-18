"""Fit and evaluate a Cox Proportional Hazards survival model for startup outcomes (Track 2 of
the Success Predictor V2 upgrade — see ml/DATASETS.md "Success Predictor V2 Upgrade").

Run from the repo root: `python -m ml.src.training.train_survival_model`

Why this exists alongside the binary classifier: the binary classifier
(ml/src/training/train_success_classifier.py) excludes every "operating" (unresolved) company —
which discards real, informative data (that a company is still operating, unfailed, as of the
snapshot date) and introduces a real survivorship-bias concern (only companies whose fate has
already resolved are used to train and evaluate it). A Cox Proportional Hazards model instead
treats "still operating" as a right-censored observation, which is the statistically correct way
to use that information rather than discarding it.

**Documented, real limitation** (see ml/src/preprocessing/survival_data.py module docstring for
detail): there is no true exit/acquisition date or as-of observation date anywhere in this
dataset, so `last_funding_at` is used as a proxy "last observed activity" date. This introduces
informative-censoring risk that this script does not attempt to correct (no correction method is
statistically defensible without a true observation-date field) — reported honestly as a ceiling
on how much this analysis can claim, not hidden.

Procedure:
1. Load ml/data/raw/survival_dataset.csv (built by ml.src.preprocessing.survival_data, which uses
   ALL rows including 'operating' ones — the correct, intentional use of censored data).
2. Feature preparation: log1p + median-impute funding_total_usd, median-impute funding_rounds/
   category_count, collapse primary_category/country_code to their top-N most frequent values
   (rest -> 'other') before one-hot encoding, specifically to control the column count that causes
   CoxPH's well-known collinearity/convergence problems with many one-hot dummy columns.
3. Stratified (by event) train/test split; fit `lifelines.CoxPHFitter` with a ridge penalizer
   (`penalizer=0.1`) on the training set — the standard, honest mitigation for one-hot collinearity
   in a Cox model, not a hidden workaround. Any real convergence warning lifelines raises is
   captured and reported in the metadata, not suppressed.
4. Evaluate: concordance index on both train and held-out test data (lifelines computes this
   directly). Time-dependent AUC / integrated Brier score were evaluated for feasibility (see
   `_TIME_DEPENDENT_METRICS_NOTE`) and not computed — documented why, not silently skipped.
5. Save the fitted model + metadata to ml/models/survival_model/v1/.
"""

from __future__ import annotations

import json
import logging
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import lifelines
import numpy as np
import pandas as pd
from lifelines import CoxPHFitter
from sklearn.model_selection import train_test_split

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

SEED = 42
TEST_SIZE = 0.2
TOP_N_CATEGORY = 10
TOP_N_COUNTRY = 8
PENALIZER = 0.1
MODEL_NAME = "survival_model"
MODEL_VERSION = "v1"
REPO_ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = REPO_ROOT / "ml" / "models" / MODEL_NAME / MODEL_VERSION
SURVIVAL_DATASET_PATH = REPO_ROOT / "ml" / "data" / "raw" / "survival_dataset.csv"

# Time-dependent AUC / integrated Brier score require either (a) lifelines' own
# `CoxPHFitter.predict_survival_function` combined with `lifelines.utils.brier_score` /
# a manual time-grid AUC, which is legitimate but adds real complexity (choosing an evaluation
# time grid, handling ties, and interpreting results correctly takes real care to not silently
# produce a misleading number), or (b) scikit-survival, which is NOT installed here (a compiled
# package judged too risky/heavy to add given this session's memory constraints and time budget —
# see ml/DATASETS.md). Given the time budget for this pass, only the concordance index (lifelines'
# built-in, directly supported metric) is reported as the primary evaluation metric — reported
# honestly as a scope limitation, not silently omitted.
_TIME_DEPENDENT_METRICS_NOTE = (
    "Not computed: time-dependent AUC / integrated Brier score would require either a manual "
    "lifelines time-grid implementation (real complexity/validity risk in the time available) or "
    "scikit-survival (not installed — a compiled package judged too risky to add given this "
    "session's memory constraints). Concordance index (lifelines' directly-supported metric) is "
    "reported as the primary evaluation metric instead."
)


def _collapse_rare(series: pd.Series, top_n: int) -> pd.Series:
    top_values = series.value_counts().head(top_n).index
    return series.where(series.isin(top_values), other="other")


def _prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["funding_total_usd"] = df["funding_total_usd"].fillna(df["funding_total_usd"].median())
    df["log_funding_total_usd"] = np.log1p(df["funding_total_usd"].clip(lower=0))
    df["funding_rounds"] = df["funding_rounds"].fillna(df["funding_rounds"].median())
    df["category_count"] = df["category_count"].fillna(df["category_count"].median())
    df["primary_category"] = _collapse_rare(df["primary_category"].fillna("unknown"), TOP_N_CATEGORY)
    df["country_code"] = _collapse_rare(df["country_code"].fillna("unknown"), TOP_N_COUNTRY)

    feature_cols = ["log_funding_total_usd", "funding_rounds", "category_count"]
    numeric = df[["duration_years", "event"] + feature_cols].copy()
    category_dummies = pd.get_dummies(df["primary_category"], prefix="category", drop_first=True)
    country_dummies = pd.get_dummies(df["country_code"], prefix="country", drop_first=True)
    prepared = pd.concat([numeric, category_dummies, country_dummies], axis=1)
    # lifelines' CoxPHFitter expects plain float/bool-as-int columns.
    for col in category_dummies.columns.tolist() + country_dummies.columns.tolist():
        prepared[col] = prepared[col].astype(int)
    return prepared


def train() -> dict:
    if not SURVIVAL_DATASET_PATH.exists():
        raise FileNotFoundError(
            f"{SURVIVAL_DATASET_PATH} not found. Run "
            "`python -m ml.src.preprocessing.survival_data` first."
        )
    raw = pd.read_csv(SURVIVAL_DATASET_PATH)
    logger.info("Loaded survival dataset: n=%d, events=%d", len(raw), raw["event"].sum())

    prepared = _prepare_features(raw)
    feature_columns = [c for c in prepared.columns if c not in ("duration_years", "event")]

    train_df, test_df = train_test_split(
        prepared, test_size=TEST_SIZE, stratify=prepared["event"], random_state=SEED
    )
    logger.info("Split: %d train / %d test", len(train_df), len(test_df))

    cph = CoxPHFitter(penalizer=PENALIZER)
    convergence_warnings: list[str] = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        cph.fit(train_df, duration_col="duration_years", event_col="event")
        for w in caught:
            convergence_warnings.append(str(w.message))
    if convergence_warnings:
        logger.warning("CoxPH raised %d warning(s) during fit: %s", len(convergence_warnings), convergence_warnings)
    else:
        logger.info("CoxPH fit with no warnings.")

    train_concordance = float(cph.concordance_index_)
    test_concordance = float(cph.score(test_df, scoring_method="concordance_index"))
    logger.info("Concordance index: train=%.4f test=%.4f", train_concordance, test_concordance)

    hazard_ratios = (
        cph.summary[["coef", "exp(coef)", "p"]]
        .reset_index()
        .rename(columns={"index": "feature", "exp(coef)": "hazard_ratio"})
        .sort_values("hazard_ratio", ascending=False)
    )
    hazard_ratio_table = hazard_ratios.to_dict(orient="records")
    for row in hazard_ratio_table:
        for k, v in row.items():
            if isinstance(v, (np.floating, np.integer)):
                row[k] = float(v)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    # lifelines' fitters have no dedicated save_model API (unlike CoxPHFitter's R counterpart) —
    # they are standard picklable Python objects, so joblib (already a project dependency) is used,
    # matching the same persistence mechanism as the binary classifier's pipeline artifact.
    joblib.dump(cph, MODEL_DIR / "model.joblib")

    metadata = {
        "model_name": MODEL_NAME,
        "version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "n_total": len(prepared),
        "n_train": len(train_df),
        "n_test": len(test_df),
        "n_events_total": int(prepared["event"].sum()),
        "n_censored_total": int((1 - prepared["event"]).sum()),
        "feature_columns": feature_columns,
        "top_n_category": TOP_N_CATEGORY,
        "top_n_country": TOP_N_COUNTRY,
        "penalizer": PENALIZER,
        "convergence_warnings": convergence_warnings,
        "concordance_index": {"train": train_concordance, "test": test_concordance},
        "time_dependent_metrics_note": _TIME_DEPENDENT_METRICS_NOTE,
        "hazard_ratios": hazard_ratio_table,
        "duration_definition": (
            "duration_years = (last_funding_at - founded_at) in years. last_funding_at is a proxy "
            "for 'last observed activity', NOT a true exit/observation-cutoff date — see "
            "ml/src/preprocessing/survival_data.py module docstring for the informative-censoring "
            "risk this creates."
        ),
        "event_definition": (
            "event=1 if status in {closed, acquired, ipo} (resolved outcome); event=0 (censored) "
            "if status == 'operating' as of this dataset snapshot."
        ),
        "library_versions": {
            "lifelines": lifelines.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "scientific_caveats": [
            "No true exit/acquisition date exists in this dataset — duration is a proxy "
            "(time-to-last-funding-event), not time-to-actual-outcome, which risks informative "
            "censoring (companies that quietly stop performing may also quietly stop raising "
            "funding rounds before formally closing).",
            "No investor-count or funding-stage/round-type field exists in this dataset (same gap "
            "documented for the binary classifier) — cannot be included as a covariate.",
            "This is a Track 2 exploratory/diagnostic analysis, not integrated into the production "
            "prediction path (see ml/DATASETS.md 'Success Predictor V2 Upgrade' for the explicit "
            "integrate/don't-integrate decision and reasoning).",
        ],
        "disclaimer": (
            "Exploratory survival analysis over historical Crunchbase company records. Not "
            "integrated into the production API; not a guarantee of any startup's time-to-outcome."
        ),
    }
    (MODEL_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2, default=str))
    logger.info("Saved survival model + metadata to %s", MODEL_DIR)
    return metadata


if __name__ == "__main__":
    try:
        train()
    except Exception:
        logger.exception("Survival model training failed")
        sys.exit(1)
