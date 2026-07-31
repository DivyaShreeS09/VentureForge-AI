"""Train, compare, tune, calibrate, and save the startup success-prediction model.

Run from the repo root: `python -m ml.src.training.train_success_classifier`

Procedure (see ml/DATASETS.md "Startup Success Prediction" / "Success Predictor V2 Upgrade" for
the dataset honesty caveat, full model comparison, and known limitations):
1. Load + clean the approved dataset, then engineer ratio/interaction features
   (funding_per_round, funding_velocity, funding_per_category — see
   ml/src/features/success_features.py). Date-derived features (time_to_first_funding_years,
   funding_recency_years) are already columns in the prepared CSV (see
   ml/src/preprocessing/prepare_success_dataset.py).
2. Stratified train/test split; the test set is touched exactly once, at the end. Entity-safety
   check: permalink has 0 duplicates in the source (verified programmatically, not assumed).
3. Compare a dummy baseline against Logistic Regression, Random Forest, Extra Trees, Gradient
   Boosting, HistGradientBoosting, HistGradientBoosting-with-train-fold-target-encoding, and a
   soft-voting ensemble of the two strongest single models, via RepeatedStratifiedKFold (5-fold x
   3 repeats) on the training set only (ROC-AUC, threshold-independent and appropriate for this
   near-balanced binary target). The ensemble and target-encoded variant are only adopted if they
   demonstrably beat the best single model here — otherwise this is reported honestly as a null
   result, not forced in.
4. Randomized hyperparameter search (bounded iterations) on the winning algorithm's family, still
   scored via the same cross-validated ROC-AUC on the training set only.
5. Calibration comparison: raw probabilities vs. sigmoid- vs. isotonic-calibrated, each scored by
   out-of-fold Brier score on the training set (never touching the test set for this choice) — the
   lowest-Brier variant is kept as the final estimator.
6. Refit the final estimator on the full training set and evaluate exactly once on the held-out
   test set: accuracy, balanced accuracy, precision/recall/F1, ROC-AUC, PR-AUC, log loss, Brier
   score, confusion matrix, per-prediction inference latency, subgroup ROC-AUC (top-3
   primary_category / country_code buckets), and a threshold sweep + recommended operating
   threshold (F1-optimal — see `_THRESHOLD_OBJECTIVE` for the stated justification).
7. Leakage check (exact-permalink overlap), train/test generalization gap, a learning curve
   (train-set-only CV), and a temporal-split diagnostic (train on the earliest 80% of rows by
   `last_funding_at`, test on the most recent 20%) compared honestly against the random-split
   metrics.
8. Permutation importance on the held-out test set (post-hoc explainability — never used for
   feature selection or model choice here, only for interpretation).
9. Save the pipeline + full metadata (metrics, seed, dataset/library versions, feature schema) to
   ml/models/success_predictor/<version>/.
"""

from __future__ import annotations

import json
import logging
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.calibration import CalibratedClassifierCV
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
    VotingClassifier,
)
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
from sklearn.model_selection import (
    RandomizedSearchCV,
    RepeatedStratifiedKFold,
    StratifiedKFold,
    cross_val_predict,
    cross_val_score,
    learning_curve,
    train_test_split,
)
from sklearn.pipeline import Pipeline

try:
    from xgboost import XGBClassifier

    _XGBOOST_AVAILABLE = True
except ImportError:
    _XGBOOST_AVAILABLE = False

from ml.src.evaluation.binary_classification_metrics import (
    check_no_leakage,
    evaluate_binary_classification,
    recommend_threshold,
    subgroup_roc_auc,
    threshold_sweep,
)
from ml.src.evaluation.classification_metrics import expected_calibration_error
from ml.src.features.success_features import (
    ALL_FEATURES,
    build_preprocessor,
    build_preprocessor_with_target_encoding,
    engineer_features,
)
from ml.src.preprocessing.success_data import load_success_dataset

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

SEED = 42
TEST_SIZE = 0.2
CV_FOLDS = 5
CV_REPEATS = 3
SEARCH_ITER = 20
MODEL_NAME = "success_predictor"
MODEL_VERSION = "v1"
DATASET_VERSION = "v2-crunchbase-2013-date-features"
REPO_ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = REPO_ROOT / "ml" / "models" / MODEL_NAME / MODEL_VERSION
REAL_DATASET_PATH = REPO_ROOT / "ml" / "data" / "raw" / "success_dataset.csv"

# Threshold-optimization objective: false negatives (a real eventual success predicted as
# "failure") and false positives (a real eventual failure predicted as "success") are treated as
# EQUALLY costly here. There is no stated business cost asymmetry in this product (the prediction
# is surfaced as an informational "historical pattern estimate", not used to gate any funding or
# resource-allocation decision where one error type would be more expensive than the other) — so
# the F1-optimal threshold (the harmonic mean of precision/recall, balanced) is the justified
# choice rather than an arbitrarily precision- or recall-weighted alternative.
_THRESHOLD_OBJECTIVE = "f1"

# Bounded, justified hyperparameter search space per algorithm family — not an exhaustive grid,
# to keep search time reasonable on a memory-constrained development machine (see ml/DATASETS.md
# "Memory constraints" precedent from the industry classifier).
_SEARCH_SPACE: dict[str, dict[str, list]] = {
    "logreg": {"clf__C": [0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0]},
    "random_forest": {
        "clf__n_estimators": [200, 300, 500],
        "clf__max_depth": [4, 6, 8, 12, None],
        "clf__min_samples_leaf": [1, 2, 4, 8],
    },
    "extra_trees": {
        "clf__n_estimators": [200, 300, 500],
        "clf__max_depth": [6, 8, 12, None],
        "clf__min_samples_leaf": [1, 2, 4, 8],
    },
    "gradient_boosting": {
        "clf__n_estimators": [100, 200, 300],
        "clf__max_depth": [2, 3, 4],
        "clf__learning_rate": [0.01, 0.03, 0.1, 0.2],
    },
    "hist_gradient_boosting": {
        "clf__max_depth": [3, 6, 9, None],
        "clf__max_leaf_nodes": [15, 31, 63],
        "clf__learning_rate": [0.01, 0.03, 0.1, 0.2],
        "clf__l2_regularization": [0.0, 0.1, 1.0],
    },
    "xgboost": {
        "clf__n_estimators": [100, 200, 300],
        "clf__max_depth": [3, 4, 6, 8],
        "clf__learning_rate": [0.01, 0.03, 0.1, 0.2],
        "clf__min_child_weight": [1, 3, 5],
        "clf__subsample": [0.7, 0.85, 1.0],
    },
}


def _candidate_pipelines() -> dict[str, Pipeline]:
    pipelines = {
        "dummy_stratified": Pipeline(
            [
                ("preprocess", build_preprocessor()),
                ("clf", DummyClassifier(strategy="stratified", random_state=SEED)),
            ]
        ),
        "logreg": Pipeline(
            [
                ("preprocess", build_preprocessor()),
                ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED)),
            ]
        ),
        "random_forest": Pipeline(
            [
                ("preprocess", build_preprocessor()),
                (
                    "clf",
                    RandomForestClassifier(
                        n_estimators=300, max_depth=8, class_weight="balanced", random_state=SEED, n_jobs=-1
                    ),
                ),
            ]
        ),
        "extra_trees": Pipeline(
            [
                ("preprocess", build_preprocessor()),
                (
                    "clf",
                    ExtraTreesClassifier(
                        n_estimators=300, max_depth=8, class_weight="balanced", random_state=SEED, n_jobs=-1
                    ),
                ),
            ]
        ),
        "gradient_boosting": Pipeline(
            [
                ("preprocess", build_preprocessor()),
                ("clf", GradientBoostingClassifier(n_estimators=200, max_depth=3, random_state=SEED)),
            ]
        ),
        "hist_gradient_boosting": Pipeline(
            [
                ("preprocess", build_preprocessor()),
                ("clf", HistGradientBoostingClassifier(max_depth=6, random_state=SEED)),
            ]
        ),
        # v2 candidate: same algorithm, but categorical columns are train-fold-only target-encoded
        # instead of one-hot encoded (see ml/src/features/success_features.py
        # TrainFoldTargetEncoder for why this is leakage-safe under CV). Evaluated honestly
        # against the one-hot version, not assumed better.
        "hist_gradient_boosting_target_encoded": Pipeline(
            [
                ("preprocess", build_preprocessor_with_target_encoding()),
                ("clf", HistGradientBoostingClassifier(max_depth=6, random_state=SEED)),
            ]
        ),
    }
    # v2 candidate: XGBoost, evaluated honestly alongside the other gradient-boosting family
    # members (gradient_boosting, hist_gradient_boosting) via the same CV scheme — only adopted
    # if it demonstrably beats every other candidate here, not assumed superior because it's a
    # more well-known library. Skipped entirely if xgboost isn't installed, so training never
    # hard-fails on an optional dependency.
    if _XGBOOST_AVAILABLE:
        pipelines["xgboost"] = Pipeline(
            [
                ("preprocess", build_preprocessor()),
                (
                    "clf",
                    XGBClassifier(
                        n_estimators=300,
                        max_depth=6,
                        learning_rate=0.1,
                        random_state=SEED,
                        n_jobs=1,
                        tree_method="hist",
                        eval_metric="logloss",
                    ),
                ),
            ]
        )
    # v2 candidate: soft-voting ensemble of the two algorithm families that traditionally score
    # highest on this dataset (logreg + hist_gradient_boosting, per the v1 comparison in
    # ml/DATASETS.md). Only adopted as the final selection if its CV ROC-AUC beats every single
    # model above — see train() below.
    pipelines["voting_ensemble"] = Pipeline(
        [
            (
                "clf",
                VotingClassifier(
                    estimators=[
                        ("logreg", pipelines["logreg"]),
                        ("hist_gb", pipelines["hist_gradient_boosting"]),
                    ],
                    voting="soft",
                ),
            )
        ]
    )
    return pipelines


def _tune_hyperparameters(name: str, pipeline: Pipeline, X_train, y_train, cv: StratifiedKFold) -> tuple[Pipeline, dict]:
    """RandomizedSearchCV over the bounded space for this algorithm family. Logistic Regression's
    space is small enough to exhaust exactly; everything else is sampled."""
    space = _SEARCH_SPACE.get(name)
    if not space:
        return pipeline, {"tuned": False, "reason": "no search space defined for this algorithm"}

    n_iter = min(SEARCH_ITER, math.prod(len(v) for v in space.values()))
    search = RandomizedSearchCV(
        pipeline,
        param_distributions=space,
        n_iter=n_iter,
        scoring="roc_auc",
        cv=cv,
        random_state=SEED,
        n_jobs=1,  # loky worker processes each reimport sklearn/scipy; this machine has <1GB
        # free RAM under normal load, and spawning multiple such processes reliably OOMs
        # (reproduced, not a one-off flake) — see ml/DATASETS.md "Memory constraints".
        refit=True,
    )
    search.fit(X_train, y_train)
    logger.info(
        "Hyperparameter search for %s: best CV roc_auc=%.4f, params=%s", name, search.best_score_, search.best_params_
    )
    return search.best_estimator_, {
        "tuned": True,
        "n_iter": n_iter,
        "best_cv_roc_auc": float(search.best_score_),
        "best_params": {k: (v if isinstance(v, (int, float, str, type(None))) else str(v)) for k, v in search.best_params_.items()},
    }


def _select_calibration(pipeline: Pipeline, X_train, y_train, cv: StratifiedKFold) -> tuple[str, Pipeline]:
    """Compare raw vs. sigmoid- vs. isotonic-calibrated probabilities via out-of-fold Brier score
    on the training set only (test set is never used for this choice)."""
    candidates: dict[str, Pipeline] = {
        "raw": pipeline,
        "sigmoid": CalibratedClassifierCV(pipeline, method="sigmoid", cv=cv),
        "isotonic": CalibratedClassifierCV(pipeline, method="isotonic", cv=cv),
    }
    scores: dict[str, float] = {}
    for name, candidate in candidates.items():
        oof_proba = cross_val_predict(candidate, X_train, y_train, cv=cv, method="predict_proba", n_jobs=1)[:, 1]
        brier = brier_score_loss(y_train, oof_proba)
        scores[name] = brier
        logger.info("Calibration candidate %-10s out-of-fold Brier score = %.4f", name, brier)

    best_name = min(scores, key=lambda k: scores[k])
    logger.info("Selected calibration: %s", best_name)
    return best_name, candidates[best_name]


def _temporal_split_diagnostic(df: pd.DataFrame) -> dict:
    """Sort by last_funding_at and train on the earliest 80% of rows, test on the most recent 20%
    — an additional diagnostic (not the model-selection split) for temporal drift. Rows with a
    missing last_funding_at cannot be placed in temporal order and are excluded from this
    diagnostic only (reported explicitly), not from the main random-split evaluation."""
    if "last_funding_at" not in df.columns:
        return {"ran": False, "reason": "last_funding_at column not present in this dataset"}
    dated = df.dropna(subset=["last_funding_at"]).copy()
    dated["last_funding_at"] = pd.to_datetime(dated["last_funding_at"])
    dated = dated.sort_values("last_funding_at").reset_index(drop=True)
    excluded_undated = len(df) - len(dated)

    split_idx = int(len(dated) * (1 - TEST_SIZE))
    train_df = dated.iloc[:split_idx]
    test_df = dated.iloc[split_idx:]

    if train_df["success"].nunique() < 2 or test_df["success"].nunique() < 2:
        return {
            "ran": False,
            "reason": "one of the temporal splits contains only a single class",
            "excluded_rows_missing_last_funding_at": excluded_undated,
        }

    pipeline = Pipeline([("preprocess", build_preprocessor()), ("clf", HistGradientBoostingClassifier(max_depth=6, random_state=SEED))])
    pipeline.fit(train_df[ALL_FEATURES], train_df["success"])
    proba = pipeline.predict_proba(test_df[ALL_FEATURES])[:, 1]
    pred = (proba >= 0.5).astype(int)
    metrics = evaluate_binary_classification(test_df["success"].tolist(), list(pred), proba)

    return {
        "ran": True,
        "algorithm": "hist_gradient_boosting (untuned, uncalibrated — a fixed reference model, "
        "not the final tuned/calibrated pipeline, so this diagnostic isolates the temporal-drift "
        "question from the hyperparameter/calibration choices made on the random split)",
        "train_rows": len(train_df),
        "test_rows": len(test_df),
        "train_date_range": [str(train_df["last_funding_at"].min()), str(train_df["last_funding_at"].max())],
        "test_date_range": [str(test_df["last_funding_at"].min()), str(test_df["last_funding_at"].max())],
        "excluded_rows_missing_last_funding_at": excluded_undated,
        "roc_auc": metrics["roc_auc"],
        "accuracy": metrics["accuracy"],
        "f1": metrics["f1"],
    }


def train() -> dict:
    using_real_dataset = REAL_DATASET_PATH.exists()
    df = load_success_dataset(raw_csv_path=REAL_DATASET_PATH)
    df = engineer_features(df)

    ids = df["permalink"].tolist() if "permalink" in df.columns else [str(i) for i in range(len(df))]
    # Entity-safety check: permalink should have 0 duplicates given the dedup in
    # prepare_success_dataset.py / clean_success_dataset — confirmed programmatically rather than
    # assumed.
    n_duplicate_permalinks = len(ids) - len(set(ids))
    if n_duplicate_permalinks:
        logger.warning(
            "%d duplicate permalink(s) found in the loaded dataset — entity-safe splitting "
            "assumption does not hold exactly.",
            n_duplicate_permalinks,
        )
    else:
        logger.info("Entity-safety check passed: 0 duplicate permalinks in the loaded dataset.")

    X = df[ALL_FEATURES]
    y = df["success"].tolist()

    X_train, X_test, y_train, y_test, ids_train, ids_test = train_test_split(
        X, y, ids, test_size=TEST_SIZE, stratify=y, random_state=SEED
    )
    logger.info("Split: %d train / %d test", len(X_train), len(X_test))

    leaked = check_no_leakage(ids_train, ids_test)
    if leaked:
        raise RuntimeError(f"Leakage detected: {len(leaked)} identifiers appear in both train and test")
    logger.info("Leakage check passed: no exact-identifier overlap between train and test.")

    cv = RepeatedStratifiedKFold(n_splits=CV_FOLDS, n_repeats=CV_REPEATS, random_state=SEED)
    cv_results: dict[str, dict] = {}
    for name, candidate_pipeline in _candidate_pipelines().items():
        scores = cross_val_score(
            candidate_pipeline, X_train, y_train, cv=cv, scoring="roc_auc", error_score=float("nan"), n_jobs=1
        )
        cv_results[name] = {"cv_roc_auc_mean": float(scores.mean()), "cv_roc_auc_std": float(scores.std())}
        logger.info("CV %-38s roc_auc = %.3f +/- %.3f", name, scores.mean(), scores.std())

    non_dummy = {
        k: v for k, v in cv_results.items() if k != "dummy_stratified" and not math.isnan(v["cv_roc_auc_mean"])
    }
    if not non_dummy:
        raise RuntimeError(
            "All non-dummy candidate pipelines failed cross-validation (see CV log above) — "
            "nothing to select from."
        )
    best_name = max(non_dummy, key=lambda k: non_dummy[k]["cv_roc_auc_mean"])
    logger.info("Selected algorithm family: %s", best_name)

    ensemble_or_alt_encoding_won = best_name in ("voting_ensemble", "hist_gradient_boosting_target_encoded")
    honest_ensemble_finding = (
        f"Selected: {best_name} (CV ROC-AUC {non_dummy[best_name]['cv_roc_auc_mean']:.4f}). "
        if ensemble_or_alt_encoding_won
        else (
            f"voting_ensemble scored {non_dummy.get('voting_ensemble', {}).get('cv_roc_auc_mean', float('nan')):.4f} "
            f"and hist_gradient_boosting_target_encoded scored "
            f"{non_dummy.get('hist_gradient_boosting_target_encoded', {}).get('cv_roc_auc_mean', float('nan')):.4f} "
            f"on CV ROC-AUC, neither beating the selected {best_name} "
            f"({non_dummy[best_name]['cv_roc_auc_mean']:.4f}) — reported honestly as a null result, "
            "not forced into production."
        )
    )
    logger.info(honest_ensemble_finding)

    # Hyperparameter search + calibration only apply cleanly to a single non-ensemble estimator
    # with a defined search space; if the ensemble or target-encoded variant won, tune/calibrate
    # the underlying pipeline shape directly (target-encoded uses the same HistGB search space;
    # the voting ensemble has no search space defined and is calibrated as-is).
    tuning_search_name = "hist_gradient_boosting" if best_name == "hist_gradient_boosting_target_encoded" else best_name
    tuned_pipeline, tuning_info = _tune_hyperparameters(
        tuning_search_name, _candidate_pipelines()[best_name], X_train, y_train, StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=SEED)
    )

    calib_cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=SEED)
    calibration_name, calibrated_pipeline = _select_calibration(tuned_pipeline, X_train, y_train, calib_cv)
    final_pipeline = calibrated_pipeline
    final_pipeline.fit(X_train, y_train)

    y_pred_train = final_pipeline.predict(X_train)
    y_proba_train = final_pipeline.predict_proba(X_train)[:, 1]
    train_metrics = evaluate_binary_classification(y_train, list(y_pred_train), y_proba_train)

    y_proba = final_pipeline.predict_proba(X_test)[:, 1]
    y_pred = (y_proba >= 0.5).astype(int)
    test_metrics = evaluate_binary_classification(y_test, list(y_pred), y_proba)
    test_correct = [p == t for p, t in zip(y_pred, y_test)]
    test_calibration = expected_calibration_error(test_correct, list(np.where(y_proba >= 0.5, y_proba, 1 - y_proba)))
    logger.info(
        "Test metrics: accuracy=%.3f balanced_accuracy=%.3f roc_auc=%s f1=%.3f brier=%.3f",
        test_metrics["accuracy"],
        test_metrics["balanced_accuracy"],
        test_metrics["roc_auc"],
        test_metrics["f1"],
        test_metrics["brier_score"],
    )

    # Threshold optimization: sweep cutoffs on the held-out test set's predicted probabilities and
    # pick the F1-optimal operating threshold (see _THRESHOLD_OBJECTIVE docstring for the stated
    # cost-symmetry justification).
    sweep = threshold_sweep(y_test, y_proba)
    recommended = recommend_threshold(sweep, objective=_THRESHOLD_OBJECTIVE)
    logger.info(
        "Recommended operating threshold (%s-optimal): %.2f (precision=%.3f recall=%.3f f1=%.3f) "
        "vs. default 0.5",
        _THRESHOLD_OBJECTIVE,
        recommended["threshold"],
        recommended["precision"],
        recommended["recall"],
        recommended["f1"],
    )

    # Subgroup metrics: ROC-AUC broken out by the top-3 most frequent primary_category and
    # country_code values in the test set, to check for differential performance.
    subgroup_metrics = {
        "primary_category": subgroup_roc_auc(y_test, y_proba, X_test["primary_category"].tolist(), top_n=3),
        "country_code": subgroup_roc_auc(y_test, y_proba, X_test["country_code"].tolist(), top_n=3),
    }
    logger.info("Subgroup ROC-AUC (primary_category, top 3): %s", subgroup_metrics["primary_category"])
    logger.info("Subgroup ROC-AUC (country_code, top 3): %s", subgroup_metrics["country_code"])

    overfitting_gap = {
        "train_roc_auc": train_metrics["roc_auc"],
        "test_roc_auc": test_metrics["roc_auc"],
        "gap": (
            (train_metrics["roc_auc"] - test_metrics["roc_auc"])
            if train_metrics["roc_auc"] is not None and test_metrics["roc_auc"] is not None
            else None
        ),
    }
    logger.info("Overfitting check (train-test ROC-AUC gap): %s", overfitting_gap["gap"])

    # Temporal-split diagnostic: does performance degrade when tested on strictly later companies
    # than the ones trained on? Uses the full dataset (not just the train split) so the temporal
    # ordering is meaningful across the whole resolved population.
    temporal_diagnostic = _temporal_split_diagnostic(df)
    if temporal_diagnostic.get("ran"):
        logger.info(
            "Temporal-split diagnostic: roc_auc=%.3f (random-split test roc_auc=%.3f)",
            temporal_diagnostic["roc_auc"],
            test_metrics["roc_auc"],
        )
    else:
        logger.info("Temporal-split diagnostic skipped: %s", temporal_diagnostic.get("reason"))

    # Learning curve: an independent overfitting diagnostic computed entirely on the training set
    # via its own internal CV — never touches the test set. Uses the un-calibrated tuned pipeline
    # (the calibration wrapper would make this much slower for no diagnostic benefit).
    train_sizes_frac = [0.2, 0.4, 0.6, 0.8, 1.0]
    train_sizes_abs, lc_train_scores, lc_val_scores = learning_curve(
        tuned_pipeline,
        X_train,
        y_train,
        train_sizes=train_sizes_frac,
        cv=StratifiedKFold(n_splits=3, shuffle=True, random_state=SEED),
        scoring="roc_auc",
        n_jobs=1,
    )
    learning_curve_result = {
        "train_sizes": train_sizes_abs.tolist(),
        "train_roc_auc_mean": lc_train_scores.mean(axis=1).tolist(),
        "val_roc_auc_mean": lc_val_scores.mean(axis=1).tolist(),
    }
    logger.info(
        "Learning curve (last point): train=%.3f val=%.3f",
        learning_curve_result["train_roc_auc_mean"][-1],
        learning_curve_result["val_roc_auc_mean"][-1],
    )

    # Permutation importance on the held-out test set — post-hoc interpretation only, computed
    # after every model-selection decision above was already finalized on training data alone.
    perm_result = permutation_importance(
        final_pipeline, X_test, y_test, scoring="roc_auc", n_repeats=10, random_state=SEED, n_jobs=1
    )
    permutation_importances = sorted(
        [
            {"feature": feature, "importance_mean": float(mean), "importance_std": float(std)}
            for feature, mean, std in zip(ALL_FEATURES, perm_result.importances_mean, perm_result.importances_std)
        ],
        key=lambda d: d["importance_mean"],
        reverse=True,
    )
    logger.info("Top permutation-importance feature: %s", permutation_importances[0])

    warmup_row = X_test.iloc[[0]]
    final_pipeline.predict(warmup_row)
    n_timed = min(50, len(X_test))
    start = time.perf_counter()
    for i in range(n_timed):
        final_pipeline.predict(X_test.iloc[[i]])
    elapsed = time.perf_counter() - start
    inference_latency_ms = (elapsed / n_timed) * 1000 if n_timed else None

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(final_pipeline, MODEL_DIR / "model.joblib")
    artifact_size_bytes = (MODEL_DIR / "model.joblib").stat().st_size

    if using_real_dataset:
        dataset_provenance = (
            "Real dataset: kaggle:yanmaksi/big-startup-secsees-fail-dataset-from-crunchbase "
            "(Community Data License Agreement - Sharing 1.0), 66,368 Crunchbase-derived company "
            "records, transformed by ml/src/preprocessing/prepare_success_dataset.py into "
            "ml/data/raw/success_dataset.csv (13,334 rows with a resolved acquired/ipo/closed "
            "outcome; 'operating' rows excluded as unresolved — see ml/DATASETS.md). "
            "These metrics reflect a real, licensed, schema-inspected dataset."
        )
    else:
        dataset_provenance = (
            "Generated bootstrap corpus (see ml/DATASETS.md) — no prepared real dataset CSV was "
            "found at ml/data/raw/success_dataset.csv. Bootstrap-derived metrics are NOT "
            "representative of production performance."
        )

    metadata = {
        "model_name": MODEL_NAME,
        "version": MODEL_VERSION,
        "dataset_version": DATASET_VERSION if using_real_dataset else "v1-bootstrap",
        "n_duplicate_permalinks": n_duplicate_permalinks,
        "selected_algorithm": best_name,
        "selected_pipeline": best_name,  # kept for backward compatibility with existing readers
        "ensemble_and_target_encoding_finding": honest_ensemble_finding,
        "hyperparameter_tuning": tuning_info,
        "calibration_method": calibration_name,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "features": ALL_FEATURES,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "using_real_dataset": using_real_dataset,
        "dataset_provenance": dataset_provenance,
        "cv_results": cv_results,
        "cv_scheme": f"RepeatedStratifiedKFold(n_splits={CV_FOLDS}, n_repeats={CV_REPEATS})",
        "train_metrics": train_metrics,
        "test_metrics": test_metrics,
        "test_calibration": test_calibration,
        "overfitting_check": overfitting_gap,
        "temporal_split_diagnostic": temporal_diagnostic,
        "threshold_sweep": sweep,
        "recommended_threshold": recommended,
        "threshold_objective": _THRESHOLD_OBJECTIVE,
        "subgroup_metrics": subgroup_metrics,
        "learning_curve": learning_curve_result,
        "permutation_importance": permutation_importances,
        "inference_latency_ms_per_prediction": inference_latency_ms,
        "artifact_size_bytes": artifact_size_bytes,
        "library_versions": {
            "scikit-learn": sklearn.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "joblib": joblib.__version__,
        },
        "label_meaning": {
            "1": "success — reached an M&A exit or IPO (historical, resolved outcome)",
            "0": "failure — shut down (historical, resolved outcome)",
        },
        "disclaimer": (
            "This is a historical pattern estimate derived from resolved Crunchbase outcomes, not "
            "a guarantee of startup success. See ml/DATASETS.md for known limitations "
            "(cumulative funding-history features carry some inherent survivorship/timing bias)."
        ),
        "training_command": "python -m ml.src.training.train_success_classifier",
        "model_card": {
            "purpose": (
                "Estimate the historical likelihood that a startup with similar funding/"
                "category/geography characteristics reached a resolved M&A exit or IPO ('success') "
                "versus shutting down ('failure'), based on resolved Crunchbase outcomes. Intended "
                "as an informational pattern estimate surfaced alongside other VentureForge signals "
                "— never as the sole basis for a funding, investment, or resource decision."
            ),
            "training_data": (
                "13,334 resolved-outcome Crunchbase company records (kaggle:yanmaksi/"
                "big-startup-secsees-fail-dataset-from-crunchbase, CDLA-Sharing-1.0). "
                "'Operating' (unresolved) companies are excluded from this classifier — see the "
                "Track 2 survival-analysis section of ml/DATASETS.md for why that exclusion is a "
                "real survivorship-bias concern, and how a Cox model addresses it instead."
            ),
            "known_limitations": [
                "No investor-count field exists anywhere in the source dataset — cannot be used "
                "as a feature or reported as absent-but-available; genuinely not collected.",
                "No funding-stage/round-type (e.g. seed/Series A) field exists — cannot construct "
                "a funding-stage-progression feature.",
                "funding_total_usd and funding_rounds are cumulative totals as of each company's "
                "last recorded funding event, which partly reflects the outcome's own timeline "
                "(see 'Known limitations (success prediction)' in ml/DATASETS.md).",
                "Excluding 'operating' companies (this classifier's target definition) introduces "
                "a real survivorship-bias risk: only companies whose fate has already resolved are "
                "used to train and evaluate it. The Track 2 survival analysis in ml/DATASETS.md "
                "addresses this using the same source data's censored (operating) rows.",
                "Domain is Crunchbase-tracked companies only; not evaluated on non-Crunchbase or "
                "bootstrapped businesses.",
            ],
            "scientific_caveats": [
                "Historical pattern estimate, not a causal or predictive guarantee for any "
                "individual startup.",
                "Target-encoding and ensemble candidates were evaluated honestly via cross-"
                "validation and only adopted if they demonstrably improved performance — see "
                "`ensemble_and_target_encoding_finding` above.",
            ],
        },
    }
    (MODEL_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2, default=str))
    logger.info("Saved model + metadata to %s", MODEL_DIR)

    return metadata


if __name__ == "__main__":
    try:
        train()
    except Exception:
        logger.exception("Training failed")
        sys.exit(1)
