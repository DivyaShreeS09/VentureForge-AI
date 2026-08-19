"""Founder-facing stage labels for the orchestrator's real node ids — used only to give The
Forging (Act IV) an honest, calm human-readable label for `current_stage`, never to invent new
orchestration. Every node id `app/agents/orchestrator.py` registers must appear here exactly once
so no real work silently goes unlabeled; grouped into founder-meaningful phases (rather than 23
raw technical node names) purely for presentation.
"""

from __future__ import annotations

STAGE_LABELS: dict[str, str] = {
    "input_validation": "Reading Your Idea",
    "invalid_input": "Reading Your Idea",
    "industry_classification": "Understanding Your Industry",
    "resolve_venture_positioning": "Understanding Your Industry",
    "funding_readiness": "Scoring Your Readiness",
    "predict_success": "Comparing Historical Patterns",
    "estimate_revenue": "Modeling Your Revenue",
    "analyze_market": "Studying Your Market",
    "analyze_competitors": "Studying Your Market",
    "build_customer_persona": "Studying Your Market",
    "evaluate_business_model": "Studying Your Market",
    "segment_customers": "Mapping Your Growth Strategy",
    "rank_actions": "Mapping Your Growth Strategy",
    "surface_innovation": "Mapping Your Growth Strategy",
    "assess_risks": "Mapping Your Growth Strategy",
    "plan_growth_strategy": "Mapping Your Growth Strategy",
    "build_pitch_deck": "Mapping Your Growth Strategy",
    "evidence_confidence_check": "Checking Your Evidence",
    "judge": "Preparing Your Mentor Report",
    "mentor_synthesis": "Preparing Your Mentor Report",
    "expand_ideas": "Preparing Your Mentor Report",
    "discover_strategic_opportunities": "Preparing Your Mentor Report",
    "synthesize_decision": "Preparing Your Mentor Report",
    "reason_causally": "Preparing Your Mentor Report",
    "simulate_counterfactuals": "Preparing Your Mentor Report",
    "persistence": "Preparing Your Mentor Report",
    "final_response": "Preparing Your Mentor Report",
}

# Founder-facing display order — every value in STAGE_LABELS appears here exactly once, in the
# order a healthy run reaches it. The frontend uses this same ordering (kept in sync by name, not
# by re-deriving it from raw node ids) to render "done / current / upcoming" without needing to
# know a single orchestrator node id.
STAGE_ORDER: list[str] = [
    "Reading Your Idea",
    "Understanding Your Industry",
    "Scoring Your Readiness",
    "Comparing Historical Patterns",
    "Modeling Your Revenue",
    "Studying Your Market",
    "Mapping Your Growth Strategy",
    "Checking Your Evidence",
    "Preparing Your Mentor Report",
]


def stage_label_for(node: str) -> str:
    """Falls back to the raw node id for anything unmapped — never silently drops a real node,
    even if a future orchestrator change adds one before this file is updated."""
    return STAGE_LABELS.get(node, node)
