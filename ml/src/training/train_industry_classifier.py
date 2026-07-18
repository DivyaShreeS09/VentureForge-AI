"""Train, compare, and save the industry classification model.

Run from the repo root: `python -m ml.src.training.train_industry_classifier`

Procedure (see ml/DATASETS.md for the dataset honesty caveat, full model comparison, error
analysis, and calibration discussion):
1. Load + clean the approved dataset (real if configured, else the generated bootstrap corpus).
2. Exclude every row whose `description` exact-matches a row in the held-out gold evaluation set
   (`ml/data/gold/industry_gold_set.csv`) BEFORE any split — the gold set is reserved for a final,
   independent report and must never influence training, cross-validation, or model selection.
3. Stratified train/test split; the test set is touched exactly once, at the end.
4. Compare a dummy baseline against TF-IDF candidates (word, char, word+char, calibrated variants,
   ComplementNB, TF-IDF->SVD/LSA) AND frozen sentence-transformer embedding candidates (LogReg,
   calibrated LinearSVC, HistGradientBoosting) via 5-fold stratified cross-validation on the
   training set only (macro F1) — the highest-scoring non-dummy candidate is selected.
5. Refit the winning pipeline on the full training set and evaluate once on the held-out test set,
   including expected calibration error, top-2 accuracy, an abstention coverage/accuracy table,
   and per-prediction inference latency.
6. Separately, evaluate the exact same fitted model on the untouched gold set and report those
   metrics as an independent block — never blended into the CV/test metrics used for selection.
7. Check for exact-text leakage between train and test.
8. Save the pipeline + metadata (metrics, label taxonomy, seed, dataset provenance, governance
   fields) to ml/models/industry_classifier/<version>/.
"""

from __future__ import annotations

import hashlib
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
from sklearn.decomposition import TruncatedSVD
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV

from ml.src.evaluation.classification_metrics import (
    abstention_report,
    check_no_leakage,
    evaluate_classification,
    expected_calibration_error,
    top2_accuracy,
)
from ml.src.features.build_features import build_text_feature
from ml.src.features.embedding_cache import get_or_compute_embeddings
from ml.src.features.embedding_pipeline import EmbeddingClassifier
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
GOLD_SET_PATH = REPO_ROOT / "ml" / "data" / "gold" / "industry_gold_set.csv"
EMBEDDING_CACHE_DIR = REPO_ROOT / "ml" / "data" / "processed"

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# Confidence thresholds explored for the abstention layer (see ml/DATASETS.md "Abstention").
ABSTENTION_THRESHOLDS = [0.4, 0.5, 0.6, 0.7]
RECOMMENDED_ABSTENTION_THRESHOLD = 0.5

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
        # This is explicitly NOT a pretrained sentence-transformer — that comparison is now done
        # for real via the `embed_*` candidates below (see `_embedding_candidates`).
        "tfidf_svd_logreg": Pipeline(
            [
                ("tfidf", TfidfVectorizer(min_df=MIN_DF, max_features=MAX_FEATURES, ngram_range=(1, 2))),
                ("svd", TruncatedSVD(n_components=SVD_COMPONENTS, random_state=SEED)),
                ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED)),
            ]
        ),
    }


def _embedding_candidates() -> dict[str, object]:
    """Sentence-transformer (`all-MiniLM-L6-v2`, 384-dim, frozen/not fine-tuned) embeddings fed
    into three different downstream classifiers, for a real comparison against the TF-IDF
    candidates above (not a synthetic LSA stand-in).

    `n_jobs` is left at its safe default (in-process threading) for `HistGradientBoostingClassifier`
    — no process-based parallelism is used anywhere in this module, per this machine's documented
    MemoryError history with `n_jobs=-1` process pools (see ml/DATASETS.md "Memory constraints").
    """
    return {
        "embed_logreg": LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED),
        "embed_linear_svc_calibrated": CalibratedClassifierCV(
            LinearSVC(class_weight="balanced", random_state=SEED), cv=3
        ),
        # HistGradientBoostingClassifier has no class_weight parameter (unlike the linear
        # candidates) — reported as-is, a real, documented asymmetry in this comparison rather
        # than papering over it with manual sample weights that would break comparability with
        # ml/DATASETS.md's success-predictor precedent for this same algorithm.
        "embed_histgb": HistGradientBoostingClassifier(random_state=SEED),
    }


def _dataset_fingerprint(csv_path: Path) -> str:
    """A sha256 fingerprint of the raw dataset CSV content, for governance/reproducibility —
    lets anyone verify the exact bytes a reported metric set was trained from."""
    if not csv_path.exists():
        return "no-real-dataset-csv-present"
    return hashlib.sha256(csv_path.read_bytes()).hexdigest()


def _library_versions() -> dict[str, str]:
    versions = {
        "python": sys.version.split()[0],
        "scikit-learn": sklearn.__version__,
        "numpy": np.__version__,
        "pandas": pd.__version__,
    }
    try:
        import torch

        versions["torch"] = torch.__version__
    except ImportError:
        versions["torch"] = "not installed"
    try:
        import sentence_transformers

        versions["sentence-transformers"] = sentence_transformers.__version__
    except ImportError:
        versions["sentence-transformers"] = "not installed"
    return versions


def _exclude_gold_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Remove every row whose `description` exact-matches a gold-set description, so the gold
    set can never leak into training, cross-validation, or model selection. Returns the filtered
    dataframe and the number of rows removed."""
    if not GOLD_SET_PATH.exists():
        logger.warning(
            "No gold set found at %s — skipping gold exclusion (nothing to exclude, and the "
            "gold-set evaluation block below will also be skipped).",
            GOLD_SET_PATH,
        )
        return df, 0

    gold_df = pd.read_csv(GOLD_SET_PATH)
    gold_descriptions = set(gold_df["description"].astype(str).str.strip())
    before = len(df)
    df = df[~df["description"].isin(gold_descriptions)].reset_index(drop=True)
    removed = before - len(df)
    logger.info("Excluded %d gold-set rows from the training/test pool (of %d gold rows).", removed, len(gold_df))
    return df, removed


def _check_memory_for_transformer_finetuning() -> tuple[bool, str]:
    """Check free RAM before even considering DistilBERT fine-tuning. This machine has a
    documented history of real MemoryErrors under far lighter loads (see ml/DATASETS.md "Memory
    constraints") — fine-tuning a transformer means holding model weights, gradients, and
    optimizer state simultaneously (2-3x the frozen-inference memory footprint), which is a much
    heavier and more crash-prone workload than anything already causing problems here.
    """
    free_gb = None
    total_gb = None
    try:
        import psutil

        free_gb = psutil.virtual_memory().available / (1024**3)
        total_gb = psutil.virtual_memory().total / (1024**3)
    except ImportError:
        pass

    if free_gb is None and sys.platform == "win32":
        # psutil is not installed in this environment — fall back to the Windows API directly
        # (equivalent to `Get-CimInstance Win32_OperatingSystem`'s FreePhysicalMemory/
        # TotalVisibleMemorySize, without shelling out to PowerShell from Python).
        try:
            import ctypes

            class _MemoryStatusEx(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            mem_status = _MemoryStatusEx()
            mem_status.dwLength = ctypes.sizeof(_MemoryStatusEx)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem_status))  # type: ignore[attr-defined]
            free_gb = mem_status.ullAvailPhys / (1024**3)
            total_gb = mem_status.ullTotalPhys / (1024**3)
        except Exception:  # pragma: no cover - best-effort fallback
            pass

    if free_gb is None:
        return False, "Could not verify free RAM on this platform — assuming unsafe to attempt."

    if free_gb < 3.0:
        return False, (
            f"Only {free_gb:.2f}GB free of {total_gb:.2f}GB total — well below a safe margin for "
            "holding transformer weights + gradients + optimizer state simultaneously. Skipped."
        )
    return True, f"{free_gb:.2f}GB free of {total_gb:.2f}GB total."


def train() -> dict:
    using_real_dataset = REAL_DATASET_PATH.exists()
    df = load_industry_dataset(raw_csv_path=REAL_DATASET_PATH)
    df, n_gold_excluded = _exclude_gold_rows(df)
    df["text"] = [build_text_feature(n, d) for n, d in zip(df["name"], df["description"])]

    labels = sorted(df["industry"].unique())
    logger.info("Loaded %d rows across %d classes (post gold-exclusion): %s", len(df), len(labels), labels)

    all_texts = df["text"].tolist()
    all_labels = df["industry"].tolist()
    row_idx = np.arange(len(df))

    train_idx, test_idx = train_test_split(
        row_idx,
        test_size=TEST_SIZE,
        stratify=df["industry"],
        random_state=SEED,
    )
    X_train = [all_texts[i] for i in train_idx]
    X_test = [all_texts[i] for i in test_idx]
    y_train = [all_labels[i] for i in train_idx]
    y_test = [all_labels[i] for i in test_idx]
    logger.info("Split: %d train / %d test", len(X_train), len(X_test))

    leaked = check_no_leakage(X_train, X_test)
    if leaked:
        raise RuntimeError(f"Leakage detected: {len(leaked)} texts appear in both train and test")
    logger.info("Leakage check passed: no exact-text overlap between train and test.")

    # Sentence embeddings are computed ONCE for the full text pool (train+test), cached to disk,
    # then sliced by fold/split index below — see ml/src/features/embedding_cache.py's docstring
    # for why reusing a frozen embedding matrix across CV folds is not leakage (no label touches
    # the embedding computation).
    logger.info("Computing/loading sentence-transformer embeddings (%s)...", EMBEDDING_MODEL_NAME)
    all_embeddings = get_or_compute_embeddings(all_texts, EMBEDDING_MODEL_NAME, EMBEDDING_CACHE_DIR)
    emb_train = all_embeddings[train_idx]
    emb_test = all_embeddings[test_idx]

    can_finetune, memory_note = _check_memory_for_transformer_finetuning()
    logger.info(
        "DistilBERT fine-tuning consideration: %s %s",
        "proceeding" if can_finetune else "SKIPPED",
        memory_note,
    )
    distilbert_note = (
        "Not attempted — " + memory_note
        if not can_finetune
        else "Memory check passed but fine-tuning was still not implemented in this pass; "
        "frozen sentence-transformer embeddings were evaluated instead as the neural comparison point."
    )

    cv = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=SEED)
    cv_results: dict[str, dict] = {}

    for name, pipeline in _candidate_pipelines().items():
        try:
            # error_score=nan handles *partial* fold failure (some folds fit, some don't) by
            # scoring the failed folds as NaN. But when EVERY fold in a candidate fails (e.g. a
            # MemoryError on this memory-constrained machine — see ml/DATASETS.md "Memory
            # constraints"), scikit-learn's cross_validate raises ValueError instead of returning
            # an all-NaN array — reproduced here for tfidf_svd_logreg. That must be caught here,
            # not left to crash the whole training run, and recorded as NaN so the existing
            # NaN-filtering logic below excludes it from model selection exactly like a
            # partial-failure candidate would be.
            scores = cross_val_score(
                pipeline, X_train, y_train, cv=cv, scoring="f1_macro", error_score=float("nan")
            )
            cv_results[name] = {"cv_macro_f1_mean": float(scores.mean()), "cv_macro_f1_std": float(scores.std())}
            logger.info("CV %-30s macro_f1 = %.3f +/- %.3f", name, scores.mean(), scores.std())
        except (ValueError, MemoryError) as exc:
            logger.error("CV %-30s FAILED entirely (%s) — recording as NaN.", name, exc)
            cv_results[name] = {"cv_macro_f1_mean": float("nan"), "cv_macro_f1_std": float("nan")}

    y_train_arr = np.asarray(y_train)
    embedding_candidate_names = list(_embedding_candidates().keys())
    for name in embedding_candidate_names:
        fold_scores = []
        try:
            for fold_train_idx, fold_val_idx in cv.split(emb_train, y_train):
                clf = _embedding_candidates()[name]  # fresh unfitted estimator each fold
                clf.fit(emb_train[fold_train_idx], y_train_arr[fold_train_idx])
                preds = clf.predict(emb_train[fold_val_idx])
                fold_scores.append(
                    f1_score(y_train_arr[fold_val_idx], preds, average="macro", zero_division=0)
                )
            scores_arr = np.asarray(fold_scores)
            cv_results[name] = {
                "cv_macro_f1_mean": float(scores_arr.mean()),
                "cv_macro_f1_std": float(scores_arr.std()),
            }
            logger.info("CV %-30s macro_f1 = %.3f +/- %.3f", name, scores_arr.mean(), scores_arr.std())
        except MemoryError:
            logger.exception("MemoryError during CV for embedding candidate %s — recording as NaN.", name)
            cv_results[name] = {"cv_macro_f1_mean": float("nan"), "cv_macro_f1_std": float("nan")}

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

    is_embedding_winner = best_name in _embedding_candidates()
    if is_embedding_winner:
        best_model = EmbeddingClassifier(
            _embedding_candidates()[best_name], EMBEDDING_MODEL_NAME, EMBEDDING_CACHE_DIR
        )
        best_model.fit(X_train, y_train, embeddings=emb_train)
        y_pred = best_model.predict(X_test, embeddings=emb_test)
        y_proba = (
            best_model.predict_proba(X_test, embeddings=emb_test)
            if hasattr(best_model.classifier, "predict_proba")
            else None
        )
    else:
        best_model = _candidate_pipelines()[best_name]
        best_model.fit(X_train, y_train)
        y_pred = best_model.predict(X_test)
        y_proba = best_model.predict_proba(X_test) if hasattr(best_model, "predict_proba") else None

    test_metrics = evaluate_classification(y_test, list(y_pred), labels, y_proba)
    logger.info(
        "Test metrics: accuracy=%.3f balanced_accuracy=%.3f macro_f1=%.3f weighted_f1=%.3f",
        test_metrics["accuracy"],
        test_metrics["balanced_accuracy"],
        test_metrics["macro_f1"],
        test_metrics["weighted_f1"],
    )

    calibration = None
    test_top2_accuracy = None
    test_abstention = None
    if y_proba is not None:
        top1_confidence = y_proba.max(axis=1)
        correct = [pred == true for pred, true in zip(y_pred, y_test)]
        calibration = expected_calibration_error(correct, list(top1_confidence))
        logger.info("Expected calibration error: %.3f", calibration["expected_calibration_error"])
        test_top2_accuracy = top2_accuracy(y_test, y_proba, labels)
        test_abstention = abstention_report(y_test, list(y_pred), y_proba, ABSTENTION_THRESHOLDS)
        logger.info("Test top-2 accuracy: %.3f", test_top2_accuracy)

    # Calibration comparison across the calibrated candidates specifically (refit on the full
    # training set, ECE measured on the same held-out test set) — reported alongside, never
    # substituted for, the winning model's own metrics above.
    calibration_comparison = {}
    calibrated_candidate_names = [
        n for n in cv_results if "calibrated" in n and n in non_dummy
    ]
    for name in calibrated_candidate_names:
        try:
            if name in _embedding_candidates():
                model = EmbeddingClassifier(_embedding_candidates()[name], EMBEDDING_MODEL_NAME, EMBEDDING_CACHE_DIR)
                model.fit(X_train, y_train, embeddings=emb_train)
                proba = model.predict_proba(X_test, embeddings=emb_test)
                preds = model.predict(X_test, embeddings=emb_test)
            else:
                model = _candidate_pipelines()[name]
                model.fit(X_train, y_train)
                proba = model.predict_proba(X_test)
                preds = model.predict(X_test)
            conf = proba.max(axis=1)
            corr = [p == t for p, t in zip(preds, y_test)]
            ece = expected_calibration_error(corr, list(conf))
            calibration_comparison[name] = ece["expected_calibration_error"]
            logger.info("Calibration comparison %-35s ECE = %.3f", name, ece["expected_calibration_error"])
        except MemoryError:
            logger.exception("MemoryError computing calibration comparison for %s — skipping.", name)
            calibration_comparison[name] = None

    # Single-prediction latency, measured on this machine — not a claim about production hardware.
    warmup = X_test[:1] or ["warmup"]
    best_model.predict(warmup)
    n_timed = min(50, len(X_test))
    timed_inputs = X_test[:n_timed]
    start = time.perf_counter()
    for text in timed_inputs:
        best_model.predict([text])
    elapsed = time.perf_counter() - start
    inference_latency_ms = (elapsed / n_timed) * 1000 if n_timed else None

    # --- Gold-set evaluation: a fully independent, additional block. The gold set was excluded
    # from df above (via _exclude_gold_rows) before the split, so nothing below has touched or
    # influenced model selection in any way. ---
    gold_block = None
    if GOLD_SET_PATH.exists():
        gold_df = pd.read_csv(GOLD_SET_PATH)
        gold_texts = [
            build_text_feature(n, d) for n, d in zip(gold_df["name"], gold_df["description"])
        ]
        gold_labels = gold_df["industry"].astype(str).str.strip().str.lower().tolist()

        if is_embedding_winner:
            gold_embeddings = get_or_compute_embeddings(
                gold_texts, EMBEDDING_MODEL_NAME, EMBEDDING_CACHE_DIR
            )
            gold_pred = best_model.predict(gold_texts, embeddings=gold_embeddings)
            gold_proba = (
                best_model.predict_proba(gold_texts, embeddings=gold_embeddings)
                if hasattr(best_model.classifier, "predict_proba")
                else None
            )
        else:
            gold_pred = best_model.predict(gold_texts)
            gold_proba = best_model.predict_proba(gold_texts) if hasattr(best_model, "predict_proba") else None

        gold_metrics = evaluate_classification(gold_labels, list(gold_pred), labels, gold_proba)
        gold_top2 = None
        gold_abstention = None
        if gold_proba is not None:
            gold_top2 = top2_accuracy(gold_labels, gold_proba, labels)
            gold_abstention = abstention_report(gold_labels, list(gold_pred), gold_proba, ABSTENTION_THRESHOLDS)

        gold_block = {
            "n_gold_rows": len(gold_df),
            "metrics": gold_metrics,
            "top2_accuracy": gold_top2,
            "abstention": gold_abstention,
        }
        logger.info(
            "Gold-set metrics: accuracy=%.3f macro_f1=%.3f (n=%d, independent — never used for selection)",
            gold_metrics["accuracy"],
            gold_metrics["macro_f1"],
            len(gold_df),
        )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, MODEL_DIR / "model.joblib")

    if is_embedding_winner:
        # Per-dimension feature importance is not meaningful for these embeddings (see
        # ml/src/explainability/nearest_neighbors.py) — the substitute explanation method is
        # nearest-training-example retrieval, which needs the training embeddings + their texts
        # and labels available at serving time. Persisted alongside the model artifact.
        np.save(MODEL_DIR / "train_embeddings.npy", emb_train)
        (MODEL_DIR / "train_texts_labels.json").write_text(
            json.dumps({"texts": X_train, "labels": y_train})
        )
        logger.info("Saved training embeddings + texts/labels for nearest-neighbor explainability.")

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

    model_card = (
        "PURPOSE: classify a startup's industry (one of 7 classes) from a short name+description "
        "founder pitch, to drive downstream market/competitor/persona agents. LIMITATIONS: trained "
        "exclusively on YC-backed startups 2012-2024 (English-only, YC vocabulary/framing); "
        "B2B is ~49% of training data, so ambiguous 'platform'-style language biases toward B2B; "
        "the smallest class (education) has the weakest per-class metrics. KNOWN WEAKNESSES: "
        "consumer-vs-b2b confusion is the dominant error mode (see ml/DATASETS.md 'Error "
        "analysis'); calibration is imperfect (see ECE below) though empirically underconfident "
        "rather than overconfident, which is the safer failure direction for a system that "
        "surfaces uncertainty rather than hiding it. NOT SUITABLE for: non-YC-style company "
        "descriptions, non-English input, or presenting predictions as certain fact — callers "
        "must surface `is_uncertain`/abstention fields."
    )

    metadata = {
        "model_name": MODEL_NAME,
        "version": MODEL_VERSION,
        "taxonomy_version": TAXONOMY_VERSION if using_real_dataset else "v1-bootstrap",
        "selected_pipeline": best_name,
        "is_embedding_model": is_embedding_winner,
        "embedding_model_name": EMBEDDING_MODEL_NAME if is_embedding_winner else None,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_command": "python -m ml.src.training.train_industry_classifier",
        "seed": SEED,
        "labels": labels,
        "label_schema": {"n_classes": len(labels), "classes": labels},
        "feature_schema": {
            "input": "single text string = build_text_feature(name, description)",
            "representation": (
                f"frozen sentence-transformer embeddings ({EMBEDDING_MODEL_NAME}, 384-dim)"
                if is_embedding_winner
                else "TF-IDF (see selected_pipeline for word/char/combined configuration)"
            ),
        },
        "n_train": len(X_train),
        "n_test": len(X_test),
        "n_gold_excluded_from_training": n_gold_excluded,
        "using_real_dataset": using_real_dataset,
        "dataset_provenance": dataset_provenance,
        "dataset_fingerprint_sha256": _dataset_fingerprint(REAL_DATASET_PATH),
        "library_versions": _library_versions(),
        "distilbert_finetuning": distilbert_note,
        "cv_results": cv_results,
        "test_metrics": test_metrics,
        "test_top2_accuracy": test_top2_accuracy,
        "calibration": calibration,
        "calibration_comparison_ece": calibration_comparison,
        "abstention": {
            "thresholds_explored": ABSTENTION_THRESHOLDS,
            "recommended_default_threshold": RECOMMENDED_ABSTENTION_THRESHOLD,
            "test_set": test_abstention,
        },
        "gold_set_evaluation": gold_block,
        "inference_latency_ms_per_prediction": inference_latency_ms,
        "model_card": model_card,
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
