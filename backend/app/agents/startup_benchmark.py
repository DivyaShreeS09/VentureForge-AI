"""Startup Benchmark Engine (Startup Domain Intelligence Sprint, Phase 3).

Answers "compared to what?" for every recommendation — reusing, not duplicating, two existing
engines: app.ml.venture_retrieval (real retrieved similar ventures + its own
build_comparative_intelligence) and app.agents.industry_knowledge_packs (general startup-domain
knowledge). No new embedding, no new retrieval, no new classifier.

Honest finding this module makes explicit rather than glossing over: the retrieval corpus (name +
description + industry label only — see app.ml.venture_retrieval's own UNSUPPORTED_DIMENSIONS)
cannot support benchmarking on pricing, customer-acquisition motion, pilot strategy, common
mistakes, typical first customer, or growth path — none of that data exists in the dataset. Only
industry positioning and shared terminology are genuinely retrieval-backed. Every field below is
therefore explicitly tagged `source: "retrieved_evidence"` or `source: "general_startup_knowledge"`
— never silently presented as if retrieval evidence supports something it structurally cannot.
"""

from __future__ import annotations

STARTUP_BENCHMARK_VERSION = "v1"


def build_startup_benchmark(venture_retrieval: dict | None, knowledge_pack: dict) -> dict:
    """`venture_retrieval` is app.ml.venture_retrieval.retrieve_similar_ventures's already-computed
    output (never re-queried here); `knowledge_pack` is
    app.agents.industry_knowledge_packs.get_industry_knowledge_pack's already-computed output."""
    venture_retrieval = venture_retrieval or {}
    comparative = venture_retrieval.get("comparative_intelligence") or {}
    neighbors = venture_retrieval.get("neighbors") or []
    retrieval_available = bool(venture_retrieval.get("available"))

    industry_positioning = None
    if retrieval_available and comparative.get("available"):
        positioning = comparative.get("common_industry_positioning") or {}
        if positioning.get("available"):
            industry_positioning = {
                "pattern": positioning["support"],
                "source": "retrieved_evidence",
                "citations": positioning.get("citations", []),
            }

    def _general(value_key: str, source_field: str) -> dict:
        return {"pattern": knowledge_pack[source_field], "source": "general_startup_knowledge", "citations": []}

    return {
        "startup_benchmark_version": STARTUP_BENCHMARK_VERSION,
        "retrieved_ventures_available": retrieval_available and bool(neighbors),
        "retrieved_ventures_used": [
            {"name": n["name"], "industry": n["industry"], "similarity": n["similarity"]} for n in neighbors
        ],
        "industry_positioning_pattern": industry_positioning,
        # Every field below is honestly general-knowledge-sourced, not retrieval-backed — the
        # retrieval corpus has no pricing/GTM/outcome data (see module docstring). Disclosed
        # explicitly per-field rather than silently implying retrieval support.
        "pricing_approach": _general("pricing_approach", "common_pricing_approaches"),
        "customer_acquisition_pattern": _general("customer_acquisition_pattern", "buying_process"),
        "typical_pilot_strategy": _general("typical_pilot_strategy", "pilot_strategy"),
        "common_mistakes": _general("common_mistakes", "common_failure_reasons"),
        # Was previously duplicating "pilot_strategy" verbatim (a founder would read the identical
        # sentence twice in the same section) — "typical_customer" is who the first customer is,
        # a genuinely distinct field from the pilot's strategy/mechanics.
        "typical_first_customer": _general("typical_first_customer", "typical_customer"),
        "growth_path": _general("growth_path", "expansion_path"),
        "disclaimer": (
            "Industry positioning above is retrieved from real, similar ventures in this project's "
            "dataset. Every other field here is general startup-domain knowledge for this venture's "
            "category — the retrieval dataset (name, description, and industry label only) has no "
            "pricing, customer-acquisition, or outcome data to benchmark against, so those fields "
            "are explicitly NOT presented as retrieval evidence."
        ),
    }
