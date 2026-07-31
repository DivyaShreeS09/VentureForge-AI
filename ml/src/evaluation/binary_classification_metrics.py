"""Shared evaluation helpers for binary classification models (startup success prediction)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    cohen_kappa_score,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)


def evaluate_binary_classification(
    y_true: list[int],
    y_pred: list[int],
    y_proba: np.ndarray | None = None,
) -> dict:
    """Compute the metric set required before a binary classifier can be trusted.

    ROC-AUC and PR-AUC (average precision) are computed whenever probabilities are supplied and
    both classes are present in y_true; Brier score measures probability calibration directly.
    """
    metrics: dict = {
        "accuracy": accuracy_score(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=[0, 1]).tolist(),
        "confusion_matrix_labels": [0, 1],
        # Chance-corrected agreement metrics — unlike accuracy, both are 0 for a chance-level
        # classifier regardless of class balance, so they're a useful cross-check alongside F1.
        "mcc": float(matthews_corrcoef(y_true, y_pred)),
        "cohen_kappa": float(cohen_kappa_score(y_true, y_pred)),
    }

    if y_proba is not None and len(set(y_true)) == 2:
        metrics["roc_auc"] = float(roc_auc_score(y_true, y_proba))
        metrics["pr_auc"] = float(average_precision_score(y_true, y_proba))
        metrics["brier_score"] = float(brier_score_loss(y_true, y_proba))
    else:
        metrics["roc_auc"] = None
        metrics["pr_auc"] = None
        metrics["brier_score"] = None

    return metrics


def check_no_leakage(train_ids: list[str], test_ids: list[str]) -> list[str]:
    """Return any identifier that appears in both the train and test splits."""
    overlap = set(train_ids) & set(test_ids)
    return sorted(overlap)


def threshold_sweep(y_true: list[int], y_proba: np.ndarray, thresholds: np.ndarray | None = None) -> list[dict]:
    """Precision/recall/F1 at each candidate probability cutoff, for choosing an operating
    threshold other than the default 0.5. Always includes 0.5 itself as a reference point."""
    y_true_arr = np.asarray(y_true)
    y_proba_arr = np.asarray(y_proba)
    if thresholds is None:
        thresholds = np.round(np.arange(0.05, 1.0, 0.05), 2)
    if 0.5 not in thresholds:
        thresholds = np.sort(np.append(thresholds, 0.5))

    rows = []
    for t in thresholds:
        y_pred = (y_proba_arr >= t).astype(int)
        rows.append(
            {
                "threshold": float(t),
                "precision": float(precision_score(y_true_arr, y_pred, zero_division=0)),
                "recall": float(recall_score(y_true_arr, y_pred, zero_division=0)),
                "f1": float(f1_score(y_true_arr, y_pred, zero_division=0)),
                "accuracy": float(accuracy_score(y_true_arr, y_pred)),
            }
        )
    return rows


def recommend_threshold(sweep: list[dict], objective: str = "f1") -> dict:
    """Pick the operating threshold that maximizes `objective` ("f1" by default) from a
    `threshold_sweep` table. Ties broken by preferring the threshold closest to 0.5 (the least
    arbitrary tie-break, rather than an unstated preference for higher/lower recall)."""
    best = max(sweep, key=lambda row: (row[objective], -abs(row["threshold"] - 0.5)))
    return best


def subgroup_roc_auc(
    y_true: list[int],
    y_proba: np.ndarray,
    groups: list[str],
    top_n: int = 3,
    min_group_size: int = 30,
) -> list[dict]:
    """ROC-AUC broken out by the `top_n` most frequent values of a grouping column (e.g.
    primary_category, country_code), to check for differential performance across subgroups.
    Groups smaller than `min_group_size` or with only one class present are reported with
    `roc_auc: None` and a reason, rather than a misleadingly noisy single-fold AUC."""
    y_true_arr = np.asarray(y_true)
    y_proba_arr = np.asarray(y_proba)
    groups_arr = np.asarray(groups, dtype=str)

    counts = pd.Series(groups_arr).value_counts()
    top_groups = counts.head(top_n).index.tolist()

    results = []
    for group in top_groups:
        mask = groups_arr == group
        n = int(mask.sum())
        y_g = y_true_arr[mask]
        if n < min_group_size:
            results.append({"group": group, "n": n, "roc_auc": None, "reason": "group smaller than min_group_size"})
            continue
        if len(set(y_g.tolist())) < 2:
            results.append({"group": group, "n": n, "roc_auc": None, "reason": "only one class present in group"})
            continue
        results.append({"group": group, "n": n, "roc_auc": float(roc_auc_score(y_g, y_proba_arr[mask]))})
    return results
