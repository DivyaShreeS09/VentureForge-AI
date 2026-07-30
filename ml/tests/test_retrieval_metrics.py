"""Master Startup Corpus Expansion Sprint, Phase 5: unit tests for the generic retrieval-metric
formulas (ml/src/evaluation/retrieval_metrics.py) — standard textbook definitions only.
"""

from __future__ import annotations

from ml.src.evaluation.retrieval_metrics import ndcg_at_k, precision_at_k, reciprocal_rank, recall_at_k


def test_precision_at_k_counts_relevant_fraction():
    assert precision_at_k([True, True, False, False], 4) == 0.5
    assert precision_at_k([True, True, False], 2) == 1.0


def test_precision_at_k_empty_list_is_zero():
    assert precision_at_k([], 5) == 0.0


def test_recall_at_k_divides_by_total_relevant():
    assert recall_at_k([True, False, True], 3, total_relevant=4) == 0.5


def test_recall_at_k_zero_total_relevant_is_zero_not_a_crash():
    assert recall_at_k([False, False], 2, total_relevant=0) == 0.0


def test_reciprocal_rank_finds_first_relevant():
    assert reciprocal_rank([False, False, True]) == 1 / 3
    assert reciprocal_rank([True, False]) == 1.0


def test_reciprocal_rank_no_relevant_is_zero():
    assert reciprocal_rank([False, False, False]) == 0.0


def test_ndcg_at_k_perfect_ranking_is_one():
    assert ndcg_at_k([True, True, False], 3) == 1.0


def test_ndcg_at_k_worse_ranking_scores_lower_than_perfect():
    perfect = ndcg_at_k([True, True, False, False], 4)
    worse = ndcg_at_k([False, True, True, False], 4)
    assert worse < perfect


def test_ndcg_at_k_no_relevant_is_zero():
    assert ndcg_at_k([False, False, False], 3) == 0.0
