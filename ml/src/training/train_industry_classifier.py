"""Train, compare, and save the industry classification model.

Run from the repo root: `python -m ml.src.training.train_industry_classifier`

Procedure (see ml/DATASETS.md for the dataset honesty caveat, full model comparison, error
analysis, and calibration discussion):
1. Load + clean the approved dataset (real if configured, else the generated bootstrap corpus).
2. Stratified train/test split; the test set is touched exactly once, at the end.
3. Compare a dummy baseline against 6 real candidates (see `_candidate_pipelines`: word TF-IDF,
   char TF-IDF, word+char combined, calibrated variants, ComplementNB, and a TF-IDF -> SVD/LSA
   compact-embedding stand-in) via 5-fold stratified cross-validation on the training set only
   (macro F1) — the highest-scoring non-dummy candidate is selected.
4. Refit the winning pipeline on the full training set and evaluate once on the held-out test set,
   including expected calibration error and per-prediction inference latency.
5. Check for exact-text leakage between train and test.
6. Save the pipeline + metadata (metrics, label taxonomy, seed, dataset provenance) to
   ml/models/industry_classifier/<version>/.
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
from sklearn.decomposition import TruncatedSVD
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV

from ml.src.evaluation.classification_metrics import (
    check_no_leakage,
    evaluate_classification,
    expected_calibration_error,
)
from ml.src.features.build_features import build_text_feature
from ml.src.preprocessing.clean_data import load_industry_dataset

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

SEED = 42
TEST_SIZE = 0.2
CV_FOLDS = 5
MODEL_NAME = "industry_classifier"
MODEL_VERSION = "v2"
TAXONOMY_VERSION = "v2-yc-2012-2024"
REPO_ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = REPO_ROOT / "ml" / "models" / MODEL_NAME / MODEL_VERSION
REAL_DATASET_PATH = REPO_ROOT / "ml" / "data" / "raw" / "industry_dataset.csv"

# On the real dataset (4,438 docs of noisy, real-world text) an unbounded vocabulary with
# min_df=1 grows past 160k features — most of it long-tail typos/rare tokens that add memory and
# overfitting risk without improving generalization. max_features caps this to a size actually
# supportable by ~4.4k training documents; min_df=2 drops terms that appear in only one document
# (which can never generalize to a held-out example anyway). This was found empirically: the
# uncapped vocabulary produced a large enough in-memory model (3 calibrated copies x 7 classes x
# 163k features) to cause real MemoryErrors when unpickled repeatedly in a test run.
MAX_FEATURES = 20_000
MIN_DF = 2

# Char n-gram and combined vocabularies are capped more tightly than the word vocabulary above —
# char_wb n-grams multiply feature count quickly, and this machine has previously hit real
# MemoryErrors during cross-validation (see ml/DATASETS.md "Memory constraints").
CHAR_MAX_FEATURES = 8_000
SVD_COMPONENTS = 100


def _candidate_pipelines() -> dict[str, Pipeline]:
    word_tfidf = TfidfVectorizer(
        min_df=MIN_DF, max_features=MAX_FEATURES, ngram_range=(1, 2), sublinear_tf=True
    )
    char_tfidf = TfidfVectorizer(
        min_df=MIN_DF,
        max_features=CHAR_MAX_FEATURES,
        analyzer="char_wb",
        ngram_range=(3, 5),
        sublinear_tf=True,
    )

    return {
        "dummy_stratified": Pipeline(
            [
                ("tfidf", TfidfVectorizer(min_df=MIN_DF, max_features=MAX_FEATURES)),
                ("clf", DummyClassifier(strategy="stratified", random_state=SEED)),
            ]
        ),
        "tfidf_logreg": Pipeline(
            [
                ("tfidf", word_tfidf),
                ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED)),
            ]
        ),
        "tfidf_linear_svc_calibrated": Pipeline(
            [
                ("tfidf", word_tfidf),
                (
                    "clf",
                    CalibratedClassifierCV(
                        LinearSVC(class_weight="balanced", random_state=SEED), cv=3
                    ),
                ),
            ]
        ),
        "tfidf_complement_nb": Pipeline(
            [
                ("tfidf", TfidfVectorizer(min_df=MIN_DF, max_features=MAX_FEATURES, ngram_range=(1, 1))),
                ("clf", ComplementNB()),
            ]
        ),
        "tfidf_char_logreg": Pipeline(
            [
                ("tfidf", char_tfidf),
                ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED)),
            ]
        ),
        "tfidf_word_char_logreg": Pipeline(
            [
                (
                    "tfidf",
                    FeatureUnion(
                        [
                            ("word", word_tfidf),
                            ("char", char_tfidf),
                        ]
                    ),
                ),
                ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED)),
            ]
        ),
        # Same word+char features as above, with isotonic calibration on top — tested specifically
        # to check whether the plain logistic regression's probabilities (ECE measured after
        # training, see ml/DATASETS.md) can be improved without hurting macro F1.
        "tfidf_word_char_logreg_calibrated": Pipeline(
            [
                (
                    "tfidf",
                    FeatureUnion(
                        [
                            ("word", word_tfidf),
                            ("char", char_tfidf),
                        ]
                    ),
                ),
                (
                    "clf",
                    CalibratedClassifierCV(
                        LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED),
                        method="isotonic",
                        cv=3,
                    ),
                ),
            ]
        ),
        # A compact, non-neural stand-in for a sentence-embedding classifier: TF-IDF -> truncated
        # SVD (LSA) yields a dense 100-dimensional representation, then a linear classifier on top.
        # This is explicitly NOT a pretrained sentence-transformer (no such model was downloaded or
        # evaluated) — it is labeled as LSA everywhere it is reported, never as "embeddings" alone.
        "tfidf_svd_logreg": Pipeline(
            [
                ("tfidf", TfidfVectorizer(min_df=MIN_DF, max_features=MAX_FEATURES, ngram_range=(1, 2))),
                ("svd", TruncatedSVD(n_components=SVD_COMPONENTS, random_state=SEED)),
                ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED)),
            ]
        ),
    }


def train() -> dict:
    using_real_dataset = REAL_DATASET_PATH.exists()
    df = load_industry_dataset(raw_csv_path=REAL_DATASET_PATH)
    df["text"] = [build_text_feature(n, d) for n, d in zip(df["name"], df["description"])]

    labels = sorted(df["industry"].unique())
    logger.info("Loaded %d rows across %d classes: %s", len(df), len(labels), labels)

    X_train, X_test, y_train, y_test = train_test_split(
        df["text"].tolist(),
        df["industry"].tolist(),
        test_size=TEST_SIZE,
        stratify=df["industry"],
        random_state=SEED,
    )
    logger.info("Split: %d train / %d test", len(X_train), len(X_test))

    leaked = check_no_leakage(X_train, X_test)
    if leaked:
        raise RuntimeError(f"Leakage detected: {len(leaked)} texts appear in both train and test")
    logger.info("Leakage check passed: no exact-text overlap between train and test.")

    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=SEED)
    cv_results: dict[str, dict] = {}
    for name, pipeline in _candidate_pipelines().items():
        scores = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring="f1_macro", error_score=float("nan"))
        cv_results[name] = {"cv_macro_f1_mean": float(scores.mean()), "cv_macro_f1_std": float(scores.std())}
        logger.info("CV %-30s macro_f1 = %.3f +/- %.3f", name, scores.mean(), scores.std())

    # NaN-scored candidates (e.g. a fold crashed) must never silently win: max()'s pairwise
    # comparison treats NaN > x and x > NaN as both False, so a NaN candidate first in iteration
    # order would otherwise never be displaced by a later, valid candidate. Filter explicitly.
    non_dummy = {
        k: v for k, v in cv_results.items() if k != "dummy_stratified" and not math.isnan(v["cv_macro_f1_mean"])
    }
    if not non_dummy:
        raise RuntimeError(
            "All non-dummy candidate pipelines failed cross-validation (see CV log above) — "
            "nothing to select from. This machine may be too memory-constrained to fit these "
            "pipelines; see ml/DATASETS.md."
        )
    best_name = max(non_dummy, key=lambda k: non_dummy[k]["cv_macro_f1_mean"])
    logger.info("Selected model: %s", best_name)

    best_pipeline = _candidate_pipelines()[best_name]
    best_pipeline.fit(X_train, y_train)

    y_pred = best_pipeline.predict(X_test)
    y_proba = best_pipeline.predict_proba(X_test) if hasattr(best_pipeline, "predict_proba") else None
    test_metrics = evaluate_classification(y_test, list(y_pred), labels, y_proba)
    logger.info(
        "Test metrics: accuracy=%.3f balanced_accuracy=%.3f macro_f1=%.3f weighted_f1=%.3f",
        test_metrics["accuracy"],
        test_metrics["balanced_accuracy"],
        test_metrics["macro_f1"],
        test_metrics["weighted_f1"],
    )

    calibration = None
    if y_proba is not None:
        top1_confidence = y_proba.max(axis=1)
        correct = [pred == true for pred, true in zip(y_pred, y_test)]
        calibration = expected_calibration_error(correct, list(top1_confidence))
        logger.info("Expected calibration error: %.3f", calibration["expected_calibration_error"])

    # Single-prediction latency, measured on this machine — not a claim about production hardware.
    warmup = X_test[:1] or ["warmup"]
    best_pipeline.predict(warmup)
    n_timed = min(50, len(X_test))
    timed_inputs = X_test[:n_timed]
    start = time.perf_counter()
    for text in timed_inputs:
        best_pipeline.predict([text])
    elapsed = time.perf_counter() - start
    inference_latency_ms = (elapsed / n_timed) * 1000 if n_timed else None

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_pipeline, MODEL_DIR / "model.joblib")

    if using_real_dataset:
        dataset_provenance = (
            "Real dataset: kaggle:ibrahimqasimi/y-combinator-companies-2012-2024 (CC BY 4.0), "
            "4,522 YC-backed companies 2012-2024, transformed by "
            "ml/src/preprocessing/prepare_yc_dataset.py into ml/data/raw/industry_dataset.csv "
            "(7-class taxonomy after excluding 'unspecified' and under-populated 'government'; "
            "see ml/DATASETS.md for the full schema profile and class-balance discussion). "
            "These metrics reflect a real, licensed, schema-inspected dataset."
        )
    else:
        dataset_provenance = (
            "Generated bootstrap corpus (see ml/DATASETS.md) — no real dataset CSV was found at "
            "ml/data/raw/industry_dataset.csv. Bootstrap-derived metrics are NOT representative "
            "of production performance — see limitations in ml/DATASETS.md."
        )

    metadata = {
        "model_name": MODEL_NAME,
        "version": MODEL_VERSION,
        "taxonomy_version": TAXONOMY_VERSION if using_real_dataset else "v1-bootstrap",
        "selected_pipeline": best_name,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "labels": labels,
        "n_train": len(X_train),
        "n_test": len(X_test),
        "using_real_dataset": using_real_dataset,
        "dataset_provenance": dataset_provenance,
        "cv_results": cv_results,
        "test_metrics": test_metrics,
        "calibration": calibration,
        "inference_latency_ms_per_prediction": inference_latency_ms,
    }
    (MODEL_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2))
    logger.info("Saved model + metadata to %s", MODEL_DIR)

    return metadata


if __name__ == "__main__":
    try:
        train()
    except Exception:
        logger.exception("Training failed")
        sys.exit(1)
