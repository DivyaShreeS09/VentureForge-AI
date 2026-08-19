"""Competitor Intelligence (Product Intelligence Sprint, Phase 6).

Deterministic, additive — complements app.agents.competitor_agent (which handles named-competitor
buckets and Gemini-suggested category possibilities) with category-level analysis of customer
switching behavior, switching friction, and how to win — never a claim about a specific real
company. Reuses app.agents.venture_vocabulary's category resolver so different domains get
genuinely different guidance. Every field is explicitly labeled as a category-level assumption,
never presented as researched fact about this venture's actual competitive landscape.
"""

from __future__ import annotations

from app.agents.venture_vocabulary import resolve_category

COMPETITOR_INTELLIGENCE_VERSION = "v1"

_COMPETITOR_PATTERNS: dict[str, dict] = {
    "healthcare": {
        "customer_alternatives": ["An existing EHR/records system's built-in module, used passively rather than as a dedicated tool", "A manual clinical workflow/checklist with no software at all", "A point solution from an established health-tech vendor"],
        "switching_behavior": "Clinicians switch tools reluctantly and only when a workflow change is clearly worth the disruption — usually driven by a champion clinician, not a top-down mandate.",
        "switching_friction": "High: clinical workflows are risk-averse, require training, and often need institutional/compliance sign-off before any new tool touches patient data.",
        "how_to_win": "Win one clinician champion with an unmistakable time/outcome improvement in a narrow workflow, rather than trying to compete on breadth against an established EHR module.",
    },
    "fintech": {
        "customer_alternatives": ["A spreadsheet-based manual process", "An existing accounting/finance platform's bolt-on feature", "An established fintech incumbent with broader but shallower coverage"],
        "switching_behavior": "Finance teams switch when a manual process becomes too error-prone or time-consuming to sustain, or when a compliance requirement forces a change.",
        "switching_friction": "High: financial data migration, compliance review, and trust-building all slow adoption regardless of feature quality.",
        "how_to_win": "Win on a narrow, high-trust wedge (one specific workflow done precisely right) rather than competing broadly against an incumbent's full platform.",
    },
    "hardware": {
        "customer_alternatives": ["A legacy/manual monitoring process (site walkthroughs, paper logs)", "An existing building-management/SCADA system's basic reporting", "An established industrial IoT vendor"],
        "switching_behavior": "Facilities teams switch slowly, usually tied to a hardware refresh cycle or a specific incident that exposes a real gap.",
        "switching_friction": "High: physical installation, integration with existing systems, and multi-stakeholder sign-off (facilities, IT, finance) all add friction.",
        "how_to_win": "Win a single site with a fast, low-disruption pilot and hard evidence of savings/prevented downtime — site-by-site proof beats a broad sales pitch.",
    },
    "cybersecurity": {
        "customer_alternatives": ["A generalist security consultancy hired for a one-off audit", "An existing cloud/platform provider's built-in (basic) security scanning", "Doing nothing and relying on manual code review"],
        "switching_behavior": "Security buyers switch when a compliance deadline forces a change, or after an incident/near-miss exposes a real gap — rarely on feature comparison alone.",
        "switching_friction": "High: trust must be earned before a security tool is even given access to sensitive systems, and switching means re-establishing that trust from zero.",
        "how_to_win": "Win by proving a concrete, specific finding or improvement in a scoped free/low-cost assessment — credibility, not a feature list, is what converts a security buyer.",
    },
    "foodtech": {
        "customer_alternatives": ["A manual whiteboard/spreadsheet ordering and inventory process", "A generic restaurant-POS system's basic inventory module", "An established food-service management vendor with broader but shallower coverage"],
        "switching_behavior": "Kitchen/facility managers switch when manual tracking visibly causes waste or stockouts they can point to — usually after a specific bad week, not proactively.",
        "switching_friction": "Moderate: staff retraining and a transition period where both old and new processes run in parallel are the main friction, not technical integration.",
        "how_to_win": "Win one site with clear, measurable waste/cost savings, then use that concrete number to win the next site — site-by-site proof beats a broad platform pitch.",
    },
    "logistics": {
        "customer_alternatives": ["A manual dispatcher planning routes by experience/spreadsheet", "An existing TMS (transport management system) with a basic routing module", "A third-party logistics provider handling delivery entirely"],
        "switching_behavior": "Operations teams switch when delivery costs or delays become visibly unacceptable to their own customers — usually triggered by a specific complaint or cost spike, not gradually.",
        "switching_friction": "Moderate to high: route data migration, driver retraining, and a period of parallel-running old and new systems to confirm reliability.",
        "how_to_win": "Win with a specific, measurable efficiency claim on one real route/hub before asking for the whole fleet — logistics buyers trust numbers, not promises.",
    },
    "marketplace": {
        "customer_alternatives": ["Direct, informal peer-to-peer arrangements (word of mouth, existing personal networks)", "A generalist marketplace not specialized for this niche", "Manual matchmaking (an agency, broker, or intermediary)"],
        "switching_behavior": "Both sides switch when liquidity (enough of the other side present) becomes real — network effects mean early switching is fragile and easily reversed.",
        "switching_friction": "Low per-transaction, but high at the network level: a marketplace with no liquidity yet has effectively infinite friction until critical mass is reached.",
        "how_to_win": "Win a small, concentrated niche first (one city, one vertical) to reach real liquidity, rather than competing broadly against a generalist with more supply.",
    },
    "developer_tools": {
        "customer_alternatives": ["An in-house/internal tool the team already built themselves", "A broader platform's built-in (but shallower) equivalent feature", "An established open-source alternative"],
        "switching_behavior": "Developers switch fast when a tool is genuinely better and easy to try — but only if migration cost from the current setup is low.",
        "switching_friction": "Low for individual trial, higher for team-wide migration (existing configuration, integrations, and habits).",
        "how_to_win": "Win on a specific, provable technical advantage plus a frictionless first-five-minutes experience — developer tools rarely win on breadth alone.",
    },
    "education": {
        "customer_alternatives": ["A generic productivity tool repurposed for the classroom", "An existing LMS's built-in (but limited) feature", "A manual/paper-based process"],
        "switching_behavior": "Individual instructors switch based on personal conviction it helps their students; institution-wide switching is slow and budget-cycle-driven.",
        "switching_friction": "Moderate at the classroom level, high at the institution level (procurement cycles, LMS integration requirements).",
        "how_to_win": "Win one enthusiastic instructor first and let a proven classroom result be the reference case for the next one, rather than pursuing institution-wide deals early.",
    },
    "consumer": {
        "customer_alternatives": ["A generalist app already covering this need partially", "A manual habit/workaround with no app at all", "An established consumer incumbent with a larger user base"],
        "switching_behavior": "Consumers switch impulsively for a genuinely better experience, but revert just as fast without a reason to form a habit.",
        "switching_friction": "Low to switch in, but also low to switch back out — retention through habit-formation matters more than the initial switch.",
        "how_to_win": "Win a specific underserved niche with an experience clearly better than the generalist incumbent's one-size-fits-all approach, then earn daily-use habit.",
    },
    "b2b": {
        "customer_alternatives": ["A spreadsheet or manual process", "An existing platform's adjacent/bolt-on feature", "An established incumbent with broader but shallower coverage of this specific need"],
        "switching_behavior": "Business buyers switch when the cost of the status quo (time, errors, missed revenue) becomes clearly higher than the cost of switching.",
        "switching_friction": "Moderate to high: procurement process, data migration, and team retraining all slow adoption regardless of product quality.",
        "how_to_win": "Win a narrow, underserved workflow precisely rather than competing broadly against an incumbent's full platform — depth beats breadth against an established player.",
    },
    "generic": {
        "customer_alternatives": ["A manual/spreadsheet-based process", "An existing tool's adjacent feature used as a workaround", "Doing nothing and living with the current pain"],
        "switching_behavior": "Users switch when the current workaround's cost (time, errors, frustration) clearly exceeds the effort of trying something new.",
        "switching_friction": "Moderate: habit and setup effort are the main barriers, more than any single feature gap.",
        "how_to_win": "Win by being dramatically better at the one specific workflow users care about most, rather than trying to match a broader incumbent feature-for-feature.",
    },
}


def build_competitor_intelligence(
    primary_domain: str | None,
    model_category_label: str | None,
    deployment_sectors: list[str] | None,
    has_named_competitors: bool,
    startup_description: str | None = None,
    venture_signals: dict | None = None,
) -> dict:
    """Produce category-level customer-alternative/switching/how-to-win analysis. Always returns a
    complete dict. `has_named_competitors` only changes the framing note (whether this supplements
    or substitutes for real named-competitor research) — the analysis itself is always produced.

    `venture_signals["known_competitors"]` (the founder's own submitted list, real and never
    invented) drives a `named_competitor_context` field with a concrete next action referencing
    those specific names — this is the venture-first signal; the category pattern below remains
    only the fallback scaffold when no names were given.
    """
    category = resolve_category(primary_domain, model_category_label, deployment_sectors, startup_description)
    pattern = _COMPETITOR_PATTERNS.get(category, _COMPETITOR_PATTERNS["generic"])
    known_competitors = (venture_signals or {}).get("known_competitors") or []
    retrieved_ventures = (venture_signals or {}).get("retrieved_ventures") or []
    comparative_intelligence = (venture_signals or {}).get("comparative_intelligence")

    named_competitor_context = (
        f"You already named {', '.join(known_competitors[:5])} as alternatives. The fastest, most "
        "reliable differentiation research isn't more analysis — it's asking 2-3 of your target "
        f"customers directly why they use (or would choose) {known_competitors[0]} today, and what "
        "they wish it did differently. That answer is the real gap to attack, not a guess."
        if known_competitors
        else "No specific competitors are on file yet — naming 2-3 real, specific alternatives your "
        "target customer already considers is the single highest-value next step here."
    )

    return {
        "competitor_intelligence_version": COMPETITOR_INTELLIGENCE_VERSION,
        "framing_note": (
            "This supplements the named competitors already on file — it's category-level "
            "pattern analysis, not a replacement for researching those specific companies."
            if has_named_competitors
            else "No specific competitors are on file yet, so this is category-level analysis of "
            "what customers likely do today instead — naming 2-3 real, specific alternatives is "
            "still the next concrete step."
        ),
        "named_competitor_context": named_competitor_context,
        "historical_reference_ventures": [
            {
                "name": v["name"],
                "industry": v["industry"],
                "similarity": v["similarity"],
                "why_similar": v["why_similar"],
            }
            for v in retrieved_ventures
        ],
        "comparative_pattern_analysis": comparative_intelligence,
        "historical_reference_disclaimer": (
            "Real companies from a historical dataset (YC-backed, 2012-2024), retrieved by "
            "description similarity — NOT verified as current competitors, may no longer be "
            "operating, and shown only as pattern reference, never as a claim about this "
            "venture's actual competitive landscape."
            if retrieved_ventures else None
        ),
        "likely_customer_alternatives": pattern["customer_alternatives"],
        "switching_behavior": pattern["switching_behavior"],
        "switching_friction": pattern["switching_friction"],
        "how_to_win": pattern["how_to_win"],
        "source": (
            f"venture-first: named_competitor_context is grounded in this founder's own submitted "
            f"competitor list when given; the category-level pattern for '{category}' ventures "
            "(deterministic, keyed off venture_positioning/model_category) is only the fallback "
            "scaffold — never a claim about a specific real company's actual product, pricing, or "
            "market position"
        ),
    }
