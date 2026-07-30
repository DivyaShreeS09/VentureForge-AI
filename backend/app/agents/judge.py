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

from app.agents.alternative_explanation_engine import build_alternative_explanation_set
from app.agents.confidence_engine import label_confidence
from app.agents.contradiction_engine import build_contradiction_set
from app.agents.evidence_ledger import build_evidence_ledger, summarize_ledger
from app.agents.founder_guidance import build_founder_guidance_items
from app.agents.hypothesis_engine import build_hypotheses_for_gaps
from app.agents.hypothesis_set import build_hypothesis_set
from app.agents.judge_voice import build_overall_assessment
from app.agents.venture_frame import build_venture_frame
from app.agents.venture_vocabulary import vocab_for

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


def _confidence_level(funding_assessment: dict, evidence_check: dict, evidence_ledger_summary: dict) -> str:
    """VentureForge Intelligence Architecture, Phase D: this used to compare the raw industry-
    classifier confidence against an undocumented 0.6 threshold in isolation. It now reads the same
    threshold via `app.agents.confidence_engine.label_confidence` (the one shared confidence
    engine), applied to `evidence_ledger_summary["overall_confidence"]` — a number that already
    combines the industry prediction *and* every rubric/market-evidence item, rather than the
    industry prediction alone. The `evidence_check.low_confidence` early-exit and the requirement
    that funding readiness also be at the "ready" level before "high" is granted are both preserved
    unchanged from the pre-Phase-D behavior.
    """
    if evidence_check.get("low_confidence"):
        return "low"
    overall_confidence = evidence_ledger_summary.get("overall_confidence", 0.0)
    if funding_assessment.get("level") == "ready" and label_confidence(overall_confidence) == "high":
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
    startup_name: str = "",
    startup_description: str = "",
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
    # Critical Fix #2/#5 (Product Intelligence Refinement Sprint): a small, category-keyed
    # vocabulary — never a new classifier, just the same primary_domain/model_category signals
    # already resolved upstream — so two ventures with an identical evidence profile (e.g. two
    # zero-evidence one-liners) still get recommendations flavored for their own category
    # (a "clinical pilot" vs. a "field trial" vs. a "design-partner pilot") instead of byte-identical
    # generic text. See app.agents.venture_vocabulary.
    vocab = vocab_for(
        (venture_positioning or {}).get("primary_domain"),
        (model_category or {}).get("label"),
        (venture_positioning or {}).get("deployment_sectors"),
    )
    suggested_possibilities = build_hypotheses_for_gaps(sorted(missing), vocab)
    founder_guidance_items = build_founder_guidance_items(funding_assessment, market_evidence, vocab)

    # Evidence Ledger (VentureForge Intelligence Architecture, Phase A) — a new, additive lens over
    # the same inputs this function already reconciles; built here, before `confidence_level`, so
    # Phase D can derive that existing field from this one shared confidence engine instead of its
    # own former ad hoc rule (see `_confidence_level`'s docstring for exactly what changed and what
    # didn't). It exists so every later phase (Hypothesis Set, Contradiction Detection, Decision
    # Synthesis) has one shared, auditable evidence structure to build on too.
    evidence_ledger = build_evidence_ledger(funding_assessment, market_evidence, industry_prediction)
    evidence_ledger_summary = summarize_ledger(evidence_ledger)

    confidence_level = _confidence_level(funding_assessment, evidence_check, evidence_ledger_summary)

    # Structured Venture Frame (VentureForge Intelligence Architecture, Phase B) — a new, additive
    # canonical understanding of the venture assembled from the same inputs this function already
    # reconciles. Does not change any field above or below; see app.agents.venture_frame for the
    # full audit of what it reuses versus what it adds.
    venture_frame = build_venture_frame(
        startup_name=startup_name,
        startup_description=startup_description,
        funding_assessment=funding_assessment,
        industry_prediction=industry_prediction,
        venture_positioning=venture_positioning,
        market_evidence=market_evidence,
        business_model=business_model,
        competitor_analysis=competitor_analysis,
    )

    # Hypothesis Set (VentureForge Intelligence Architecture, Phase C) — competing interpretations
    # built only from the Venture Frame + Evidence Ledger above; see app.agents.hypothesis_set for
    # what it does and does not build, and why. Additive: does not change any field above or below.
    hypothesis_set = build_hypothesis_set(venture_frame, evidence_ledger, funding_assessment)

    # Global Contradiction Detection (VentureForge Intelligence Architecture, Phase E) — a new,
    # additive reasoning layer over the Evidence Ledger + Venture Frame + Hypothesis Set above; see
    # app.agents.contradiction_engine for the full audit of what it reuses, what it does and does
    # not detect, and why. Additive: does not change any field above or below.
    contradiction_set = build_contradiction_set(evidence_ledger, venture_frame, hypothesis_set)

    # Alternative Explanation Engine (VentureForge Intelligence Architecture, Phase F) — broadens
    # the search space for every leading conclusion the Contradiction Engine already flagged as
    # genuinely open, plus the one stage-gated traction reading; see
    # app.agents.alternative_explanation_engine for the full audit of what it reuses and what it does
    # not attempt. Additive: does not change any field above or below, and makes no decision itself.
    alternative_explanation_set = build_alternative_explanation_set(
        evidence_ledger, venture_frame, hypothesis_set, contradiction_set
    )

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
        industry_model_description = (
            f"ML model prediction ({industry_prediction.get('model_pipeline', 'unknown pipeline')}, "
            f"version {industry_prediction.get('model_version', 'unknown')})"
        )
    else:
        industry_model_description = "unavailable for this run"
    source_attribution["industry_prediction"] = industry_model_description

    # Founder-facing summary sentence — see app.agents.judge_voice for the full rationale on why
    # this is composed separately from the raw classification/rubric data above (never a quoted
    # model label, never a "X/100 on the vN rubric" readout, never the evidence_check node's raw
    # technical notes). Narrates from the Judge's own resolved `venture_positioning` (never the raw
    # `industry_prediction` alone) so a weak classifier guess can never dominate this sentence when
    # the positioning resolution has already recovered to something better-reasoned.
    overall_assessment = build_overall_assessment(
        industry_prediction,
        funding_assessment,
        evidence_check,
        venture_positioning=venture_positioning,
        model_category=model_category,
    )

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
        # See app.agents.evidence_ledger — additive, does not affect confidence_level above or any
        # other existing field.
        "evidence_ledger": evidence_ledger,
        "evidence_ledger_summary": evidence_ledger_summary,
        "venture_frame": venture_frame,
        "hypothesis_set": hypothesis_set,
        "contradiction_set": contradiction_set,
        "alternative_explanation_set": alternative_explanation_set,
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
