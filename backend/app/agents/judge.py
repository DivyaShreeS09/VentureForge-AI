"""Judge Agent: deterministic synthesis of the industry, funding-readiness, and venture-
positioning outputs.

This never calls an external LLM and never invents facts. It only reformats and reconciles what
the industry classifier (a model prediction), the funding-readiness rubric (a deterministic score
derived from user-provided answers), and the venture-positioning resolution (see
app.agents.venture_positioning.resolve_venture_positioning — the sole final authority for
`venture_positioning`, computed upstream in app.agents.nodes.venture_positioning_node) already
produced. An optional narrative enhancement (Gemini, via backend/app/ai/) is layered on top by the
orchestrator after this function returns — see app/agents/orchestrator.py's `_try_llm_narrative` —
never inside this module, so `synthesize` itself has no network dependency and its output is
identical whether or not an LLM is configured.
"""

from __future__ import annotations

from app.agents.founder_guidance import build_founder_guidance_items
from app.agents.hypothesis_engine import build_hypotheses_for_gaps

_ACTION_BY_DIMENSION: dict[str, str] = {
    "problem_clarity": "Write a one-sentence problem statement naming who has the problem and what it costs them.",
    "customer_pain_evidence": "Collect at least 5 customer interviews or a survey documenting the pain point.",
    "market_size_evidence": "Produce a sourced TAM/SAM/SOM estimate rather than an unsupported figure.",
    "product_maturity": "Ship a working prototype or MVP that a real user can try.",
    "traction": "Recruit pilot users or early customers and track usage/retention.",
    "revenue_model_clarity": "Define pricing and unit economics (CAC, margin, expected LTV).",
    "team_completeness": "Identify or recruit a co-founder/hire covering the missing core skill.",
    "competitive_differentiation": "Document how the offering differs from the 2-3 closest alternatives.",
}


def _confidence_level(industry_prediction: dict | None, funding_assessment: dict, evidence_check: dict) -> str:
    if evidence_check.get("low_confidence"):
        return "low"
    industry_confidence = (industry_prediction or {}).get("confidence", 0.0)
    if funding_assessment.get("level") == "ready" and industry_confidence >= 0.6:
        return "high"
    return "medium"


def synthesize(
    industry_prediction: dict | None,
    funding_assessment: dict,
    evidence_check: dict,
    success_prediction: dict | None = None,
    revenue_estimate: dict | None = None,
    market_intelligence: dict | None = None,
    competitor_analysis: dict | None = None,
    customer_personas: dict | None = None,
    business_model: dict | None = None,
    model_category: dict | None = None,
    venture_positioning: dict | None = None,
    taxonomy_candidates: list[dict] | None = None,
    gemini_structured_recommendation: dict | None = None,
    gemini_rationale: str | None = None,
    positioning_correction_rationale: str | None = None,
    market_evidence: dict | None = None,
    customer_segment: dict | None = None,
    ranked_actions: list[dict] | None = None,
    risks: list[dict] | None = None,
) -> dict:
    """Produce the final Judge summary. Raises ValueError if required fields are missing.

    The Student 2 arguments are optional and additive: each is independently attributed to its
    source (trained ML, deterministic calculation, or user-submitted evidence) in
    `source_attribution` and never averaged or blended with the industry/funding scores — a
    success-prediction probability and a funding-readiness score measure different things and
    combining them into one number would misrepresent both.

    `strengths`/`weaknesses`/`missing_evidence` below are kept for backward compatibility only
    (deprecated, technical-only fields) — see `founder_guidance_items` for the structured,
    coached replacement every new consumer (app.agents.mentor_synthesis, the frontend) must use
    instead. Nothing in this module or downstream parses the raw `weaknesses` strings.
    """
    if funding_assessment is None or "overall_score" not in funding_assessment:
        raise ValueError("funding_assessment is required and must include overall_score")

    breakdown = funding_assessment.get("breakdown", [])
    missing = set(funding_assessment.get("missing_evidence", []))

    # `state` is present on every breakdown item produced by the current
    # app.ml.funding_readiness.assess_funding_readiness. Fall back to the legacy raw_score-only
    # shape (raw_score == 0 and not in `missing` implied confirmed_negative) for any caller that
    # hand-built a funding_assessment fixture without the `state` field.
    def _state(item: dict) -> str | None:
        state = item.get("state")
        if state is not None:
            return state
        if item.get("raw_score") == 2:
            return "confirmed_positive"
        if item.get("raw_score") == 0:
            return "confirmed_negative" if item["dimension"] not in missing else "not_sure_yet"
        return "confirmed_positive"

    strengths = [
        f"{item['label']}: {item['scale_description']}"
        for item in breakdown
        if _state(item) == "confirmed_positive" and item["raw_score"] == 2
    ]
    # Only a `confirmed_negative` — the founder's own affirmed absence of evidence — may ever
    # become a weakness. `not_sure_yet` is never a weakness; it is routed to the Hypothesis Engine
    # below instead.
    weaknesses = [
        f"{item['label']}: {item['scale_description']}"
        for item in breakdown
        if _state(item) == "confirmed_negative"
    ]
    missing_evidence = [
        next(item["label"] for item in breakdown if item["dimension"] == dim) for dim in missing
    ]
    next_actions = [
        _ACTION_BY_DIMENSION[item["dimension"]]
        for item in breakdown
        if _state(item) in ("confirmed_negative", "not_sure_yet") and item["dimension"] in _ACTION_BY_DIMENSION
    ]
    suggested_possibilities = build_hypotheses_for_gaps(sorted(missing))
    founder_guidance_items = build_founder_guidance_items(funding_assessment, market_evidence)

    confidence_level = _confidence_level(industry_prediction, funding_assessment, evidence_check)

    source_attribution: dict[str, str] = {
        "funding_assessment": "deterministic rubric score from user-provided answers",
        "strengths_weaknesses_next_actions": "generated from rubric breakdown via fixed templates",
    }

    if success_prediction is not None:
        source_attribution["success_prediction"] = (
            f"trained ML model ({success_prediction.get('model_pipeline', 'unknown')}, "
            f"version {success_prediction.get('model_version', 'unknown')}) — historical pattern "
            "estimate, not a guarantee"
        )
        # A heavily-imputed or near-chance historical pattern signal must never read as a
        # founder-facing risk (see app.ml.success_predictor's founder-facing band label) — it used
        # to be appended to `weaknesses` here; deliberately removed so it can never surface as a
        # biggest_risk/top-action item downstream (app.agents.mentor_synthesis).
    if revenue_estimate is not None:
        source_attribution["revenue_estimate"] = (
            "deterministic scenario calculator — not a trained model; per-field "
            f"assumption_source ({revenue_estimate.get('default_basis', 'unknown')} where the "
            "founder supplied no value) is in revenue_estimate.assumptions"
        )
    if market_intelligence is not None:
        source_attribution["market_intelligence"] = (
            "agent synthesis of user-submitted market evidence + deterministic funding-readiness rubric"
        )
        missing_evidence.extend(
            f"Market: {gap}" for gap in market_intelligence.get("evidence_gaps", [])
        )
    if competitor_analysis is not None:
        source_attribution["competitor_analysis"] = (
            "user-submitted competitor names (unverified) or generic unverified categories — never a "
            "verified company database"
        )
    if customer_personas is not None:
        source_attribution["customer_personas"] = "agent synthesis of user-submitted evidence and inference"
    if business_model is not None:
        source_attribution["business_model"] = "agent synthesis of user-submitted evidence and deterministic rubric"
        missing_evidence.extend(
            f"Business model: {gap}" for gap in business_model.get("evidence_gaps", [])
        )
    if customer_segment is not None:
        source_attribution["customer_segment"] = (
            "deterministic segment fallback from model/rubric evidence, or a trained clustering "
            "artifact when customer RFM input was supplied (Phase 5 / Student 3)"
        )
    if ranked_actions is not None:
        source_attribution["ranked_actions"] = "versioned deterministic ranking rules (Phase 5 / Student 3)"
    if risks is not None:
        source_attribution["risks"] = "fixed planning-risk templates grounded in readiness evidence (Phase 5 / Student 3)"
    if venture_positioning is not None:
        source_attribution["venture_positioning"] = (
            f"deterministic controlled-taxonomy resolution (resolution_source="
            f"{venture_positioning.get('resolution_source', 'unknown')}); Gemini's structured "
            "recommendation, if invoked, is advisory input only — the Judge Agent's rule set is "
            "the sole final authority, never overridden by Gemini's rationale text"
        )

    if industry_prediction is not None:
        industry_clause = (
            f"classified as '{industry_prediction['predicted_industry']}' "
            f"(model confidence {industry_prediction['confidence']:.0%})"
        )
        if industry_prediction.get("is_uncertain"):
            industry_clause += " — flagged uncertain, do not treat as a confident fact"
        industry_model_description = (
            f"ML model prediction ({industry_prediction.get('model_pipeline', 'unknown pipeline')}, "
            f"version {industry_prediction.get('model_version', 'unknown')})"
        )
    else:
        industry_clause = "not classified — the industry model was unavailable for this run"
        industry_model_description = "unavailable for this run"
    source_attribution["industry_prediction"] = industry_model_description

    readiness_level = funding_assessment["level"].replace("_", " ")
    overall_assessment = (
        f"This startup was {industry_clause} and rated '{readiness_level}' for funding "
        f"readiness ({funding_assessment['overall_score']}/100 on the {funding_assessment['rubric_version']} "
        f"rubric). " + " ".join(evidence_check.get("notes", []))
    ).strip()

    return {
        "overall_assessment": overall_assessment,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "missing_evidence": missing_evidence,
        "next_actions": next_actions,
        "confidence_level": confidence_level,
        "source_attribution": source_attribution,
        "suggested_possibilities": suggested_possibilities,
        "founder_guidance_items": founder_guidance_items,
        # Two distinct category outputs (see app.agents.venture_positioning): `model_category` is
        # the untouched trained-model output, relabeled as technical evidence; `venture_positioning`
        # is the founder-facing identity the Judge Agent's deterministic rule set already decided
        # upstream (app.agents.venture_positioning.resolve_venture_positioning) — never
        # re-decided or overridden here. `gemini_rationale` is carried through as display-only
        # text; nothing in this function (or in resolve_venture_positioning) ever parses it.
        "model_category": model_category,
        "venture_positioning": venture_positioning,
        "taxonomy_candidates": taxonomy_candidates or [],
        "gemini_structured_recommendation": gemini_structured_recommendation,
        "gemini_rationale": gemini_rationale,
        "positioning_correction_rationale": positioning_correction_rationale,
        # Phase 5 (Student 3) passthrough — never blended with the industry/funding scores above;
        # see app.agents.student3 for how each is produced.
        "customer_segment": customer_segment,
        "ranked_actions": ranked_actions or [],
        "risks": risks or [],
    }
