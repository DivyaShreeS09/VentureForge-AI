"""Shared evaluation helpers for text classification models."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
)


def evaluate_classification(
    y_true: list[str],
    y_pred: list[str],
    labels: list[str],
    y_proba: np.ndarray | None = None,
) -> dict:
    """Compute the metric set required before a classifier can be trusted.

    Returns accuracy, balanced accuracy, macro/weighted precision-recall-F1, per-class support,
    the confusion matrix, and log loss (only when probabilities are supplied).
    """
    report = classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0)

    metrics: dict = {
        "accuracy": accuracy_score(y_true, y_pred),
        "balanced_accuracy": balanced_accuracy_score(y_true, y_pred),
        "macro_precision": precision_score(y_true, y_pred, average="macro", zero_division=0),
        "macro_recall": recall_score(y_true, y_pred, average="macro", zero_division=0),
        "macro_f1": f1_score(y_true, y_pred, average="macro", zero_division=0),
        "weighted_f1": f1_score(y_true, y_pred, average="weighted", zero_division=0),
        "per_class": {
            label: {
                "precision": report[label]["precision"],
                "recall": report[label]["recall"],
                "f1": report[label]["f1-score"],
                "support": report[label]["support"],
            }
            for label in labels
        },
        "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
        "confusion_matrix_labels": labels,
    }

    if y_proba is not None:
        try:
            metrics["log_loss"] = log_loss(y_true, y_proba, labels=labels)
        except ValueError as exc:
            metrics["log_loss"] = None
            metrics["log_loss_error"] = str(exc)

    return metrics


def top2_accuracy(y_true: list[str], y_proba: np.ndarray, classes: list[str]) -> float:
    """Fraction of examples where the true label is among the top-2 highest-probability classes.

    A softer, still-honest notion of "the model was in the right neighborhood" — useful for a
    7-class, imbalanced problem where forcing a single top-1 answer discards real partial signal
    (e.g. b2b vs. fintech ambiguity where the model correctly narrows to 2 plausible classes).
    """
    class_index = {c: i for i, c in enumerate(classes)}
    proba = np.asarray(y_proba)
    top2_idx = np.argsort(proba, axis=1)[:, -2:]
    hits = 0
    for i, true_label in enumerate(y_true):
        true_idx = class_index.get(true_label)
        if true_idx is not None and true_idx in top2_idx[i]:
            hits += 1
    return hits / len(y_true) if y_true else 0.0


def abstention_report(
    y_true: list[str],
    y_pred: list[str],
    y_proba: np.ndarray,
    thresholds: list[float],
) -> list[dict]:
    """For each confidence threshold, report coverage (share of predictions whose top-1
    probability clears the threshold) and accuracy computed only on that covered subset.

    This is the standard coverage/accuracy trade-off table for a confidence-threshold abstention
    layer: a higher threshold keeps fewer predictions (lower coverage) but the ones it does keep
    should be more reliable (higher accuracy-on-covered). Reported for every threshold requested,
    not just the eventually-recommended one, so the trade-off is visible.
    """
    top1_confidence = np.asarray(y_proba).max(axis=1)
    y_true_arr = np.asarray(y_true)
    y_pred_arr = np.asarray(y_pred)
    n = len(y_true_arr)

    report = []
    for threshold in thresholds:
        keep = top1_confidence >= threshold
        coverage = float(keep.sum()) / n if n else 0.0
        if keep.sum() > 0:
            accuracy_on_covered = float((y_true_arr[keep] == y_pred_arr[keep]).mean())
        else:
            accuracy_on_covered = None
        report.append(
            {
                "threshold": threshold,
                "coverage": coverage,
                "n_covered": int(keep.sum()),
                "accuracy_on_covered": accuracy_on_covered,
            }
        )
    return report


def check_no_leakage(train_texts: list[str], test_texts: list[str]) -> list[str]:
    """Return any text that appears in both the train and test splits (exact-match leakage)."""
    overlap = set(train_texts) & set(test_texts)
    return sorted(overlap)


def expected_calibration_error(
    correct: list[bool], confidences: list[float], n_bins: int = 10
) -> dict:
    """Bin top-1 predictions by confidence and compare each bin's average confidence to its
    actual accuracy. A well-calibrated model has near-zero gaps in every bin; ECE is the
    support-weighted average gap. This is a real, standard calibration diagnostic — not a
    stand-in for accuracy, and it is reported even when it makes the selected model look worse.
    """
    confidences_arr = np.asarray(confidences, dtype=float)
    correct_arr = np.asarray(correct, dtype=bool)
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)

    bins = []
    ece = 0.0
    n = len(confidences_arr)
    for i in range(n_bins):
        lo, hi = bin_edges[i], bin_edges[i + 1]
        in_bin = (confidences_arr > lo) & (confidences_arr <= hi) if i > 0 else (
            (confidences_arr >= lo) & (confidences_arr <= hi)
        )
        count = int(in_bin.sum())
        if count == 0:
            continue
        avg_confidence = float(confidences_arr[in_bin].mean())
        avg_accuracy = float(correct_arr[in_bin].mean())
        gap = abs(avg_confidence - avg_accuracy)
        ece += (count / n) * gap
        bins.append(
            {
                "range": [round(lo, 2), round(hi, 2)],
                "count": count,
                "avg_confidence": avg_confidence,
                "avg_accuracy": avg_accuracy,
                "gap": gap,
            }
        )

    return {"expected_calibration_error": ece, "bins": bins}
