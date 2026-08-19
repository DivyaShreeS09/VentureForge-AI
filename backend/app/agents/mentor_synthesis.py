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

Sprint 8 ("The Mentor") rewrote every sentence built in this module for founder-facing voice — no
rubric labels, no quoted model output, no backend terminology, never a bare "I'm not sure." None of
the underlying data (scores, categories, priority order, which capabilities are included/excluded)
changed; only how it's narrated. See `_contradiction_note` for the one genuinely new piece of
reasoning this sprint added: a conservative, deterministic check for when a founder's own submitted
fields describe two different target customers.
"""

from __future__ import annotations

from app.agents.competitor_intelligence import build_competitor_intelligence
from app.agents.consistency_audit import audit_founder_report
from app.agents.feature_intelligence import build_feature_intelligence
from app.agents.founder_guidance import finalize_priority, impact_for_category
from app.agents.founder_intelligence import (
    build_critical_blind_spots,
    build_explainability_index,
    build_feature_gap_vs_market,
    build_founder_challenge_mode,
    build_founder_iq_report,
    build_funding_stage_ladder,
    build_investor_intelligence,
    build_investor_questions,
    build_moat_intelligence,
)
from app.agents.founder_report import build_founder_report
from app.agents.go_to_market_intelligence import build_go_to_market_intelligence
from app.agents.industry_knowledge_packs import get_industry_knowledge_pack
from app.agents.knowledge_audit import audit_knowledge_sources
from app.agents.mentor_schemas import MENTOR_SCHEMA_VERSION
from app.agents.pricing_intelligence import build_pricing_intelligence
from app.agents.regulatory_context import classify_regulatory_context
from app.agents.startup_benchmark import build_startup_benchmark
from app.agents.venture_vocabulary import with_article
from app.ml.capability_library import CAPABILITY_LIBRARY_VERSION, classify_capabilities
from app.ml.venture_retrieval import retrieve_similar_ventures

MENTOR_SYNTHESIS_VERSION = "v1"

# Capability-derived items get a modest, fixed internal weight so they generally rank behind
# rubric-derived items of the same category (resolving core evidence gaps first) while still
# competing fairly within `finalize_priority`'s single shared ordering.
_CAPABILITY_ITEM_WEIGHT = 0.05

_ACTIONABLE_CATEGORIES = ("confirmed_risk", "validation_opportunity", "discovery_question")

# A reasonable starting guess for who typically buys/uses a venture in this domain, used only when
# the founder supplied no market_evidence.customer_type — always framed as a guess to confirm, never
# presented as a fact about this specific founder's customer.
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

_STOPWORDS = {"the", "a", "an", "and", "or", "for", "to", "of", "in", "on", "with", "that", "this", "at", "your", "you"}


def _significant_words(text: str) -> set[str]:
    return {w.strip(".,!?;:\"'").lower() for w in text.split() if len(w) > 3 and w.lower() not in _STOPWORDS}


def _contradiction_note(startup_description: str, market_evidence: dict) -> str | None:
    """A conservative, deterministic contradiction check — compares only the founder's own
    submitted text (the free-form description vs. the structured customer_type answer), never
    infers or invents a customer that wasn't named anywhere. Fires only when the founder gave a
    short, specific customer_type answer that shares no significant word with their own
    description — the one case that can be checked safely without accusing a founder over ordinary
    phrasing differences (e.g. "restaurant owners" vs. "restaurants" still overlaps on "restaurant").
    """
    customer_type = (market_evidence or {}).get("customer_type")
    if not customer_type or len(customer_type.split()) > 6:
        return None
    customer_words = _significant_words(customer_type)
    description_words = _significant_words(startup_description)
    if not customer_words or not description_words:
        return None
    # Substring containment (not exact token equality) so ordinary word-form differences —
    # "restaurant" in a customer_type answer vs. "restaurants" in the description — never count
    # as a contradiction; only genuinely unrelated words do.
    overlaps = any(cw in dw or dw in cw for cw in customer_words for dw in description_words)
    if overlaps:
        return None
    return (
        f'I\'m noticing two slightly different customers here — your description reads like one '
        f'group, but you named "{customer_type}" as the target customer elsewhere. Before building '
        "further, I'd clarify which one feels like the first real buyer. It's fine to serve both "
        "eventually — the first pilot just needs one clear answer."
    )


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
                "title": f"Worth adding eventually: {cap['label']}.",
                "observation": cap["description"],
                "why_it_matters": cap["reason"],
                "next_step": f"Before you build it, answer this: {cap['validation_question']}",
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
                "title": f"Not yet — {cap['label']} would be premature right now.",
                "observation": cap["description"],
                "why_it_matters": cap["reason"],
                "next_step": f"Revisit this once its prerequisite is real: {cap['validation_question']}",
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

# Founder Consulting Experience Sprint — a coarse, disclosed planning estimate (difficulty,
# duration) for the merged Founder Strategy section, keyed off the same participants profile above
# rather than a new per-venture computation. Always a rough, labeled estimate (never presented as a
# measured fact) — the point is giving a founder a sense of scale, not a precise schedule.
_EFFORT_BY_DIMENSION: dict[str, tuple[str, str]] = {
    "problem_clarity": ("Easy", "3-5 days"),
    "customer_pain_evidence": ("Easy", "1 week"),
    "market_size_evidence": ("Easy", "2-3 days"),
    "product_maturity": ("Medium", "2-4 weeks"),
    "traction": ("Medium", "2-4 weeks"),
    "revenue_model_clarity": ("Easy", "1 week"),
    "team_completeness": ("Hard", "2-6 weeks"),
    "competitive_differentiation": ("Easy", "3-5 days"),
}
_DEFAULT_EFFORT = ("Medium", "1-2 weeks")

# Founder Report Experience Redesign — a concrete "done means X, not Y" completion bar per
# dimension, so a founder can't quietly mark an action complete after doing something adjacent but
# easier (e.g. recruiting a pilot instead of actually running one). Reuses the same dimension set
# as everything else above; no new evidence, just a sharper definition of "finished."
_DONE_MEANS_BY_DIMENSION: dict[str, str] = {
    "problem_clarity": "Done means the one-sentence problem statement survived contact with 3 real people, not that you wrote it down.",
    "customer_pain_evidence": "Done means 5 real conversations happened about their current behavior, not that you sent 5 messages.",
    "market_size_evidence": "Done means a sourced number exists, not a confident guess.",
    "product_maturity": "Done means one real person used it, not that it works in a demo.",
    "traction": "Done means a signed commitment exists, not a verbal 'sounds interesting.'",
    "revenue_model_clarity": "Done means 3 real people reacted to a real price, not that you picked a number.",
    "team_completeness": "Done means the specific gap has a named owner or advisor, not just an acknowledgment that it exists.",
    "competitive_differentiation": "Done means you can name the one dimension that actually wins, not a list of features.",
}
_DEFAULT_DONE_MEANS = "Done means the concrete evidence exists, not that the task was attempted."


def _build_idea_understanding(
    startup_name: str, startup_description: str, market_evidence: dict, venture_positioning: dict
) -> dict:
    domain = venture_positioning.get("primary_domain") or "an unresolved space"
    sectors = venture_positioning.get("deployment_sectors") or []

    business_context = f"I'd place this as {with_article(domain)} play"
    if sectors:
        business_context += f", most relevant to {', '.join(sectors)}"
    business_context += "."
    contradiction = _contradiction_note(startup_description, market_evidence)
    if contradiction:
        business_context += f" {contradiction}"

    typical_customer = _DOMAIN_TYPICAL_CUSTOMER.get(domain)
    if market_evidence.get("customer_type"):
        target_user = market_evidence["customer_type"]
    elif typical_customer:
        target_user = (
            f"You haven't named a specific buyer yet, so my working guess — based on who usually "
            f"buys into this kind of venture — is {typical_customer}. Confirm that with a real "
            "conversation before you commit to it."
        )
    else:
        target_user = (
            "Most founders haven't nailed this down yet at this stage, and that's completely "
            "normal. Here's how I'd answer it over the next two weeks: talk to five people you "
            "*think* might be the buyer, and let their reaction tell you if you found the right one."
        )

    if market_evidence.get("target_market"):
        problem = market_evidence["target_market"]
    else:
        problem = (
            "You haven't spelled this out yet, which is common this early. I'd write one sentence "
            "naming exactly who feels this problem and what it costs them — that sentence alone "
            "will sharpen everything else in this plan."
        )

    return {
        "summary": f"Here's what I understand you're building, {startup_name}: {startup_description.strip()}",
        "target_user": target_user,
        "problem": problem,
        "proposed_solution": startup_description.strip(),
        "business_context": business_context,
    }


def _summarize_customer_and_market(market_intelligence: dict | None, customer_personas: dict | None) -> str:
    if not market_intelligence:
        return (
            "I don't have enough submitted evidence yet to say anything concrete about your "
            "market — that's the first gap worth closing."
        )
    parts = [market_intelligence.get("market_summary", "")]
    personas = (customer_personas or {}).get("personas") or []
    if personas:
        names = ", ".join(p["persona_name"] for p in personas)
        parts.append(
            f"My best working guesses for who you're building for: {names} — treat these as "
            "starting points to test, not confirmed segments."
        )
    return " ".join(p for p in parts if p)


def _summarize_business_model(business_model: dict | None) -> str:
    if not business_model:
        return "There's no business-model read for this run yet."
    text = business_model.get("value_proposition", "")
    if business_model.get("revenue_streams"):
        text += f" On pricing, here's where I'd start: {business_model['revenue_streams']}."
    return text


def _summarize_competitors(competitor_analysis: dict | None) -> str:
    if not competitor_analysis:
        return "No competitive read exists yet for this run."
    verified = competitor_analysis.get("verified_competitors") or []
    if verified:
        names = ", ".join(c["name"] for c in verified)
        base = (
            f"You named {names} yourself — I haven't independently verified these, but they're "
            "your own read on the field, and worth taking seriously."
        )
    else:
        base = (
            "You haven't named a competitor yet, and I'm not going to invent one — that's worth "
            "naming honestly before you go much further."
        )
    manual = (competitor_analysis.get("manual_process_alternative") or {}).get("description")
    do_nothing = (competitor_analysis.get("do_nothing_alternative") or {}).get("description")
    if manual:
        base += f" Realistically, most people in this position get by today with: {manual}."
    if do_nothing:
        base += f" And the honest baseline — doing nothing at all — looks like: {do_nothing}."
    return base


def _summarize_revenue(revenue_estimate: dict | None) -> str:
    if not revenue_estimate or not revenue_estimate.get("scenarios"):
        return "There's no revenue scenario to show yet for this run."
    missing = revenue_estimate.get("missing_assumptions") or []
    assumptions = revenue_estimate.get("assumptions") or {}
    if not missing:
        basis = "using the numbers you gave me"
    elif len(missing) == len(assumptions):
        basis = "using placeholder numbers, since you haven't supplied your own yet"
    else:
        basis = "using a mix of your numbers and a few placeholders"
    base_scenario = revenue_estimate["scenarios"]["base"]
    return (
        f"A realistic base case for your first 12 months, {basis}: about "
        f"${base_scenario['annual_revenue_usd']:,.0f} in annual revenue. Treat this as a starting "
        "estimate to sharpen, not a forecast."
    )


def _build_mvp_recommendation(
    primary_domain: str | None, feature_gap: dict, market_evidence: dict, is_low_confidence: bool
) -> dict:
    if is_low_confidence:
        return {
            "target_user": "Not yet — the positioning itself is still too unsettled to name a specific first user honestly.",
            "single_core_problem": "Not yet — narrow down the space itself before locking in a single problem to solve.",
            "minimum_workflow": "Hold off on scoping a workflow until the target user and problem are clearer.",
            "included_capabilities": [],
            "excluded_for_now": [
                c["id"] for c in feature_gap["recommended_capabilities"] + feature_gap["premature_capabilities"]
            ],
            "success_metric": "Not applicable until you've validated a specific user/problem pair.",
            "pilot_environment": "Not applicable yet.",
            "reasons": [
                "I'd rather tell you honestly that this isn't settled yet than hand you a specific "
                "MVP that only looks confident because I made something up."
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

    workflow_labels = ", ".join(c["label"] for c in included) or "your single core workflow"
    target_user = (
        market_evidence.get("customer_type")
        or _DOMAIN_TYPICAL_CUSTOMER.get(primary_domain or "")
        or "one specific early-adopter segment you haven't named yet"
    )

    return {
        "target_user": f"Start with {target_user}, and only that one segment.",
        "single_core_problem": (
            f"The narrowest possible version of the problem you're solving in the {primary_domain} "
            "space — resist the urge to solve the whole thing at once."
        ),
        "minimum_workflow": (
            f"{workflow_labels}, running for one pilot only (one building, restaurant, clinic, or "
            "event) — not a broad launch."
        ),
        "included_capabilities": [c["id"] for c in included],
        "excluded_for_now": excluded_for_now,
        "success_metric": "One number that tells you the pilot worked — usage, retention, or a real willingness-to-pay signal.",
        "pilot_environment": "One real site, customer, or segment — not a broad launch.",
        "reasons": [
            "Narrowing to one segment and one workflow is how you de-risk this cheaply — it's a strength, not a limitation.",
            "Anything gated on a capability you don't have yet stays out of scope until that dependency is real.",
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
        difficulty, duration = _DEFAULT_EFFORT if is_capability else _EFFORT_BY_DIMENSION.get(item["dimension"], _DEFAULT_EFFORT)
        actions.append(
            {
                "priority": len(actions) + 1,
                "question_to_answer": item["title"],
                "method": item["next_step"],
                "target_participants": participants,
                "success_criterion": (
                    f"You'll know this is answered once you have real evidence here — right now "
                    f"what you have is: {item['observation']}."
                ),
                "source_gap": source_gap,
                "build_dependency": "Resolve this before you scale past your first pilot — everything after leans on it.",
                # Founder Consulting Experience Sprint — additive fields feeding the Founder
                # Strategy section of app.agents.founder_report; the pydantic ValidationAction
                # model doesn't declare these, so they're silently dropped if this dict is ever
                # validated as a standalone MentorInterpretation.validation_plan entry, but they
                # survive intact inside the raw mentor dict founder_report.py consumes.
                "reason": item["why_it_matters"],
                "impact": impact_for_category(item["category"]),
                "difficulty": difficulty,
                "estimated_duration": duration,
                "first_step": item["next_step"],
                "definition_of_done": _DONE_MEANS_BY_DIMENSION.get(source_gap, _DEFAULT_DONE_MEANS),
            }
        )
    return actions


def _build_roadmap(
    funding_assessment: dict,
    is_low_confidence: bool,
    validation_plan: list[dict],
    mvp_recommendation: dict,
    primary_domain: str | None,
    top_next_actions: list[str] | None = None,
) -> list[dict]:
    # `is_ready` (readiness level alone) drives the roadmap's headline framing — a venture the
    # verdict already called "genuinely investor-ready" must never see a Day-1-30 focus labeled
    # "Discovery" underneath that verdict; that direct contradiction was Critical Fix #3's roadmap
    # bug. `has_strong_evidence` (readiness + confident positioning) is reserved for the more
    # nuanced rationale text, which legitimately wants both signals before claiming "you're ahead of
    # most founders at this stage."
    is_ready = funding_assessment.get("level") == "ready"
    has_strong_evidence = is_ready and not is_low_confidence
    domain_label = primary_domain or "your space"

    if is_ready and top_next_actions:
        # A venture with little left in `validation_plan` (mostly gate-checked
        # future_enhancement filler) still needs substantive days-1-30 activities — the same
        # broadened, forward-looking list `top_next_actions` already surfaces (Critical Fix #3).
        period_1_activities = top_next_actions[:3]
    else:
        period_1_activities = [a["method"] for a in validation_plan[:3]] or [
            "Talk to enough real prospective users to confirm the problem is real, not assumed."
        ]
    period_1 = {
        "period": "days_1_30",
        "focus": (
            "Sharpening — confirming what's already working before you scale it further"
            if is_ready
            else "Discovery — confirming the problem and the buyer before building further"
        ),
        "activities": period_1_activities,
        "rationale": (
            f"You already have solid evidence for {domain_label} — a short confirmation pass here "
            "still de-risks the next 60 days cheaply, even though you're ahead of most founders at "
            "this stage."
            if has_strong_evidence
            else "Everything you build after this depends on these answers, so validating comes first, not last."
        ),
    }
    period_2_focus = mvp_recommendation.get("minimum_workflow", "the minimum workflow for your first pilot")
    period_2 = {
        "period": "days_31_60",
        "focus": "Building the smallest real version — one workflow, one pilot",
        "activities": [
            f"Build only what days 1-30 confirmed you need: {period_2_focus}",
            "Line up the pilot itself, and decide in advance what success will actually look like.",
        ],
        "rationale": (
            "Since the evidence already points the right way, you can start building sooner than a "
            "typical early-stage venture would."
            if has_strong_evidence
            else "Hold off on building anything beyond this until days 1-30 has answered the open questions above."
        ),
    }
    period_3 = {
        "period": "days_61_90",
        "focus": "Running the pilot and letting real usage tell you what's next",
        "activities": [
            "Run the pilot with the one segment you scoped it for.",
            "Measure the specific outcome you defined, and let the result — not your instinct — decide what changes next.",
        ],
        "rationale": "This is where your assumptions meet reality — treat whatever you learn here as more reliable than anything from days 1-60.",
    }
    return [period_1, period_2, period_3]


def _build_pilot_roadmap(
    mvp_recommendation: dict, validation_plan: list[dict], venture_signals: dict, is_low_confidence: bool
) -> dict:
    """Master Product Differentiation Sprint, Phase 6 — a week-by-week refinement of the existing
    `roadmap_30_60_90`'s first period, built ENTIRELY from already-computed `mvp_recommendation` and
    `validation_plan` (never a second independent plan) — this is the same days-1-30 work, just at
    weekly granularity with explicit pilot customers, validation metrics, and a go/no-go gate."""
    if is_low_confidence:
        return {
            "weeks": [],
            "pilot_customers": "Not yet — settle on a specific target user and problem first (see mvp_recommendation).",
            "validation_metrics": "Not applicable until the positioning itself is settled.",
            "success_criteria": "Not applicable yet.",
            "pivot_conditions": "Not applicable yet.",
            "go_no_go_decision": "Too early for a go/no-go gate — the first gate is narrowing the positioning itself.",
        }

    target_user = mvp_recommendation.get("target_user", "your first target user")
    workflow = mvp_recommendation.get("minimum_workflow", "the minimum workflow")
    metric = mvp_recommendation.get("success_metric", "one clear usage or willingness-to-pay signal")
    validation_methods = [v["method"] for v in validation_plan[:2]]

    weeks = [
        {
            "week": 1,
            "focus": "Confirm the target user and problem are real",
            "activities": [f"Talk to real people who fit: {target_user}"] + validation_methods[:1],
        },
        {
            "week": 2,
            "focus": "Line up one real pilot site or customer",
            "activities": [
                "Recruit exactly one pilot site/customer — not a broad list, one real commitment.",
                (validation_methods[1] if len(validation_methods) > 1 else "Confirm the pilot site agrees on what success will look like before you build anything further."),
            ],
        },
        {
            "week": 3,
            "focus": "Deploy the minimum workflow with that one pilot",
            "activities": [f"Get {workflow} running for real with your one pilot site — not a demo.", "Start measuring from day one, not at the end of the pilot."],
        },
        {
            "week": 4,
            "focus": "Measure and decide",
            "activities": [f"Review the result against your own target for: {metric}", "Make the go/no-go call below based on the real number, not on how the pilot felt."],
        },
    ]

    return {
        "weeks": weeks,
        "pilot_customers": f"One real site or customer matching: {target_user}. Resist recruiting more than one until this one produces a real result.",
        "validation_metrics": metric,
        "success_criteria": (
            f"Before you start, write down the specific number that would make you say '{metric}' "
            "was met — a number decided in week 4 after seeing the result isn't a real bar."
        ),
        "pivot_conditions": (
            "If, by the end of week 4, the pilot site would not pay or continue without you actively "
            "pushing them to, that's a pivot signal on the problem or customer — not just a signal to "
            "try harder with the same plan."
        ),
        "go_no_go_decision": (
            "GO if the pilot site shows real, unprompted usage or a genuine willingness-to-pay signal. "
            "NO-GO (meaning: revisit the target user or problem, not necessarily abandon the venture) "
            "if the pilot site needed convincing at every step."
        ),
    }


_FORWARD_LOOKING_CATEGORIES = ("improvement_opportunity", "future_enhancement")


def _prioritize_next_actions(guidance_items: list[dict]) -> list[str]:
    """Derived from the single shared `founder_guidance_items` ranking — see
    app.agents.founder_guidance. This is deliberately the same ordering `_build_validation_plan`
    renders in more detail, not a second independently-computed ranking (Phase 1 dedup fix). Gemini
    never supplies or reorders this ranking — see app.agents.mentor_reviewer.

    A venture with few or no open validation/discovery gaps (i.e. most of what it has left is
    already-good `improvement_opportunity`/`future_enhancement` items) must still get a substantive,
    forward-looking list here — not a single generic filler line. Confidence Calibration (Critical
    Fix #3): the fewer open gaps remain, the more this list should read as execution-focused next
    moves rather than validation questions.
    """
    actionable = [item for item in guidance_items if item["category"] in _ACTIONABLE_CATEGORIES]
    actions = [item["next_step"] for item in actionable[:5]]
    if len(actions) < 3:
        forward_looking = [
            item["next_step"]
            for item in guidance_items
            if item["category"] in _FORWARD_LOOKING_CATEGORIES and item["next_step"] not in actions
        ]
        actions.extend(forward_looking[: 5 - len(actions)])
    if not actions:
        actions = [
            "Keep validating the target user and the problem itself before you build further — "
            "that foundation is what everything else here depends on."
        ]
    return actions


def _build_mentor_verdict(
    funding_assessment: dict,
    guidance_items: list[dict],
    top_next_actions: list[str],
    regulatory_context: dict | None = None,
) -> dict:
    """`strongest_signal`/`biggest_risk` are sourced entirely from `founder_guidance_items` — never
    from the raw `strengths`/`weaknesses` string lists (deprecated), and never from the Historical
    Pattern Signal / success-prediction uncertainty (see app.ml.success_predictor — that signal is
    informational only and must never become a founder-facing risk or verdict driver).

    The one exception: a high-likelihood/high-impact `regulatory_context` match (see
    app.agents.regulatory_context — Critical Fix #1, context-aware mentor judgment) outranks a
    rubric-derived risk here, since "verify your licensing before you scale" is a more consequential
    thing to hear first than "you haven't validated traction yet." This is the same
    `regulatory_context` value app.agents.strategic_opportunity folds into `strategic_risks`, so the
    Risk scene's headline and its supporting detail never contradict each other.
    """
    level = funding_assessment.get("level", "early_stage")
    # Founder Report Experience Redesign — framed the way an actual YC partner would say it out
    # loud, not as a bare status label. The distinction that matters: a weak idea and weak evidence
    # read identically as "early_stage" on the rubric, but the fix is completely different — ideas
    # improve through execution, evidence improves through customers, and conflating the two is
    # exactly what makes AI-generated feedback feel generic.
    readiness_map = {
        "ready": "You're genuinely investor-ready — the evidence here would hold up in a real "
        "diligence conversation, not just a pitch.",
        "developing": "An investor wouldn't say no outright, but wouldn't say yes yet either — a "
        "few specific gaps below are what stand between 'promising' and 'fundable.'",
        "early_stage": "If I were a YC partner, I'd pass on this today — not because the idea is "
        "weak, but because the evidence is. Ideas improve through execution; evidence improves "
        "through customers. Come back after one paying customer and a month of real usage, and this "
        "becomes a completely different conversation.",
    }
    strength_items = [item for item in guidance_items if item["category"] == "strength"]
    risk_items = [item for item in guidance_items if item["category"] in _ACTIONABLE_CATEGORIES]

    if strength_items:
        top = strength_items[0]
        strongest_signal = f"{top['title']} {top['why_it_matters']}"
    else:
        strongest_signal = (
            "You don't have a confirmed strength yet — that's expected this early, and it isn't a "
            "mark against the idea itself."
        )

    if regulatory_context and regulatory_context["likelihood"] == "high" and regulatory_context["impact"] == "high":
        biggest_risk = f"{regulatory_context['headline']} {regulatory_context['note']}"
    elif risk_items:
        top = risk_items[0]
        biggest_risk = f"{top['title']} {top['why_it_matters']}"
    else:
        biggest_risk = (
            "Nothing here rises to a real risk yet — if anything, the open question is simply how "
            "much you still have to validate."
        )

    return {
        "readiness_level": level,
        "concise_verdict": readiness_map.get(level, level),
        "strongest_signal": strongest_signal,
        "biggest_risk": biggest_risk,
        "immediate_priority": top_next_actions[0] if top_next_actions else "Define and validate exactly who your first real customer is.",
    }


def _build_evidence_and_uncertainty(
    judge_summary: dict, success_prediction: dict | None, revenue_estimate: dict | None
) -> dict:
    model_category = judge_summary.get("model_category") or {}
    venture_positioning = judge_summary.get("venture_positioning") or {}

    low_confidence_flags = []
    if venture_positioning.get("is_low_confidence"):
        low_confidence_flags.append("I'm not fully confident yet in how I've positioned this venture.")
    if model_category.get("is_uncertain"):
        low_confidence_flags.append("The underlying industry read is uncertain — treat it as a rough guess, not a settled fact.")
    if success_prediction and success_prediction.get("is_uncertain"):
        low_confidence_flags.append("The historical comparison below is too thin to lean on heavily yet.")

    missing = (revenue_estimate or {}).get("missing_assumptions") or []
    assumptions = (revenue_estimate or {}).get("assumptions") or {}
    if not revenue_estimate or not revenue_estimate.get("scenarios"):
        revenue_summary = "No revenue numbers exist for this run yet."
    elif not missing:
        revenue_summary = "Every revenue figure here came from you, not a guess."
    elif len(missing) == len(assumptions):
        revenue_summary = "Every revenue figure here is my placeholder estimate, not something you've confirmed yet."
    else:
        revenue_summary = "You're looking at a mix of founder-supplied numbers and placeholder estimates for the rest, until you confirm them."

    return {
        "model_category_caveat": (
            "There's a second, more technical industry label underneath all of this — the kind a "
            "spreadsheet would use. I've deliberately kept it out of your way; everything you've "
            "read so far uses the founder-facing read instead."
        ),
        "historical_pattern_signal_caveat": (success_prediction or {}).get(
            "disclaimer",
            "The historical comparison only draws on companies that had already raised funding — "
            "think of it as a loose reference point, not a prediction about you.",
        ),
        "low_confidence_flags": low_confidence_flags,
        "user_supplied_vs_suggested_summary": revenue_summary,
        "unresolved_questions": list(judge_summary.get("missing_evidence", [])),
    }


def _extract_venture_signals(
    funding_assessment: dict,
    market_evidence: dict,
    feature_gap: dict,
    business_model: dict | None,
    deployment_sectors: list[str] | None,
) -> dict:
    """Product Intelligence Sprint (Adaptive pass): assemble the small set of REAL, already-computed
    facts about THIS venture — never a new inference, never a new model — so pricing/GTM/feature/
    competitor intelligence can reason from the founder's own inputs first and the coarse category
    label only as a fallback. Every value here traces directly to something the founder submitted or
    a deterministic module already computed elsewhere in this same pipeline run:
      - `has_prototype`/`has_traction`: real funding-readiness evidence states (app.ml.funding_readiness).
      - `customer_type`/`startup_stage`/`known_competitors`: raw founder-submitted MarketEvidence fields.
      - `top_present_capability`/`top_recommended_capability`: app.ml.capability_library's own
        present-vs-buildable-next classification, itself matched against the founder's own description.
      - `revenue_streams`: app.agents.business_model's own output, only surfaced when it isn't a
        placeholder (i.e. the founder actually supplied a number).
    """
    breakdown = {item.get("dimension"): item for item in funding_assessment.get("breakdown", [])}
    present = feature_gap.get("present_capabilities") or []
    recommended = feature_gap.get("recommended_capabilities") or []
    revenue_streams = (business_model or {}).get("revenue_streams")
    return {
        "has_prototype": (breakdown.get("product_maturity") or {}).get("state") == "confirmed_positive",
        "has_traction": (breakdown.get("traction") or {}).get("state") == "confirmed_positive",
        "customer_type": market_evidence.get("customer_type"),
        "startup_stage": market_evidence.get("startup_stage"),
        "known_competitors": market_evidence.get("known_competitors") or [],
        "deployment_sectors": deployment_sectors or [],
        "top_present_capability": present[0] if present else None,
        "top_recommended_capability": recommended[0] if recommended else None,
        "revenue_streams": revenue_streams if revenue_streams and "placeholder" not in str(revenue_streams).lower() else None,
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

    venture_signals = _extract_venture_signals(
        funding_assessment, market_evidence, feature_gap, business_model, venture_positioning.get("deployment_sectors")
    )

    # Venture Retrieval (ML Differentiator Sprint): semantic nearest-neighbor search over the real
    # industry-classifier corpus — off by default (app.core.config.Settings.enable_venture_retrieval)
    # and always degrades to {"available": False} without raising, so this never affects behavior
    # unless explicitly enabled. See app.ml.venture_retrieval for the full anti-fabrication framing.
    # Master Startup Corpus Expansion Sprint, Phase 6 — reuses the already-computed, frozen
    # industry classifier's own predicted label (never a new model) as the reranking signal, only
    # when the classifier itself wasn't flagged uncertain about that prediction.
    model_category_for_rerank = judge_summary.get("model_category") or {}
    known_industry_for_rerank = (
        model_category_for_rerank.get("label") if not model_category_for_rerank.get("is_uncertain") else None
    )
    venture_retrieval = retrieve_similar_ventures(startup_description, known_industry=known_industry_for_rerank)
    venture_signals["retrieved_ventures"] = venture_retrieval.get("neighbors", [])
    venture_signals["comparative_intelligence"] = venture_retrieval.get("comparative_intelligence")

    # Startup Domain Intelligence Sprint: general, category-level startup-domain reference
    # knowledge — reused by pricing/GTM/investor-intelligence/benchmark below, never a second
    # independent recommendation engine. See app.agents.industry_knowledge_packs.
    industry_knowledge_pack = get_industry_knowledge_pack(
        primary_domain, (judge_summary.get("model_category") or {}).get("label"),
        venture_positioning.get("deployment_sectors"), startup_description,
    )

    pricing_intelligence = build_pricing_intelligence(
        venture_positioning, judge_summary.get("model_category"), market_evidence, startup_description,
        venture_signals=venture_signals,
    )
    go_to_market_intelligence = build_go_to_market_intelligence(
        primary_domain,
        (judge_summary.get("model_category") or {}).get("label"),
        venture_positioning.get("deployment_sectors"),
        funding_assessment.get("level", "early_stage"),
        startup_description,
        venture_signals=venture_signals,
        knowledge_pack=industry_knowledge_pack,
    )
    _differentiation_state = next(
        (
            item.get("state")
            for item in funding_assessment.get("breakdown", [])
            if item.get("dimension") == "competitive_differentiation"
        ),
        None,
    )
    feature_intelligence = build_feature_intelligence(
        primary_domain,
        (judge_summary.get("model_category") or {}).get("label"),
        venture_positioning.get("deployment_sectors"),
        differentiation_is_weak=_differentiation_state in ("confirmed_negative", "not_sure_yet", None),
        startup_description=startup_description,
        venture_signals=venture_signals,
    )
    competitor_intelligence = build_competitor_intelligence(
        primary_domain,
        (judge_summary.get("model_category") or {}).get("label"),
        venture_positioning.get("deployment_sectors"),
        has_named_competitors=bool((competitor_analysis or {}).get("verified_competitors")),
        startup_description=startup_description,
        venture_signals=venture_signals,
    )
    mvp_recommendation = _build_mvp_recommendation(primary_domain, feature_gap, market_evidence, is_low_confidence)
    validation_plan = _build_validation_plan(founder_guidance_items)
    top_next_actions = _prioritize_next_actions(founder_guidance_items)
    roadmap = _build_roadmap(
        funding_assessment, is_low_confidence, validation_plan, mvp_recommendation, primary_domain, top_next_actions
    )
    pilot_roadmap = _build_pilot_roadmap(mvp_recommendation, validation_plan, venture_signals, is_low_confidence)
    regulatory_context = classify_regulatory_context(
        startup_description, primary_domain, venture_positioning.get("deployment_sectors")
    )
    mentor_verdict = _build_mentor_verdict(funding_assessment, founder_guidance_items, top_next_actions, regulatory_context)
    evidence_and_uncertainty = _build_evidence_and_uncertainty(judge_summary, success_prediction, revenue_estimate)

    # Master Product Differentiation Sprint: new founder-intelligence lenses, all deterministic and
    # built entirely from signals already computed above — see app.agents.founder_intelligence's
    # module docstring for why none of this is a new reasoning engine.
    critical_blind_spots = build_critical_blind_spots(funding_assessment, venture_signals, go_to_market_intelligence)
    investor_questions = build_investor_questions(funding_assessment, venture_signals, competitor_analysis)
    founder_challenge_mode = build_founder_challenge_mode(funding_assessment)
    moat_intelligence = build_moat_intelligence(
        startup_description, venture_signals, primary_domain, venture_positioning.get("deployment_sectors")
    )
    feature_gap_vs_market = build_feature_gap_vs_market(feature_gap, venture_signals)
    funding_stage_ladder = build_funding_stage_ladder(funding_assessment, venture_signals)
    founder_iq_report = build_founder_iq_report(funding_assessment)

    # Startup Domain Intelligence Sprint: reuses venture_retrieval + industry_knowledge_pack
    # (never a new retrieval/classifier) to answer "compared to what?", and reuses
    # investor_questions (already computed above, never re-derived) for investor intelligence.
    startup_benchmark = build_startup_benchmark(venture_retrieval, industry_knowledge_pack)
    investor_intelligence = build_investor_intelligence(funding_assessment, investor_questions, industry_knowledge_pack)

    idea_understanding = _build_idea_understanding(startup_name, startup_description, market_evidence, venture_positioning)
    venture_positioning_text = (
        f"{venture_positioning.get('primary_domain', 'Unresolved')}"
        + (
            f" — also worth watching: {', '.join(venture_positioning.get('secondary_domains', []))}"
            if venture_positioning.get("secondary_domains")
            else ""
        )
        + (
            " I'd treat this as a working guess rather than a settled identity for now."
            if is_low_confidence
            else "."
        )
    )

    mentor_result = {
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
        "pricing_intelligence": pricing_intelligence,
        "go_to_market_intelligence": go_to_market_intelligence,
        "feature_intelligence": feature_intelligence,
        "competitor_intelligence": competitor_intelligence,
        "venture_retrieval": venture_retrieval,
        "mvp_recommendation": mvp_recommendation,
        "validation_plan": validation_plan,
        "roadmap_30_60_90": roadmap,
        "pilot_roadmap": pilot_roadmap,
        "top_next_actions": top_next_actions,
        "mentor_verdict": mentor_verdict,
        "evidence_and_uncertainty": evidence_and_uncertainty,
        "critical_blind_spots": critical_blind_spots,
        "investor_questions": investor_questions,
        "founder_challenge_mode": founder_challenge_mode,
        "moat_intelligence": moat_intelligence,
        "feature_gap_vs_market": feature_gap_vs_market,
        "funding_stage_ladder": funding_stage_ladder,
        "founder_iq_report": founder_iq_report,
        "industry_knowledge_pack": industry_knowledge_pack,
        "startup_benchmark": startup_benchmark,
        "investor_intelligence": investor_intelligence,
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
            "pricing_intelligence": "deterministic heuristic (domain comparator + disclosed currency/market adjustment) — see app.agents.pricing_intelligence; never live market data or a cited study",
            "go_to_market_intelligence": "category-level deterministic go-to-market pattern — see app.agents.go_to_market_intelligence; never a claim about this venture's actual customers",
            "feature_intelligence": "category-level deterministic feature/differentiation ideas — see app.agents.feature_intelligence; concrete starting ideas, never a claim about this venture's existing capabilities",
            "competitor_intelligence": "category-level deterministic switching-behavior/how-to-win analysis — see app.agents.competitor_intelligence; never a claim about a specific real competitor",
            "venture_retrieval": "semantic nearest-neighbor search over a real historical company dataset — see app.ml.venture_retrieval; retrieved companies are real but NOT verified as current competitors, may no longer operate, and are shown as historical pattern reference only",
            "mvp_recommendation": "derived from feature_gap_analysis + market_evidence",
            "validation_plan": "derived from founder_guidance_items (actionable categories only)",
            "roadmap_30_60_90": "derived from the validation plan, the funding-readiness level, and the MVP recommendation",
            "pilot_roadmap": "weekly refinement of roadmap_30_60_90's first period, derived from mvp_recommendation + validation_plan — see app.agents.mentor_synthesis._build_pilot_roadmap",
            "top_next_actions": "derived from founder_guidance_items — the same single priority order as validation_plan, never Gemini free text",
            "mentor_verdict": "derived from funding_assessment.level and founder_guidance_items",
            "evidence_and_uncertainty": "derived from model_category, venture_positioning, success_prediction, revenue_estimate",
            "critical_blind_spots": "re-presents funding_assessment.breakdown's own gap-state dimensions as founder-facing blind spots — see app.agents.founder_intelligence",
            "investor_questions": "templated from real rubric gap dimensions and venture_signals fields — see app.agents.founder_intelligence",
            "founder_challenge_mode": "templated objections from the same rubric gap dimensions, paired with the concrete next step to overcome each — see app.agents.founder_intelligence",
            "moat_intelligence": "keyword/signal-based moat-type check against the founder's own description, plus app.agents.regulatory_context reused for the regulation dimension — see app.agents.founder_intelligence",
            "feature_gap_vs_market": "cross-references capability_library's recommended_capabilities against venture_retrieval's comparative_intelligence common_terminology — unavailable unless venture retrieval is enabled",
            "funding_stage_ladder": "derived from venture_signals (has_prototype/has_traction/revenue_streams) and funding_assessment.level — see app.agents.founder_intelligence",
            "founder_iq_report": "re-scores the founder's OWN funding-readiness answers for demonstrated preparation, not venture quality — see app.agents.founder_intelligence",
            "industry_knowledge_pack": "general, category-level startup-domain reference knowledge (qualitative, no invented statistics/prices/named companies) — see app.agents.industry_knowledge_packs; feeds go_to_market_intelligence/startup_benchmark/investor_intelligence below rather than acting as a second recommendation engine",
            "startup_benchmark": "answers 'compared to what?' by combining real retrieved-venture evidence (industry positioning only) with industry_knowledge_pack for every other dimension, each explicitly labeled which — see app.agents.startup_benchmark",
            "investor_intelligence": "reuses investor_questions (not re-derived) for objections, funding_assessment.breakdown for real milestones, and industry_knowledge_pack for general success/failure patterns — see app.agents.founder_intelligence.build_investor_intelligence",
            "founder_report": "composed entirely from the sections above — see app.agents.founder_report; adds no new facts, only presentation and per-item evidence/inference/ai_recommendation/market_assumption/experiment_suggestion tagging",
            "consistency_audit": "audits the assembled founder_report for invalid tags, near-duplicate sentences, generic boilerplate, unsupported claims, and contradictions — see app.agents.consistency_audit; never rewrites content, only reports findings",
            "knowledge_audit": "classifies every tagged founder_report item's knowledge source (retrieved evidence / deterministic reasoning / AI reasoning / startup knowledge / unsupported generic advice) — see app.agents.knowledge_audit; never rewrites content, only reports findings",
        },
    }
    mentor_result["explainability_index"] = build_explainability_index(
        mentor_result["source_attribution"], venture_retrieval.get("available", False)
    )
    mentor_result["founder_report"] = build_founder_report(
        startup_name, judge_summary, mentor_result, funding_assessment, revenue_estimate, success_prediction
    )
    mentor_result["consistency_audit"] = audit_founder_report(mentor_result["founder_report"])
    mentor_result["knowledge_audit"] = audit_knowledge_sources(
        mentor_result["founder_report"], consistency_audit_result=mentor_result["consistency_audit"]
    )
    return mentor_result
