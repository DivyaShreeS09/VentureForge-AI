"""Founder Intelligence (Master Product Differentiation Sprint).

Deterministic, purely additive — invents no new facts and builds no new reasoning engine. Every
function here is a new *lens* over signals this pipeline already computes: the funding-readiness
rubric's per-dimension evidence states (app.ml.funding_readiness), `venture_signals` (already
extracted in app.agents.mentor_synthesis from real founder-submitted fields and other agents'
outputs), `founder_guidance_items` (app.agents.founder_guidance's single prioritized ranking), and
`regulatory_context` (app.agents.regulatory_context). Nothing below re-scores the venture or
re-derives evidence states independently — it re-presents the same underlying facts through five
new frames a founder actually needs: what they haven't thought about yet (blind spots), what a
real evaluator would ask (investor questions), the strongest case against the venture (challenge
mode), how defensible it is (moat intelligence), and how well the founder understands their own
venture (founder IQ) — never the venture's quality itself.
"""

from __future__ import annotations

from app.agents.regulatory_context import classify_regulatory_context

FOUNDER_INTELLIGENCE_VERSION = "v1"

# Maps each funding-readiness rubric dimension (app.ml.funding_readiness.DIMENSIONS) onto the
# blind-spot category it represents. Not a new taxonomy invented per-venture — a fixed, versioned
# relabeling of the same 8 dimensions every venture is already scored against.
_DIMENSION_TO_BLIND_SPOT_TYPE = {
    "problem_clarity": "missing_assumption",
    "customer_pain_evidence": "missing_customer_evidence",
    "market_size_evidence": "missing_customer_evidence",
    "product_maturity": "missing_technical_risk",
    "traction": "missing_business_risk",
    "revenue_model_clarity": "missing_pricing_evidence",
    "team_completeness": "missing_business_risk",
    "competitive_differentiation": "missing_business_risk",
}

_GAP_STATES = ("not_sure_yet", "confirmed_negative")

# One distinct, dimension-specific reason a real evaluator cares about each gap — never a single
# reused template, since the same generic sentence repeated across every dimension is exactly the
# genericness app.agents.consistency_audit checks for.
_WHY_INVESTORS_CARE = {
    "problem_clarity": "A vague problem statement is usually the first thing that stalls a pitch — an evaluator can't assess a solution to a problem they can't picture concretely.",
    "customer_pain_evidence": "Evaluators discount claims about pain that aren't backed by real conversations — this is usually the very first thing they ask you to substantiate.",
    "market_size_evidence": "Without a sizing estimate, an evaluator can't tell whether this is a venture-scale opportunity or a lifestyle business — that distinction drives the entire funding conversation.",
    "product_maturity": "Evaluators weight what exists today far more than what's planned — an idea-only stage changes the entire conversation from 'how big' to 'is this real yet.'",
    "traction": "Traction is usually the single strongest signal an evaluator looks for — its absence means every other claim in the pitch is still unproven.",
    "revenue_model_clarity": "An unclear revenue model means an evaluator can't model the business at all — this is often the difference between 'interesting idea' and 'investable business.'",
    "team_completeness": "Evaluators bet heavily on the team's ability to execute — a coverage gap here raises real doubt about execution speed, independent of how good the idea is.",
    "competitive_differentiation": "Without stated differentiation, an evaluator can't tell why this wins versus an incumbent or a well-funded copycat — that's usually the second question after 'how big is the market.'",
}


def build_critical_blind_spots(
    funding_assessment: dict, venture_signals: dict, go_to_market_intelligence: dict | None
) -> list[dict]:
    """Phase 1 — walks the SAME funding-readiness breakdown already scored (never re-evaluates
    it), surfacing every dimension still in a gap state as a named blind-spot category, plus one
    structural GTM check that dimension set doesn't cover on its own."""
    blind_spots: list[dict] = []
    for item in funding_assessment.get("breakdown", []):
        if item.get("state") in _GAP_STATES:
            spot_type = _DIMENSION_TO_BLIND_SPOT_TYPE.get(item["dimension"], "missing_assumption")
            confirmed = item["state"] == "confirmed_negative"
            blind_spots.append(
                {
                    "blind_spot_type": spot_type,
                    "dimension": item["dimension"],
                    "title": item["label"],
                    "detail": (
                        f"You've confirmed this doesn't exist yet: {item['scale_description']}."
                        if confirmed
                        else f"You haven't answered this yet: {item['scale_description']}."
                    ),
                    "why_investors_care": _WHY_INVESTORS_CARE.get(
                        item["dimension"],
                        f"An unaddressed '{item['label']}' gap is usually one of the first things a serious evaluator checks.",
                    ),
                }
            )
    if not (venture_signals.get("known_competitors") or []):
        blind_spots.append(
            {
                "blind_spot_type": "missing_business_risk",
                "dimension": "named_competitors",
                "title": "No competitor named",
                "detail": "You haven't named a single alternative your target customer might already use — not even an informal one (a spreadsheet, a manual process, a bigger incumbent).",
                "why_investors_care": "Every real market has an alternative, even if it's 'doing nothing.' Not naming one reads as not having looked, which is a research gap, not a market-strength signal.",
            }
        )
    validation_roadmap = (go_to_market_intelligence or {}).get("validation_roadmap") or []
    if validation_roadmap:
        blind_spots.append(
            {
                "blind_spot_type": "missing_gtm_evidence",
                "dimension": "go_to_market_validation",
                "title": "Go-to-market is still unvalidated",
                "detail": f"The concrete first step you haven't taken yet: {validation_roadmap[0]}",
                "why_investors_care": "\"How will your first 20 customers actually hear about this\" is one of the most common early questions — an unvalidated GTM plan is a real gap, not a formality.",
            }
        )
    return blind_spots


# Each entry: (rubric dimension it's grounded in, persona, question template using {field}
# placeholders resolved from real venture_signals/market_evidence — never invented facts).
_INVESTOR_QUESTION_TEMPLATES = [
    (
        "revenue_model_clarity",
        "YC Partner",
        "You say {customer_type} will pay for this — why won't they just keep using {alternative}?",
    ),
    (
        "traction",
        "Accelerator Judge",
        "You have {traction_state} traction so far — what specifically would you need to see in the next 90 days to know this is real, versus a false start?",
    ),
    (
        "competitive_differentiation",
        "VC",
        "If {top_competitor} decided to build this tomorrow, what stops them from doing it faster than you, given their existing distribution?",
    ),
    (
        "team_completeness",
        "Angel Investor",
        "Your team currently covers {team_state} — who fills the gap, and what happens to execution speed until they do?",
    ),
    (
        "market_size_evidence",
        "VC",
        "You haven't sized the market yet — is this a $10M opportunity or a $1B one, and how would you actually find out?",
    ),
]


def build_investor_questions(
    funding_assessment: dict, venture_signals: dict, competitor_analysis: dict | None
) -> list[dict]:
    """Phase 2 — every question is templated from a real rubric dimension's actual state plus
    real founder-submitted fields (customer_type, known_competitors) where available; falls back to
    an honest placeholder phrase (never an invented competitor/customer name) when the founder
    hasn't supplied that field."""
    breakdown = {item["dimension"]: item for item in funding_assessment.get("breakdown", [])}
    customer_type = venture_signals.get("customer_type") or "your target customer"
    competitors = venture_signals.get("known_competitors") or []
    top_competitor = competitors[0] if competitors else "a well-funded incumbent"
    manual_alt = ((competitor_analysis or {}).get("manual_process_alternative") or {}).get("description")
    alternative = manual_alt or "whatever they use today"

    questions: list[dict] = []
    for dimension, persona, template in _INVESTOR_QUESTION_TEMPLATES:
        item = breakdown.get(dimension)
        if not item or item["state"] not in _GAP_STATES:
            continue
        traction_state = item["scale_description"].lower() if dimension == "traction" else None
        team_state = item["scale_description"].lower() if dimension == "team_completeness" else None
        question = template.format(
            customer_type=customer_type,
            alternative=alternative,
            traction_state=traction_state or "",
            top_competitor=top_competitor,
            team_state=team_state or "",
        )
        questions.append(
            {
                "dimension": dimension,
                "persona": persona,
                "question": question,
                "grounded_in": f"Your own '{item['label']}' answer: {item['scale_description']}",
            }
        )
    if not questions:
        questions.append(
            {
                "dimension": None,
                "persona": "YC Partner",
                "question": "Every dimension I'd normally push on already has a real answer from you — so the fair question becomes: what would make you doubt this yourself?",
                "grounded_in": "No open funding-readiness gaps remain in the current submission.",
            }
        )
    return questions


# (dimension, objection_category, "objection" template, "how_to_overcome" template)
_CHALLENGE_TEMPLATES = [
    ("market_size_evidence", "market_objection", "Nobody has shown this market is big enough to matter.", "Size the market with even a rough bottom-up estimate (target customers x price) — a defensible rough number beats an unsupported claim."),
    ("product_maturity", "product_objection", "There's no working product yet, only a description of an idea.", "Build the smallest possible version of the single core workflow and get one real person to use it, even manually behind the scenes."),
    ("customer_pain_evidence", "customer_objection", "There's no evidence any real person has this pain badly enough to pay for a fix.", "Talk to 5 people who fit the target profile and ask what they currently do about this problem today — their answer is the real evidence."),
    ("revenue_model_clarity", "pricing_objection", "There's no defined pricing model, so it's unclear anyone would actually pay, or how much.", "Propose one specific price to 3 real prospective customers and see if they flinch, agree, or negotiate — that reaction is real pricing signal."),
    ("team_completeness", "execution_objection", "The team doesn't yet cover the core skills this venture needs to execute.", "Name the single most critical missing skill and either recruit for it or find an advisor who covers that gap credibly."),
    ("competitive_differentiation", "moat_objection", "There's no clear reason a well-resourced competitor couldn't copy this.", "Identify the one thing that gets harder to copy over time (data, workflow lock-in, a relationship) and invest specifically in that, not in features generally."),
    ("traction", "scaling_objection", "With no real traction yet, there's nothing to suggest this scales beyond a single pilot.", "Prove it works in one pilot site first, with one clear metric, before making any claim about scaling further."),
]


def build_founder_challenge_mode(funding_assessment: dict) -> list[dict]:
    """Phase 3 — argues against the venture using the same rubric gap states, then points back to
    the same concrete next step a real evaluator would expect, never a generic "improve this"."""
    breakdown = {item["dimension"]: item for item in funding_assessment.get("breakdown", [])}
    objections: list[dict] = []
    for dimension, category, objection, overcome in _CHALLENGE_TEMPLATES:
        item = breakdown.get(dimension)
        if not item or item["state"] not in _GAP_STATES:
            continue
        objections.append(
            {
                "dimension": dimension,
                "objection_category": category,
                "objection": objection,
                "grounded_in": f"Your own '{item['label']}' answer: {item['scale_description']}",
                "how_to_overcome": overcome,
            }
        )
    if not objections:
        objections.append(
            {
                "dimension": None,
                "objection_category": "execution_objection",
                "objection": "Every dimension I'd normally attack already has a real answer — the toughest honest objection left is execution risk: plans on paper are cheap, consistent execution is what's actually unproven.",
                "grounded_in": "No open funding-readiness gaps remain in the current submission.",
                "how_to_overcome": "Keep the same discipline that got these answers this far — the risk from here is losing focus, not lacking a plan.",
            }
        )
    return objections


# Each moat dimension: (id, label, keyword signal check against the description, why-template).
_MOAT_KEYWORDS = {
    "data_moat": ("data", "dataset", "historical data", "proprietary data", "user data", "training data"),
    "network_effects": ("marketplace", "two-sided", "multi-sided", "community", "network", "peer to peer", "peer-to-peer"),
    "switching_costs": ("integration", "workflow", "api", "existing system", "embedded", "records"),
    "technology": ("proprietary", "patent", "algorithm", "model", "ai-powered", "machine learning"),
    "distribution": ("partnership", "channel", "distributor", "existing customers", "sales team"),
    "community": ("community", "user-generated", "creators", "members"),
}

# What each no-signal moat would concretely require, so the "not yet established" basis is a
# distinct, actionable statement per moat rather than one repeated generic sentence.
_MOAT_NOT_ESTABLISHED_BASIS = {
    "data_moat": "Nothing in your description suggests you're accumulating proprietary data over time — that data would need to compound with usage to become a real moat, not just be collected.",
    "network_effects": "Nothing in your description suggests value grows as more people join (a marketplace, community, or multi-sided dynamic) — without that, this isn't a realistic moat yet.",
    "switching_costs": "Nothing in your description suggests customers would have real switching friction (integrations, embedded workflows) once they adopt this — right now, switching away would likely be easy.",
    "technology": "Nothing in your description suggests a proprietary technical edge (a novel algorithm, model, or patent) — without one, competitors can plausibly replicate the product itself.",
    "distribution": "Nothing in your description suggests you have a distribution advantage (an existing channel, partnership, or sales relationship) that a competitor would have to rebuild from scratch.",
    "community": "Nothing in your description suggests a community or user-generated dynamic that would make the product harder to leave once people are invested in it.",
}


def build_moat_intelligence(
    startup_description: str, venture_signals: dict, primary_domain: str | None, deployment_sectors: list[str] | None
) -> dict:
    """Phase 4 — ranks moat TYPES by whether real, checkable signal exists for each, reusing
    app.agents.regulatory_context directly for the regulation dimension rather than re-implementing
    a second keyword classifier. Never assigns a fabricated numeric score — each moat gets one of
    three disclosed-basis tiers (`signal_found`, `not_yet_established`, `not_applicable`), each with
    the exact keyword or signal it was checked against."""
    text = (startup_description or "").lower()
    moats: list[dict] = []

    for moat_id, keywords in _MOAT_KEYWORDS.items():
        matched = [k for k in keywords if k in text]
        moats.append(
            {
                "moat_type": moat_id,
                "tier": "signal_found" if matched else "not_yet_established",
                "basis": (
                    f"Your description mentions: {', '.join(matched)}."
                    if matched
                    else _MOAT_NOT_ESTABLISHED_BASIS[moat_id]
                ),
            }
        )

    has_traction = bool(venture_signals.get("has_traction"))
    moats.append(
        {
            "moat_type": "brand",
            "tier": "signal_found" if has_traction else "not_yet_established",
            "basis": (
                "You've confirmed real traction, which is the earliest real precondition for brand value — brand itself still has to be earned over time."
                if has_traction
                else "No confirmed traction yet — brand isn't a realistic moat this early; it's earned through traction, not claimed in advance."
            ),
        }
    )

    regulatory = classify_regulatory_context(startup_description, primary_domain, deployment_sectors)
    if regulatory and regulatory.get("likelihood") in ("medium", "high"):
        moats.append(
            {
                "moat_type": "regulation",
                "tier": "signal_found",
                "basis": f"{regulatory['headline']} A real compliance/licensing bar can be a genuine moat against less-careful competitors, not just a cost.",
            }
        )
    else:
        moats.append(
            {
                "moat_type": "regulation",
                "tier": "not_applicable",
                "basis": "Nothing in your description touches a regulated category strongly enough for compliance itself to function as a moat.",
            }
        )

    rank_order = {"signal_found": 0, "not_yet_established": 1, "not_applicable": 2}
    moats.sort(key=lambda m: rank_order[m["tier"]])

    return {
        "founder_intelligence_version": FOUNDER_INTELLIGENCE_VERSION,
        "moats": moats,
        "disclaimer": (
            "Each moat is checked against what you actually wrote, not estimated — 'signal_found' "
            "means the described concept exists in your own words, not that the moat is already "
            "strong or proven. Nothing here is a fabricated defensibility score."
        ),
    }


# Maps each rubric dimension onto the Founder-IQ category(ies) it evidences understanding of.
_DIMENSION_TO_IQ_CATEGORY = {
    "problem_clarity": "business",
    "customer_pain_evidence": "customers",
    "market_size_evidence": "customers",
    "product_maturity": "technology",
    "traction": "execution",
    "revenue_model_clarity": "pricing",
    "team_completeness": "execution",
    "competitive_differentiation": "competition",
}

_IQ_CATEGORIES = ("customers", "pricing", "competition", "business", "technology", "execution", "fundraising")


def build_founder_iq_report(funding_assessment: dict) -> dict:
    """Phase 8 — scores the FOUNDER's demonstrated preparation, not the venture. Reuses the exact
    same rubric evidence states already scored; a `confirmed_negative` answer scores as an
    "acknowledged gap" (honest, not a knowledge gap), while `not_sure_yet` scores as a genuine
    knowledge gap — the same distinction app.ml.funding_readiness already draws, just relabeled
    for what it says about founder preparation rather than venture readiness."""
    breakdown = {item["dimension"]: item for item in funding_assessment.get("breakdown", [])}
    category_items: dict[str, list[dict]] = {c: [] for c in _IQ_CATEGORIES}
    for dimension, category in _DIMENSION_TO_IQ_CATEGORY.items():
        item = breakdown.get(dimension)
        if item:
            category_items[category].append(item)

    category_scores: dict[str, dict] = {}
    for category in _IQ_CATEGORIES:
        items = category_items.get(category) or []
        if category == "fundraising":
            level = funding_assessment.get("level", "early_stage")
            label = {
                "ready": "strong understanding",
                "developing": "developing understanding",
                "early_stage": "early-stage understanding",
            }.get(level, "early-stage understanding")
            category_scores[category] = {
                "understanding_level": label,
                "basis": f"Derived from your overall funding-readiness level ({level}), the closest real proxy for fundraising preparation this pipeline has.",
            }
            continue
        if not items:
            category_scores[category] = {"understanding_level": "not assessed", "basis": "No rubric dimension maps to this category for this run."}
            continue
        states = [i["state"] for i in items]
        severities = [i.get("raw_score") for i in items if i.get("raw_score") is not None]
        dimension_labels = ", ".join(i["label"] for i in items)
        gap_labels = ", ".join(i["label"] for i in items if i["state"] == "not_sure_yet")
        negative_labels = ", ".join(i["label"] for i in items if i["state"] == "confirmed_negative")
        if "not_sure_yet" in states:
            level = "knowledge gap — not yet thought through"
            basis = f"You marked '{gap_labels}' as not sure yet — a real gap to close in this area, not a judgment on you."
        elif "confirmed_negative" in states:
            level = "acknowledged gap — honestly flagged, not unknown to you"
            basis = f"You confirmed '{negative_labels}' genuinely doesn't exist yet — an honest answer, distinct from not having thought about it."
        elif severities and max(severities) == 2:
            level = "strong understanding"
            basis = f"Your own answer on '{dimension_labels}' reflects specific, well-evidenced thinking, not a rough guess."
        else:
            level = "developing understanding"
            basis = f"You have a real starting answer on '{dimension_labels}', worth sharpening with more specific evidence."
        category_scores[category] = {"understanding_level": level, "basis": basis}

    knowledge_gaps = [c for c, s in category_scores.items() if "knowledge gap" in s["understanding_level"]]

    # Founder Report Experience Redesign — a founder should read "you think primarily like an
    # engineer" and recognize themselves, not just seven independent category labels. Built
    # entirely from the category_scores already computed above (technical vs. commercial
    # categories), never a new assessment.
    _TECHNICAL_CATEGORIES = ("technology", "execution")
    _COMMERCIAL_CATEGORIES = ("customers", "pricing", "competition")
    technical_strong = any(category_scores.get(c, {}).get("understanding_level") == "strong understanding" for c in _TECHNICAL_CATEGORIES)
    commercial_gaps = [c for c in _COMMERCIAL_CATEGORIES if c in knowledge_gaps]
    if technical_strong and len(commercial_gaps) >= 2:
        dominant_thinking_pattern = (
            "Your answers read like an engineer's: strong on implementation and technical planning, "
            "with a real prototype already in hand. Commercial thinking — pricing experiments, "
            "distribution, sales planning, customer interviews — is still developing by comparison. "
            "The highest-leverage upgrade from here isn't another technical skill; it's customer "
            f"discovery, starting with {' and '.join(gap.replace('_', ' ') for gap in commercial_gaps)}."
        )
    elif not knowledge_gaps:
        dominant_thinking_pattern = (
            "Your answers show real preparation across both the technical and commercial sides — "
            "the open question from here is execution discipline, not which side to learn next."
        )
    else:
        dominant_thinking_pattern = None

    return {
        "founder_intelligence_version": FOUNDER_INTELLIGENCE_VERSION,
        "category_scores": category_scores,
        "knowledge_gaps": knowledge_gaps,
        "dominant_thinking_pattern": dominant_thinking_pattern,
        "disclaimer": (
            "This scores how well-prepared your OWN answers are, not whether the venture itself is "
            "good — it reuses the exact same funding-readiness answers you already gave, viewed "
            "through what they say about founder preparation instead of venture readiness."
        ),
    }


def build_feature_gap_vs_market(feature_gap: dict, venture_signals: dict) -> dict:
    """Phase 5 — cross-references app.ml.capability_library's already-computed
    `recommended_capabilities` (buildable-next, per THIS venture's own description) against
    app.ml.venture_retrieval's already-computed `comparative_intelligence.common_terminology`
    (real shared words across real retrieved similar ventures' own descriptions). Surfaces only the
    intersection — a recommended capability whose own matching concepts appear in what similar real
    ventures actually say about themselves — never a fabricated "competitors have this" claim, and
    never anything when retrieval is unavailable (matches app.ml.venture_retrieval's off-by-default,
    always-degrades-gracefully contract)."""
    comparative = venture_signals.get("comparative_intelligence") or {}
    if not comparative.get("available"):
        return {
            "founder_intelligence_version": FOUNDER_INTELLIGENCE_VERSION,
            "available": False,
            "reason": "Venture retrieval is not enabled for this run, or no similar ventures were found — this section only ever surfaces real, retrieved evidence, never a guess.",
            "gaps": [],
        }
    terminology = (comparative.get("common_terminology") or {})
    if not terminology.get("available"):
        return {
            "founder_intelligence_version": FOUNDER_INTELLIGENCE_VERSION,
            "available": False,
            "reason": terminology.get("reason", "No common terminology could be established across the retrieved ventures."),
            "gaps": [],
        }
    shared_terms = {t["term"].lower() for t in terminology.get("terms", [])}
    # Reuses app.ml.capability_library's own importance tier as the priority signal (Phase 4) —
    # never a new score. "core" capabilities are prerequisite-level; "advanced" ones are
    # differentiating but non-blocking, which is exactly what determines business impact here too.
    _IMPACT_BY_IMPORTANCE = {
        "core": "high — this is prerequisite-level functionality for the category, not a nice-to-have",
        "useful": "medium — strengthens the product but isn't a blocking prerequisite",
        "advanced": "differentiating — valuable once the core workflow is proven, not before",
    }
    _PRIORITY_RANK = {"core": 0, "useful": 1, "advanced": 2}
    gaps = []
    for cap in feature_gap.get("recommended_capabilities", []):
        matches = [c for c in cap.get("matching_concepts", []) if any(c in term or term in c for term in shared_terms)]
        if matches:
            gaps.append(
                {
                    "capability": cap["label"],
                    "why_it_matters": cap["reason"],
                    "evidence": f"Ventures similar to yours commonly use related language ({', '.join(sorted(set(matches))[:3])}) in their own descriptions — not proof they built it, but a real signal this concept is common in this space.",
                    "validation_question": cap["validation_question"],
                    "priority_rank": cap.get("importance", "useful"),
                    "business_impact": _IMPACT_BY_IMPORTANCE.get(cap.get("importance"), "unclear"),
                }
            )
    gaps.sort(key=lambda g: _PRIORITY_RANK.get(g["priority_rank"], 3))
    return {
        "founder_intelligence_version": FOUNDER_INTELLIGENCE_VERSION,
        "available": True,
        "gaps": gaps,
        "provenance": terminology.get("provenance"),
        "disclaimer": (
            "This dataset has no feature-level data — 'evidence' above means shared descriptive "
            "language across similar real ventures, never a claim about what any specific "
            "competitor actually built."
        ),
    }


# Stage ladder in order; each stage's REQUIREMENT is grounded in a real venture_signal, never
# invented. This mirrors, not replaces, funding_assessment.level — it adds the *sequence* framing
# ("what specifically changes to reach the next stage") that a bare level label doesn't carry.
_STAGE_ORDER = ("idea", "prototype", "pilot", "revenue", "seed", "series_a")


def build_funding_stage_ladder(funding_assessment: dict, venture_signals: dict) -> dict:
    """Phase 7 — determines the current real stage from already-computed venture_signals
    (has_prototype, has_traction, revenue_streams) and funding_assessment.level, then states what
    would concretely need to be true to reach the next stage — never a generic "grow more"."""
    has_prototype = bool(venture_signals.get("has_prototype"))
    has_traction = bool(venture_signals.get("has_traction"))
    has_revenue = bool(venture_signals.get("revenue_streams"))
    level = funding_assessment.get("level", "early_stage")

    if has_revenue and has_traction and level == "ready":
        current_stage = "revenue"
    elif has_traction:
        current_stage = "pilot"
    elif has_prototype:
        current_stage = "prototype"
    else:
        current_stage = "idea"

    requirements = {
        "idea": "Build a working prototype of the single narrowest version of the core workflow.",
        "prototype": "Get one real pilot user or site actually using it and confirm real (not hypothetical) engagement.",
        "pilot": "Convert at least one pilot into a paying relationship, however small, to confirm willingness to pay.",
        "revenue": "Show the revenue is repeatable across more than one customer, not a single one-off deal.",
        "seed": "Demonstrate consistent, growing usage/revenue with a clear, defensible reason customers keep choosing you over alternatives.",
        "series_a": "This stage is beyond what this rubric evaluates — it typically requires demonstrated, scalable unit economics.",
    }
    current_idx = _STAGE_ORDER.index(current_stage)
    next_stage = _STAGE_ORDER[current_idx + 1] if current_idx + 1 < len(_STAGE_ORDER) else None

    return {
        "founder_intelligence_version": FOUNDER_INTELLIGENCE_VERSION,
        "stages": list(_STAGE_ORDER),
        "current_stage": current_stage,
        "next_stage": next_stage,
        "what_moves_you_to_next_stage": requirements.get(current_stage, ""),
        "basis": (
            f"Determined from real signals already on file: prototype confirmed={has_prototype}, "
            f"traction confirmed={has_traction}, revenue model supplied={has_revenue}, overall "
            f"readiness level={level}."
        ),
    }


def build_investor_intelligence(
    funding_assessment: dict, investor_questions: list[dict], knowledge_pack: dict
) -> dict:
    """Startup Domain Intelligence Sprint, Phase 7 — reuses three already-computed sources rather
    than building any new reasoning: `investor_questions` (this sprint's own Phase-2 output, not
    re-derived) for likely objections, `funding_assessment.breakdown` for the real milestones/
    traction metrics this specific venture is actually measured against, and
    `industry_knowledge_packs` for general (never per-venture, never fabricated) startup-outcome
    patterns — explicitly labeled as such, since the retrieval corpus has no real outcome data to
    ground a "why THIS venture would succeed/fail" claim in."""
    milestone_dimensions = ("traction", "product_maturity", "revenue_model_clarity")
    breakdown = {item["dimension"]: item for item in funding_assessment.get("breakdown", [])}
    milestones = [
        {"milestone": breakdown[d]["label"], "current_state": breakdown[d]["scale_description"], "category": "evidence"}
        for d in milestone_dimensions
        if d in breakdown
    ]

    return {
        "founder_intelligence_version": FOUNDER_INTELLIGENCE_VERSION,
        "why_similar_ventures_succeed": {
            "patterns": knowledge_pack["common_competitive_advantages"],
            "category": "general_startup_knowledge",
            "disclaimer": "General patterns for this venture's category, not a claim about this specific venture or any named real company — the retrieval dataset has no outcome data to ground a per-venture success claim.",
        },
        "why_similar_ventures_fail": {
            "patterns": knowledge_pack["common_failure_reasons"],
            "category": "general_startup_knowledge",
            "disclaimer": "General patterns for this venture's category, not a claim about this specific venture or any named real company.",
        },
        "likely_investor_objections": [
            {"persona": q["persona"], "objection": q["question"], "category": "inference"} for q in investor_questions
        ],
        "most_important_milestones": milestones,
        "most_important_traction_metrics": [
            {"metric": "Confirmed pilot usage or paying customers, not just signups", "category": "recommendation"},
            {"metric": "Repeatability across more than one customer/site, not a single anecdote", "category": "recommendation"},
        ],
    }


# Which sections used real retrieved evidence (only true when venture retrieval is enabled AND
# available for this run) vs. pure deterministic reasoning vs. general startup-domain knowledge —
# a fixed, disclosed map of THIS pipeline's own architecture, not a per-run inference.
_SECTION_EVIDENCE_TYPE = {
    "pricing_intelligence": "deterministic_reasoning",
    "go_to_market_intelligence": "deterministic_reasoning",
    "feature_intelligence": "deterministic_reasoning",
    "competitor_intelligence": "deterministic_reasoning",
    "critical_blind_spots": "deterministic_reasoning",
    "investor_questions": "deterministic_reasoning",
    "founder_challenge_mode": "deterministic_reasoning",
    "moat_intelligence": "deterministic_reasoning",
    "funding_stage_ladder": "deterministic_reasoning",
    "founder_iq_report": "deterministic_reasoning",
    "feature_gap_vs_market": "retrieved_evidence_when_available",
    "startup_benchmark": "mixed_retrieved_and_general_knowledge",
    "investor_intelligence": "mixed_deterministic_and_general_knowledge",
    "venture_retrieval": "retrieved_evidence_when_available",
    "industry_knowledge_pack": "general_startup_knowledge",
}


def build_explainability_index(source_attribution: dict, venture_retrieval_available: bool) -> list[dict]:
    """Phase 8 — reuses app.agents.mentor_synthesis's own already-written `source_attribution`
    text (one sentence per section, written when each section was built) rather than re-deriving
    provenance independently. Adds only the evidence-type classification and a confidence note,
    both derived from this pipeline's own fixed, known architecture (which sections CAN use
    retrieval, and whether retrieval is actually available this run) — never a per-run guess."""
    index = []
    for section, description in source_attribution.items():
        evidence_type = _SECTION_EVIDENCE_TYPE.get(section, "deterministic_reasoning")
        uses_retrieval = "retrieved" in evidence_type or "mixed" in evidence_type
        if uses_retrieval and not venture_retrieval_available:
            confidence_note = "Retrieval is not enabled/available for this run — this section fell back to its non-retrieval reasoning path."
        elif uses_retrieval:
            confidence_note = "Retrieval was available for this run — see the section's own citations for which retrieved ventures were used."
        else:
            confidence_note = "This section never depends on retrieval — confidence rests entirely on the deterministic rule/evidence described."
        index.append(
            {
                "section": section,
                "why": description,
                "evidence_type": evidence_type,
                "confidence_note": confidence_note,
            }
        )
    return index
