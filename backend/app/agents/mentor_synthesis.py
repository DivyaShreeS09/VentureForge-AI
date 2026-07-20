"""Deterministic Mentor Synthesis (Full Mentor Orchestration phase).

Reconciles the Judge Agent's already-decided output plus every business-intelligence agent's
output into one coherent MentorInterpretation (see app.agents.mentor_schemas) — never a
concatenation of raw agent dicts. This is the complete fallback: every field is always populated
from here whether or not Gemini is configured (see app.agents.mentor_reviewer for the optional,
narrow Gemini narrative layer on top).

Key reconciliation rules (see module functions below for where each is implemented):
  - `venture_positioning` (the Judge's already-resolved founder-facing identity) is used as the
    identity throughout; `model_category` (the raw ML label) only ever appears inside
    `evidence_and_uncertainty` as technical-evidence caveat text.
  - `strengths`/`real_weaknesses`/`suggested_possibilities` are deprecated, backward-compatibility
    string fields only — every founder-facing rendering (validation plan, top actions, mentor
    verdict) is instead derived from `founder_guidance_items` (app.agents.founder_guidance), one
    structured, coached item per funding-readiness dimension plus capability-library signals,
    carrying exactly one deterministic priority order shared by every consumer.
"""

from __future__ import annotations

from app.agents.founder_guidance import finalize_priority
from app.agents.mentor_schemas import MENTOR_SCHEMA_VERSION
from app.ml.capability_library import CAPABILITY_LIBRARY_VERSION, classify_capabilities

MENTOR_SYNTHESIS_VERSION = "v1"

# Capability-derived items get a modest, fixed internal weight so they generally rank behind
# rubric-derived items of the same category (resolving core evidence gaps first) while still
# competing fairly within `finalize_priority`'s single shared ordering.
_CAPABILITY_ITEM_WEIGHT = 0.05

_ACTIONABLE_CATEGORIES = ("confirmed_risk", "validation_opportunity", "discovery_question")

# A clearly-labeled ("[Suggested]") fallback target-user hint per controlled domain, used only
# when the founder supplied no market_evidence.customer_type — never presented as a confirmed
# fact, just a reasonable starting guess about who typically buys/uses a venture in this domain.
_DOMAIN_TYPICAL_CUSTOMER: dict[str, str] = {
    "Smart Facilities Technology": "facilities managers at campuses, hotels, or commercial buildings",
    "PropTech": "property managers",
    "Sustainability Technology": "facilities or sustainability managers",
    "Clinical Decision Support": "clinicians reviewing flagged cases",
    "Remote Patient Monitoring": "clinicians and care teams monitoring patients remotely",
    "HealthTech Diagnostics": "clinicians reviewing flagged diagnostic cases",
    "Restaurant Operations Technology": "independent restaurant owners and kitchen managers",
    "Food-Cost Management": "independent restaurant owners and kitchen managers",
    "Campus & Student Services": "students on one campus",
    "Peer Collaboration Marketplaces": "students on one campus or at one event",
    "EdTech": "students and educators",
}


def _capability_guidance_items(feature_gap: dict) -> list[dict]:
    """Build founder_guidance_items for capability-library signals not already covered by the
    funding-readiness rubric — `recommended_capabilities` become `improvement_opportunity` items,
    `premature_capabilities` become `future_enhancement` items (see app.agents.founder_guidance for
    the shared category/priority model these merge into).
    """
    items: list[dict] = []
    for cap in feature_gap.get("recommended_capabilities", []):
        items.append(
            {
                "dimension": f"capability:{cap['id']}",
                "category": "improvement_opportunity",
                "status": "Good start — can be strengthened",
                "title": f"Consider building: {cap['label']}",
                "observation": cap["description"],
                "why_it_matters": cap["reason"],
                "next_step": f"Validate: {cap['validation_question']}",
                "example": cap["description"],
                "priority": 0,
                "evidence_state": "not_applicable",
                "source": "deterministic",
                "_weight": _CAPABILITY_ITEM_WEIGHT,
            }
        )
    for cap in feature_gap.get("premature_capabilities", []):
        items.append(
            {
                "dimension": f"capability:{cap['id']}",
                "category": "future_enhancement",
                "status": "Future enhancement",
                "title": f"Not yet: {cap['label']}",
                "observation": cap["description"],
                "why_it_matters": cap["reason"],
                "next_step": f"Revisit once its prerequisites are in place: {cap['validation_question']}",
                "example": cap["description"],
                "priority": 0,
                "evidence_state": "not_applicable",
                "source": "deterministic",
                "_weight": _CAPABILITY_ITEM_WEIGHT,
            }
        )
    return items


_PARTICIPANTS_BY_DIMENSION: dict[str, str] = {
    "problem_clarity": "3-5 people in the target group",
    "customer_pain_evidence": "5+ people in the target group",
    "market_size_evidence": "N/A (secondary research)",
    "product_maturity": "1 real user or site",
    "traction": "1 pilot site/customer",
    "revenue_model_clarity": "3 prospective customers",
    "team_completeness": "N/A (internal)",
    "competitive_differentiation": "2-3 closest alternatives",
}


def _build_idea_understanding(
    startup_name: str, startup_description: str, market_evidence: dict, venture_positioning: dict
) -> dict:
    domain = venture_positioning.get("primary_domain") or "an unresolved domain"
    sectors = venture_positioning.get("deployment_sectors") or []
    business_context = f"Positioned as {domain}"
    if sectors:
        business_context += f", serving {', '.join(sectors)}"
    business_context += "."

    typical_customer = _DOMAIN_TYPICAL_CUSTOMER.get(domain)
    target_user = market_evidence.get("customer_type") or (
        f"[Suggested] {typical_customer}." if typical_customer
        else "Not yet specified by the founder — a real segment must still be named and validated."
    )

    return {
        "summary": f"{startup_name} is building in the {domain} space: {startup_description.strip()}",
        "target_user": target_user,
        "problem": market_evidence.get("target_market")
        or "Not explicitly stated by the founder yet — inferred only from the description above.",
        "proposed_solution": startup_description.strip(),
        "business_context": business_context,
    }


def _summarize_customer_and_market(market_intelligence: dict | None, customer_personas: dict | None) -> str:
    if not market_intelligence:
        return "No market intelligence was generated for this run."
    parts = [market_intelligence.get("market_summary", "")]
    personas = (customer_personas or {}).get("personas") or []
    if personas:
        names = ", ".join(p["persona_name"] for p in personas)
        parts.append(f"Suggested personas (assumptions requiring validation, not confirmed facts): {names}.")
    return " ".join(p for p in parts if p)


def _summarize_business_model(business_model: dict | None) -> str:
    if not business_model:
        return "No business-model synthesis was generated for this run."
    text = business_model.get("value_proposition", "")
    if business_model.get("revenue_streams"):
        text += f" Suggested revenue streams: {business_model['revenue_streams']}."
    return text


def _summarize_competitors(competitor_analysis: dict | None) -> str:
    if not competitor_analysis:
        return "No competitor analysis was generated for this run."
    verified = competitor_analysis.get("verified_competitors") or []
    if verified:
        names = ", ".join(c["name"] for c in verified)
        base = f"Founder-named alternatives (unverified by this system): {names}."
    else:
        base = "No competitors were named by the founder; no company name is invented here."
    manual = (competitor_analysis.get("manual_process_alternative") or {}).get("description")
    do_nothing = (competitor_analysis.get("do_nothing_alternative") or {}).get("description")
    if manual:
        base += f" Realistic status-quo alternative: {manual}."
    if do_nothing:
        base += f" Baseline alternative: {do_nothing}."
    return base


def _summarize_revenue(revenue_estimate: dict | None) -> str:
    if not revenue_estimate or not revenue_estimate.get("scenarios"):
        return "No revenue scenario is available for this run."
    missing = revenue_estimate.get("missing_assumptions") or []
    assumptions = revenue_estimate.get("assumptions") or {}
    if not missing:
        basis = "entirely founder-supplied assumptions"
    elif len(missing) == len(assumptions):
        basis = "entirely suggested-default assumptions (never presented as fact, all editable)"
    else:
        basis = "a mix of founder-supplied and suggested-default assumptions"
    base_scenario = revenue_estimate["scenarios"]["base"]
    return (
        f"Base-case 12-month scenario using {basis}: "
        f"${base_scenario['annual_revenue_usd']:,.0f} annual revenue (see revenue_estimate for the full range)."
    )


def _build_mvp_recommendation(
    primary_domain: str | None, feature_gap: dict, market_evidence: dict, is_low_confidence: bool
) -> dict:
    if is_low_confidence:
        return {
            "target_user": "Not yet defined — discovery must narrow this before an MVP is scoped.",
            "single_core_problem": "Not yet defined — the idea is too broad to scope a build yet.",
            "minimum_workflow": "None recommended yet; validate the target user and problem first.",
            "included_capabilities": [],
            "excluded_for_now": [
                c["id"] for c in feature_gap["recommended_capabilities"] + feature_gap["premature_capabilities"]
            ],
            "success_metric": "N/A until a specific user/problem pair is validated.",
            "pilot_environment": "N/A",
            "reasons": [
                "The venture positioning signal is low-confidence; recommending a specific MVP now "
                "would fabricate specificity that doesn't exist yet."
            ],
        }

    core_candidates = [
        c for c in feature_gap["present_capabilities"] + feature_gap["recommended_capabilities"]
        if c["importance"] == "core"
    ]
    included = core_candidates[:2] or feature_gap["present_capabilities"][:1] or feature_gap["recommended_capabilities"][:1]
    included_ids = {c["id"] for c in included}
    excluded_for_now = [
        c["id"]
        for c in feature_gap["recommended_capabilities"] + feature_gap["premature_capabilities"]
        if c["id"] not in included_ids
    ]

    workflow_labels = ", ".join(c["label"] for c in included) or "the single core workflow"
    target_user = (
        market_evidence.get("customer_type")
        or _DOMAIN_TYPICAL_CUSTOMER.get(primary_domain or "")
        or "one specific early-adopter segment (not yet named by the founder)"
    )

    return {
        "target_user": f"[Suggested] {target_user}, scoped to one site/segment first.",
        "single_core_problem": f"[Suggested] The narrowest version of the problem this idea addresses in the {primary_domain} space.",
        "minimum_workflow": f"[Suggested] {workflow_labels}, applied to one pilot only (e.g. a single building, restaurant, clinic, or event) — not a broad launch.",
        "included_capabilities": [c["id"] for c in included],
        "excluded_for_now": excluded_for_now,
        "success_metric": "[Suggested] One measurable outcome from the single pilot (usage, retention, or a validated willingness-to-pay signal).",
        "pilot_environment": "[Suggested] One real site/customer/segment, not a broad launch.",
        "reasons": [
            "Scoped to a single user segment and one core workflow to de-risk the idea cheaply.",
            "Advanced or prerequisite-blocked capabilities are excluded until their dependencies exist.",
        ],
    }


def _build_validation_plan(guidance_items: list[dict]) -> list[dict]:
    """Derived from the single shared `founder_guidance_items` ranking (already priority-ordered)
    rather than independently re-sorting the funding-readiness breakdown — see
    app.agents.founder_guidance for why there is now exactly one prioritized ordering. Includes
    `future_enhancement` items too (prerequisite-gated capabilities) since "validate the
    prerequisite first" is itself a validation task, even though those items are low-urgency for
    the shorter `top_next_actions` list (see `_prioritize_next_actions`).
    """
    relevant = [item for item in guidance_items if item["category"] in (*_ACTIONABLE_CATEGORIES, "future_enhancement")]
    actions: list[dict] = []
    for item in relevant:
        is_capability = item["dimension"].startswith("capability:")
        source_gap = item["dimension"].removeprefix("capability:")
        participants = "N/A" if is_capability else _PARTICIPANTS_BY_DIMENSION.get(item["dimension"], "N/A")
        actions.append(
            {
                "priority": len(actions) + 1,
                "question_to_answer": item["title"],
                "method": item["next_step"],
                "target_participants": participants,
                "success_criterion": f"Clear, direct evidence resolving: {item['observation']}",
                "source_gap": source_gap,
                "build_dependency": "Must be resolved before scaling beyond the initial pilot.",
            }
        )
    return actions


def _build_roadmap(funding_assessment: dict, is_low_confidence: bool, validation_plan: list[dict]) -> list[dict]:
    has_strong_evidence = funding_assessment.get("level") == "ready" and not is_low_confidence

    period_1_activities = [a["method"] for a in validation_plan[:3]] or [
        "Interview target users to confirm the problem is real."
    ]
    period_1 = {
        "period": "days_1_30",
        "focus": "Discovery, evidence-gathering, buyer/user validation",
        "activities": period_1_activities,
        "rationale": (
            "Even with strong existing evidence, a short confirmation pass de-risks the next 60 days."
            if has_strong_evidence
            else "Validation must come before build effort while core assumptions remain unconfirmed."
        ),
    }
    period_2 = {
        "period": "days_31_60",
        "focus": "Minimal prototype / pilot preparation",
        "activities": [
            "Build the minimum workflow for the single pilot only.",
            "Prepare the pilot environment and its success metric.",
        ],
        "rationale": (
            "Confirmed evidence allows prototype work to start sooner than a typical thin-evidence case."
            if has_strong_evidence
            else "Building begins only once days 1-30 validation reduces the biggest open risks."
        ),
    }
    period_3 = {
        "period": "days_61_90",
        "focus": "Pilot execution, measurement, and iteration",
        "activities": [
            "Run the pilot with the single target segment.",
            "Measure the defined success metric and iterate.",
        ],
        "rationale": "Execution and measurement close the loop on the hypotheses set in days 1-60.",
    }
    return [period_1, period_2, period_3]


def _prioritize_next_actions(guidance_items: list[dict]) -> list[str]:
    """Derived from the single shared `founder_guidance_items` ranking — see
    app.agents.founder_guidance. This is deliberately the same ordering `_build_validation_plan`
    renders in more detail, not a second independently-computed ranking (Phase 1 dedup fix). Gemini
    never supplies or reorders this ranking — see app.agents.mentor_reviewer.
    """
    actionable = [item for item in guidance_items if item["category"] in _ACTIONABLE_CATEGORIES]
    actions = [item["next_step"] for item in actionable[:5]]
    if not actions:
        actions = ["Continue validating the target user and problem before building further."]
    return actions


def _build_mentor_verdict(funding_assessment: dict, guidance_items: list[dict], top_next_actions: list[str]) -> dict:
    """`strongest_signal`/`biggest_risk` are sourced entirely from `founder_guidance_items` — never
    from the raw `strengths`/`weaknesses` string lists (deprecated), and never from the Historical
    Pattern Signal / success-prediction uncertainty (see app.ml.success_predictor — that signal is
    informational only and must never become a founder-facing risk or verdict driver).
    """
    level = funding_assessment.get("level", "early_stage")
    readiness_map = {
        "ready": "Investor-ready signals present.",
        "developing": "Developing — real progress alongside real gaps.",
        "early_stage": "Early-stage — validation-first, not build-first.",
    }
    strength_items = [item for item in guidance_items if item["category"] == "strength"]
    risk_items = [item for item in guidance_items if item["category"] in _ACTIONABLE_CATEGORIES]
    return {
        "readiness_level": level,
        "concise_verdict": readiness_map.get(level, level),
        "strongest_signal": (
            f"{strength_items[0]['title']} {strength_items[0]['why_it_matters']}"
            if strength_items
            else "No confirmed strength yet — everything here is still a hypothesis."
        ),
        "biggest_risk": (
            f"{risk_items[0]['title']} {risk_items[0]['why_it_matters']}"
            if risk_items
            else "No confirmed risk yet — the biggest opportunity is how much remains to validate."
        ),
        "immediate_priority": top_next_actions[0] if top_next_actions else "Define and validate the target user and problem.",
    }


def _build_evidence_and_uncertainty(
    judge_summary: dict, success_prediction: dict | None, revenue_estimate: dict | None
) -> dict:
    model_category = judge_summary.get("model_category") or {}
    venture_positioning = judge_summary.get("venture_positioning") or {}

    low_confidence_flags = []
    if venture_positioning.get("is_low_confidence"):
        low_confidence_flags.append("Venture positioning is low-confidence.")
    if model_category.get("is_uncertain"):
        low_confidence_flags.append("Raw industry classification is uncertain.")
    if success_prediction and success_prediction.get("is_uncertain"):
        low_confidence_flags.append("Historical pattern signal is uncertain.")

    missing = (revenue_estimate or {}).get("missing_assumptions") or []
    assumptions = (revenue_estimate or {}).get("assumptions") or {}
    if not revenue_estimate or not revenue_estimate.get("scenarios"):
        revenue_summary = "No revenue assumptions were supplied or computed."
    elif not missing:
        revenue_summary = "All revenue figures are founder-supplied."
    elif len(missing) == len(assumptions):
        revenue_summary = "All revenue figures are suggested defaults, not founder-supplied."
    else:
        revenue_summary = "Revenue figures are a mix of founder-supplied and suggested-default values."

    return {
        "model_category_caveat": (
            "model_category is the raw trained classifier's technical output — a coarse label, "
            "never the founder-facing identity (see venture_positioning above)."
        ),
        "historical_pattern_signal_caveat": (success_prediction or {}).get(
            "disclaimer",
            "Historical Pattern Signal: trained on already-funded companies — treat as a loose "
            "historical pattern match, not a probability of this specific idea's success.",
        ),
        "low_confidence_flags": low_confidence_flags,
        "user_supplied_vs_suggested_summary": revenue_summary,
        "unresolved_questions": list(judge_summary.get("missing_evidence", [])),
    }


def build_deterministic_mentor(
    startup_name: str,
    startup_description: str,
    judge_summary: dict,
    funding_assessment: dict,
    success_prediction: dict | None = None,
    revenue_estimate: dict | None = None,
    market_intelligence: dict | None = None,
    competitor_analysis: dict | None = None,
    customer_personas: dict | None = None,
    business_model: dict | None = None,
    market_evidence: dict | None = None,
) -> dict:
    """Build the complete MentorInterpretation dict (see app.agents.mentor_schemas), fully
    deterministic, no network call. This is the always-available fallback — every field is
    populated here whether or not Gemini is ever configured; nothing disappears without it.
    """
    market_evidence = market_evidence or {}
    venture_positioning = judge_summary.get("venture_positioning") or {}
    primary_domain = venture_positioning.get("primary_domain")
    is_low_confidence = bool(venture_positioning.get("is_low_confidence", True))

    # Deprecated, backward-compatibility only — kept populated so any external/technical consumer
    # of the old shape doesn't break, but nothing below reads them. See founder_guidance_items.
    strengths = list(judge_summary.get("strengths", []))
    real_weaknesses = list(judge_summary.get("weaknesses", []))
    suggested_possibilities = list(judge_summary.get("suggested_possibilities", []))

    feature_gap = classify_capabilities(startup_description, primary_domain, is_low_confidence)

    # The single structured, coached list: funding-readiness-dimension items already built by
    # app.agents.judge, merged with capability-library-derived items, re-ranked together so there
    # is exactly one prioritized ordering (see app.agents.founder_guidance).
    founder_guidance_items = finalize_priority(
        list(judge_summary.get("founder_guidance_items", [])) + _capability_guidance_items(feature_gap),
        strip_internal=True,
    )

    mvp_recommendation = _build_mvp_recommendation(primary_domain, feature_gap, market_evidence, is_low_confidence)
    validation_plan = _build_validation_plan(founder_guidance_items)
    roadmap = _build_roadmap(funding_assessment, is_low_confidence, validation_plan)
    top_next_actions = _prioritize_next_actions(founder_guidance_items)
    mentor_verdict = _build_mentor_verdict(funding_assessment, founder_guidance_items, top_next_actions)
    evidence_and_uncertainty = _build_evidence_and_uncertainty(judge_summary, success_prediction, revenue_estimate)

    idea_understanding = _build_idea_understanding(startup_name, startup_description, market_evidence, venture_positioning)
    venture_positioning_text = (
        f"{venture_positioning.get('primary_domain', 'Unresolved')}"
        + (f" (also relevant: {', '.join(venture_positioning.get('secondary_domains', []))})" if venture_positioning.get("secondary_domains") else "")
        + (" — flagged low-confidence; treat as a working hypothesis, not a settled identity." if is_low_confidence else ".")
    )

    return {
        "mentor_schema_version": MENTOR_SCHEMA_VERSION,
        "source": "deterministic",
        "idea_understanding": idea_understanding,
        "venture_positioning": venture_positioning_text,
        "strengths": strengths,
        "real_weaknesses": real_weaknesses,
        "suggested_possibilities": suggested_possibilities,
        "founder_guidance_items": founder_guidance_items,
        "feature_gap_analysis": feature_gap,
        "customer_and_market": _summarize_customer_and_market(market_intelligence, customer_personas),
        "business_model": _summarize_business_model(business_model),
        "competitor_landscape": _summarize_competitors(competitor_analysis),
        "revenue_scenarios": _summarize_revenue(revenue_estimate),
        "mvp_recommendation": mvp_recommendation,
        "validation_plan": validation_plan,
        "roadmap_30_60_90": roadmap,
        "top_next_actions": top_next_actions,
        "mentor_verdict": mentor_verdict,
        "evidence_and_uncertainty": evidence_and_uncertainty,
        "source_attribution": {
            "idea_understanding": "derived from the founder's submitted name/description and market_evidence",
            "venture_positioning": "restates the Judge Agent's already-decided resolution — never a second decision",
            "strengths_real_weaknesses": "deprecated, backward-compatibility only — see founder_guidance_items",
            "suggested_possibilities": "deprecated, backward-compatibility only — see founder_guidance_items",
            "founder_guidance_items": "structured, coached items merging funding-readiness rubric states and capability-library signals into one deterministic priority order",
            "feature_gap_analysis": f"controlled capability library {CAPABILITY_LIBRARY_VERSION}, keyed by venture_positioning.primary_domain",
            "customer_and_market": "market intelligence + customer persona agent synthesis",
            "business_model": "business model agent synthesis",
            "competitor_landscape": "user-submitted competitor names (unverified) or generic categories — never a verified database",
            "revenue_scenarios": "deterministic revenue scenario calculator, not a trained model",
            "mvp_recommendation": "derived from feature_gap_analysis + market_evidence",
            "validation_plan": "derived from founder_guidance_items (actionable categories only)",
            "roadmap_30_60_90": "derived from the validation plan and funding-readiness level",
            "top_next_actions": "derived from founder_guidance_items — the same single priority order as validation_plan, never Gemini free text",
            "mentor_verdict": "derived from funding_assessment.level and founder_guidance_items",
            "evidence_and_uncertainty": "derived from model_category, venture_positioning, success_prediction, revenue_estimate",
        },
    }
