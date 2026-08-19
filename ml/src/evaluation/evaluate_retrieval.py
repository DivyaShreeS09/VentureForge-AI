"""Master Startup Corpus Expansion Sprint, Phase 5 — retrieval evaluation.

Honest methodology, stated up front: this project has no human relevance judgments for "is
company X actually similar to company Y" (building one would require fabricating labels this
project's own rules forbid). The best available, non-fabricated proxy is LEAVE-ONE-OUT SAME-
INDUSTRY AGREEMENT: for every company in the corpus, treat it as a query (excluding itself from
its own candidate pool) and check whether the neighbors this project's own real cosine-similarity
retrieval surfaces share its already-real, human-assigned industry label. This measures "does
retrieval surface industry-coherent neighbors," not "does retrieval find this founder's true
competitors" — a real, useful, and honestly-scoped signal, not an inflated claim.

Restricted to the 7-class controlled YC industry taxonomy shared by both v1 and v2 (v2 additionally
carries ~170 free-text single-source category labels from the joebeachcapital source that have no
v1 counterpart and too little per-label support for a meaningful precision/recall number — excluded
from this specific comparison, not silently mixed in).

Run: `python -m ml.src.evaluation.evaluate_retrieval --version v1`
     `python -m ml.src.evaluation.evaluate_retrieval --version v2`
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

from ml.src.evaluation.retrieval_metrics import ndcg_at_k, precision_at_k, reciprocal_rank, recall_at_k

REPO_ROOT = Path(__file__).resolve().parents[3]
MODELS_DIR = REPO_ROOT / "ml" / "models" / "venture_retrieval"

# Final ML Excellence Sprint, Phase 8 (duplicate-constant cleanup): reuse the SAME reranking-boost
# constant app.ml.venture_retrieval actually deploys, rather than a second hand-copied literal that
# could silently drift out of sync with production.
_BACKEND_DIR = REPO_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
from app.ml.venture_retrieval import _INDUSTRY_RERANK_BOOST  # noqa: E402

_CONTROLLED_TAXONOMY = {
    "b2b", "consumer", "healthcare", "fintech", "industrials",
    "real estate and construction", "education",
}
K_VALUES = (1, 3, 5)


def _load(version: str) -> tuple[np.ndarray, list[dict]]:
    version_dir = MODELS_DIR / version
    embeddings = np.load(version_dir / "corpus_embeddings.npy").astype(np.float64)
    metadata = json.loads((version_dir / "corpus_metadata.json").read_text(encoding="utf-8"))
    return embeddings, metadata["records"]


def evaluate(version: str, max_k: int = 5, apply_rerank: bool = False) -> dict:
    embeddings, records = _load(version)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1e-12
    normalized = embeddings / norms

    eligible_idx = [i for i, r in enumerate(records) if r.get("industry") in _CONTROLLED_TAXONOMY]
    industries = np.array([records[i]["industry"] for i in range(len(records))])

    t0 = time.perf_counter()
    similarity_matrix = normalized @ normalized.T
    build_time = time.perf_counter() - t0

    precisions = {k: [] for k in K_VALUES}
    recalls_at_5 = []
    reciprocal_ranks = []
    ndcgs_at_5 = []
    failure_cases: list[dict] = []
    per_query_latencies = []

    for qi in eligible_idx:
        t0 = time.perf_counter()
        sims = similarity_matrix[qi].copy()
        sims[qi] = -np.inf  # exclude self (leave-one-out)
        if apply_rerank:
            # Simulates app.ml.venture_retrieval's Phase 6 industry-aware reranking using the
            # query's OWN real, already-known label as the "classifier prediction" -- an
            # upper-bound measurement of the boost's effect assuming a correct classifier call,
            # isolated from corpus-size effects (both use the SAME corpus/version here).
            ranking = sims + np.where(industries == records[qi]["industry"], _INDUSTRY_RERANK_BOOST, 0.0)
        else:
            ranking = sims
        top_idx = np.argsort(-ranking)[:max_k]
        per_query_latencies.append(time.perf_counter() - t0)

        query_industry = records[qi]["industry"]
        relevance = [industries[j] == query_industry for j in top_idx]
        total_relevant = int((industries == query_industry).sum()) - 1  # minus the query itself

        for k in K_VALUES:
            precisions[k].append(precision_at_k(relevance, k))
        recalls_at_5.append(recall_at_k(relevance, 5, total_relevant))
        reciprocal_ranks.append(reciprocal_rank(relevance))
        ndcgs_at_5.append(ndcg_at_k(relevance, 5))
        if not any(relevance):
            failure_cases.append({
                "query_name": records[qi]["name"],
                "query_industry": query_industry,
                "top_neighbor_industries": [records[j]["industry"] for j in top_idx],
            })

    n_queries = len(eligible_idx)
    return {
        "evaluated_version": version,
        "n_queries": n_queries,
        "n_total_records": len(records),
        "method": (
            "Leave-one-out same-industry agreement over the controlled 7-class YC taxonomy subset "
            "shared by both corpus versions -- a proxy for 'does retrieval surface "
            "industry-coherent neighbors', not a claim of verified real-world competitor relevance "
            "(no such ground truth exists or was fabricated)."
        ),
        "precision_at_k": {f"precision@{k}": round(sum(v) / n_queries, 4) if n_queries else 0.0 for k, v in precisions.items()},
        "recall_at_5": round(sum(recalls_at_5) / n_queries, 4) if n_queries else 0.0,
        "mrr": round(sum(reciprocal_ranks) / n_queries, 4) if n_queries else 0.0,
        "ndcg_at_5": round(sum(ndcgs_at_5) / n_queries, 4) if n_queries else 0.0,
        "coverage_pct": round(sum(1 for r in reciprocal_ranks if r > 0) / n_queries * 100, 2) if n_queries else 0.0,
        "n_failure_cases": len(failure_cases),
        "failure_case_rate_pct": round(len(failure_cases) / n_queries * 100, 2) if n_queries else 0.0,
        "sample_failure_cases": failure_cases[:5],
        "latency_ms": {
            "similarity_matrix_build_total_ms": round(build_time * 1000, 2),
            "avg_per_query_lookup_ms": round(sum(per_query_latencies) / len(per_query_latencies) * 1000, 4) if per_query_latencies else 0.0,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="v1")
    parser.add_argument("--rerank", action="store_true")
    args = parser.parse_args()
    print(json.dumps(evaluate(args.version, apply_rerank=args.rerank), indent=2))


if __name__ == "__main__":
    main()
