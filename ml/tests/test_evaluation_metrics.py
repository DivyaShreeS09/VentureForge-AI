"""Tests for the top-2 accuracy and abstention-report helpers added to
ml/src/evaluation/classification_metrics.py.
"""

from __future__ import annotations

import numpy as np

from ml.src.evaluation.classification_metrics import abstention_report, top2_accuracy

CLASSES = ["a", "b", "c"]


def test_top2_accuracy_counts_true_label_in_top_two():
    y_true = ["a", "b", "c"]
    # Row 0: true='a', proba ranks b>a>c -> a is 2nd -> counts.
    # Row 1: true='b', proba ranks b highest -> counts.
    # Row 2: true='c', proba ranks a>b>c -> c is last, NOT top-2 -> does not count.
    y_proba = np.array(
        [
            [0.4, 0.5, 0.1],
            [0.1, 0.8, 0.1],
            [0.5, 0.4, 0.1],
        ]
    )
    acc = top2_accuracy(y_true, y_proba, CLASSES)
    assert acc == 2 / 3


def test_top2_accuracy_perfect_when_top1_always_correct():
    y_true = ["a", "b", "c"]
    y_proba = np.array(
        [
            [0.9, 0.05, 0.05],
            [0.05, 0.9, 0.05],
            [0.05, 0.05, 0.9],
        ]
    )
    assert top2_accuracy(y_true, y_proba, CLASSES) == 1.0


def test_top2_accuracy_empty_input_returns_zero():
    assert top2_accuracy([], np.zeros((0, 3)), CLASSES) == 0.0


def test_abstention_report_higher_threshold_lowers_coverage():
    y_true = ["a", "a", "b", "b"]
    y_pred = ["a", "a", "b", "a"]  # last prediction wrong
    y_proba = np.array(
        [
            [0.9, 0.05, 0.05],
            [0.55, 0.3, 0.15],
            [0.1, 0.1, 0.8],
            [0.45, 0.4, 0.15],
        ]
    )
    report = abstention_report(y_true, y_pred, y_proba, thresholds=[0.4, 0.6, 0.85])

    by_threshold = {r["threshold"]: r for r in report}
    # Coverage must be non-increasing as the threshold rises.
    assert by_threshold[0.4]["coverage"] >= by_threshold[0.6]["coverage"] >= by_threshold[0.85]["coverage"]
    # At threshold 0.85, only the first row (0.9 confidence) is covered, and it's correct.
    assert by_threshold[0.85]["n_covered"] == 1
    assert by_threshold[0.85]["accuracy_on_covered"] == 1.0


def test_abstention_report_no_covered_rows_reports_none_accuracy():
    y_true = ["a"]
    y_pred = ["a"]
    y_proba = np.array([[0.5, 0.3, 0.2]])
    report = abstention_report(y_true, y_pred, y_proba, thresholds=[0.99])
    assert report[0]["n_covered"] == 0
    assert report[0]["accuracy_on_covered"] is None
    assert report[0]["coverage"] == 0.0
