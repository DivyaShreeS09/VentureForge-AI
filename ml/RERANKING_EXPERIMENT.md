# Phase 2 — Cross-Encoder Reranking Experiment (Final ML Excellence Sprint)

## What was evaluated

A second-stage reranker: cosine similarity (existing, unchanged) retrieves a 20-candidate pool,
then `cross-encoder/ms-marco-MiniLM-L-6-v2` (~90MB, pretrained, CPU, no fine-tuning, no online API)
rescores each (query, candidate) pair directly. Evaluated on a fixed 80-query random sample (seed
42) from the production retrieval corpus — a full-corpus run (~7,173 queries × 20 candidates ≈
143,000 forward passes) was computationally infeasible to run repeatedly on this project's
memory-constrained CPU-only development machine; a sample is disclosed as a sample, not presented
as a full-population number. Script: `ml/src/evaluation/experiment_cross_encoder_rerank.py`.

## Result (same 80-query sample, same 20-candidate pool, both methods)

| Metric | Cosine-only (baseline) | Cross-encoder reranked |
|---|---|---|
| Precision@1 | **0.850** | 0.825 |
| Precision@3 | 0.783 | **0.800** |
| Precision@5 | 0.770 | **0.780** |
| MRR | **0.896** | 0.882 |
| NDCG@5 | 0.896 | **0.898** |
| Coverage | 96.25% | 96.25% |

**Mixed result, not a clear win**: precision@1 and MRR both got *worse*; precision@3/5 and NDCG
improved marginally (all well within noise range for an 80-query sample).

**Latency**: 2,938ms average added latency per query (20 cross-encoder forward passes each,
plus an 8.55s one-time model load) — versus the existing cosine lookup's ~0.2ms per query. This is
a **~15,000x latency increase**, completely incompatible with a synchronous analysis request.

## Decision criteria (this sprint's own rule)

> Deploy ONLY if every deployment criterion is satisfied. Otherwise reject.

## Result: **REJECTED — not deployed**

Fails on two independent grounds: (1) no consistent precision/ranking improvement — some metrics
improved marginally, others got worse, netting out to noise; (2) latency is disqualifying on its
own regardless of accuracy — adding ~3 seconds to every retrieval call is not a viable trade for a
founder-facing report generation flow. The existing single-stage cosine retrieval (optionally
boosted by the already-frozen industry classifier's own prediction — see the Master Startup Corpus
Expansion Sprint's Phase 6 industry-aware reranking, already in production) remains the retrieval
architecture. No new model, no new dependency, was added to production as a result of this
experiment.
