"""Master Startup Corpus Expansion Sprint, Phase 5 — generic, reusable retrieval-quality metrics.

Standard, textbook formulas only (no invented metric) — Precision@k, Recall@k, MRR, NDCG@k —
parameterized over a boolean relevance function, so the same functions serve leave-one-out
same-industry evaluation here and could serve a differently-defined relevance judgment later
without rewriting the metric math.
"""

from __future__ import annotations

import math


def precision_at_k(relevance: list[bool], k: int) -> float:
    top_k = relevance[:k]
    return sum(top_k) / len(top_k) if top_k else 0.0


def recall_at_k(relevance: list[bool], k: int, total_relevant: int) -> float:
    if total_relevant == 0:
        return 0.0
    return sum(relevance[:k]) / total_relevant


def reciprocal_rank(relevance: list[bool]) -> float:
    for i, is_relevant in enumerate(relevance):
        if is_relevant:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(relevance: list[bool], k: int) -> float:
    """Binary-relevance NDCG@k (graded relevance 1/0 — same-industry match or not)."""
    top_k = relevance[:k]
    dcg = sum((1.0 if rel else 0.0) / math.log2(i + 2) for i, rel in enumerate(top_k))
    ideal_relevant = min(sum(relevance), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_relevant))
    return dcg / idcg if idcg > 0 else 0.0
