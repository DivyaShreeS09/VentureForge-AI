"""Tests for the v2 additions to ml/src/evaluation/binary_classification_metrics.py:
threshold_sweep, recommend_threshold, subgroup_roc_auc.
"""

from __future__ import annotations

import numpy as np

from ml.src.evaluation.binary_classification_metrics import (
    recommend_threshold,
    subgroup_roc_auc,
    threshold_sweep,
)


def test_threshold_sweep_includes_default_and_bounds():
    y_true = [0, 0, 1, 1, 1, 0, 1, 0]
    y_proba = [0.1, 0.4, 0.9, 0.8, 0.6, 0.3, 0.7, 0.2]
    sweep = threshold_sweep(y_true, y_proba)
    thresholds = [row["threshold"] for row in sweep]
    assert 0.5 in thresholds
    for row in sweep:
        assert 0.0 <= row["precision"] <= 1.0
        assert 0.0 <= row["recall"] <= 1.0
        assert 0.0 <= row["f1"] <= 1.0
        assert 0.0 <= row["accuracy"] <= 1.0


def test_threshold_sweep_higher_threshold_never_increases_recall():
    y_true = [0, 0, 1, 1, 1, 0, 1, 0]
    y_proba = [0.1, 0.4, 0.9, 0.8, 0.6, 0.3, 0.7, 0.2]
    sweep = sorted(threshold_sweep(y_true, y_proba), key=lambda r: r["threshold"])
    recalls = [row["recall"] for row in sweep]
    assert all(recalls[i] >= recalls[i + 1] for i in range(len(recalls) - 1))


def test_recommend_threshold_picks_max_f1():
    sweep = [
        {"threshold": 0.3, "precision": 0.5, "recall": 0.9, "f1": 0.64, "accuracy": 0.6},
        {"threshold": 0.5, "precision": 0.8, "recall": 0.8, "f1": 0.80, "accuracy": 0.8},
        {"threshold": 0.7, "precision": 0.9, "recall": 0.5, "f1": 0.64, "accuracy": 0.7},
    ]
    best = recommend_threshold(sweep, objective="f1")
    assert best["threshold"] == 0.5


def test_recommend_threshold_ties_broken_toward_default():
    sweep = [
        {"threshold": 0.3, "precision": 0.5, "recall": 0.9, "f1": 0.70, "accuracy": 0.6},
        {"threshold": 0.5, "precision": 0.8, "recall": 0.8, "f1": 0.70, "accuracy": 0.8},
        {"threshold": 0.9, "precision": 0.9, "recall": 0.5, "f1": 0.70, "accuracy": 0.7},
    ]
    best = recommend_threshold(sweep, objective="f1")
    assert best["threshold"] == 0.5  # closest to 0.5 among the tied-F1 candidates


def test_subgroup_roc_auc_reports_top_n_groups_only():
    rng = np.random.default_rng(0)
    n = 200
    groups = ["usa"] * 100 + ["gbr"] * 60 + ["ind"] * 30 + ["rare"] * 10
    y_true = rng.integers(0, 2, size=n).tolist()
    y_proba = rng.random(n).tolist()
    result = subgroup_roc_auc(y_true, y_proba, groups, top_n=3, min_group_size=5)
    reported_groups = {r["group"] for r in result}
    assert reported_groups == {"usa", "gbr", "ind"}
    assert "rare" not in reported_groups


def test_subgroup_roc_auc_flags_small_or_single_class_groups():
    y_true = [1, 1, 1, 1, 1]  # only one class present
    y_proba = [0.9, 0.8, 0.7, 0.6, 0.5]
    groups = ["usa"] * 5
    result = subgroup_roc_auc(y_true, y_proba, groups, top_n=1, min_group_size=3)
    assert result[0]["roc_auc"] is None
    assert "reason" in result[0]
