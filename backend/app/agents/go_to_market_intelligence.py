"""Go-To-Market Intelligence (Product Intelligence Sprint, Phase 4).

Deterministic, additive — reuses app.agents.venture_vocabulary's category resolution (the same
8-bucket healthcare/fintech/hardware/marketplace/developer_tools/education/consumer/b2b/generic
scheme app.agents.judge/founder_guidance/hypothesis_engine already key off) so two ventures in
different categories get genuinely different, specific guidance instead of byte-identical generic
text — never a fabricated claim about this specific venture's actual customers/traction, only
category-level go-to-market patterns. Gemini may separately add qualitative `go_to_market`
mentor_advice_items (see app.agents.mentor_reviewer) for venture-specific color on top of this.

Answers exactly the questions the product mandate requires every founder leave knowing: who to
approach first, first 20 pilot customers, early adopter profile, outreach strategy, distribution
channels, sales motion, validation roadmap, expansion roadmap.
"""

from __future__ import annotations

from app.agents.venture_vocabulary import resolve_category

GTM_INTELLIGENCE_VERSION = "v1"

_GTM_VOCAB: dict[str, dict] = {
    "healthcare": {
        "who_to_approach_first": "A single clinician or department head who already feels this pain daily (not hospital IT or procurement — they can't say yes to a pilot alone).",
        "first_customers_source": "Personal/professional network referrals into one clinic or department, plus clinician-focused communities (specialty associations, LinkedIn groups for that specialty) — never cold outreach to hospital systems this early.",
        "early_adopter_profile": "A smaller, independent practice or a single forward-leaning department inside a larger institution — big enough to matter, small enough to decide fast without a full procurement cycle.",
        "outreach_strategy": "Warm introductions through clinical networks and specialty conferences; a cold-inbound demo request is rare in healthcare and shouldn't be the primary channel.",
        "distribution_channels": ["Clinician referral networks", "Specialty conferences/associations", "Direct relationship-based outreach"],
        "sales_motion": "Consultative, relationship-led, slow — expect weeks-to-months per decision, not self-serve signup.",
    },
    "fintech": {
        "who_to_approach_first": "A single design-partner business willing to be compliance-reviewed alongside you — not a large enterprise procurement team.",
        "first_customers_source": "Founder/operator communities in the relevant vertical, fintech-focused accelerators/demo days, and direct outreach to businesses already complaining publicly about the problem you solve.",
        "early_adopter_profile": "A smaller operator with real transaction volume but no in-house compliance/finance-ops team — motivated to move fast, not blocked by a large legal review.",
        "outreach_strategy": "Direct founder-to-founder outreach plus a clear compliance/security one-pager ready before the first call — trust is the blocker, not features.",
        "distribution_channels": ["Fintech founder communities", "Accelerator/demo-day networks", "Direct outbound to businesses with the visible pain point"],
        "sales_motion": "Consultative with a compliance review step baked in — not pure self-serve at this stage.",
    },
    "hardware": {
        "who_to_approach_first": "One facility/site operations lead who controls a physical pilot location, not a corporate innovation team with no deployment authority.",
        "first_customers_source": "Industry trade shows, equipment-vendor networks, and direct site visits — hardware adoption rarely starts from inbound web traffic.",
        "early_adopter_profile": "A single facility or site willing to host a physical pilot in exchange for early access/pricing — the actual decision-maker for that one site, not a distant HQ.",
        "outreach_strategy": "In-person site visits and trade-show relationships beat digital outreach for physical deployments.",
        "distribution_channels": ["Trade shows/industry associations", "Equipment/systems-integrator partnerships", "Direct site outreach"],
        "sales_motion": "Field sales with a physical pilot install — long cycle, high-touch.",
    },
    "cybersecurity": {
        "who_to_approach_first": "A security lead, CTO, or engineering lead at a company that has already shown some security maturity (a bug bounty, a compliance push) — not a company with no security budget at all.",
        "first_customers_source": "Security-focused communities (conferences, practitioner Slack/Discord groups), and direct outreach to companies who've publicly discussed a recent incident or compliance deadline.",
        "early_adopter_profile": "A mid-size SaaS or tech company facing a compliance deadline (SOC 2, ISO 27001) or a recent scare, with no in-house dedicated security team yet.",
        "outreach_strategy": "Credibility-first outreach — a concrete finding or a free scoped scan showing real value beats a generic pitch; trust is the entire sale in security.",
        "distribution_channels": ["Security practitioner communities/conferences", "Compliance-deadline-driven outbound", "Referrals from a first trusted client"],
        "sales_motion": "Consultative, trust-led, often starting with a scoped paid assessment before any subscription conversation.",
    },
    "foodtech": {
        "who_to_approach_first": "A single kitchen, restaurant, or campus-canteen operations manager who personally deals with the ordering/waste/inventory pain daily.",
        "first_customers_source": "Local restaurant-owner networks, food-service industry associations, and direct site visits — this is a hands-on, relationship-driven sale, not an inbound-led one.",
        "early_adopter_profile": "A single independent kitchen or one corporate campus site willing to run a trial without a lengthy vendor-approval process.",
        "outreach_strategy": "In-person visits and word-of-mouth between kitchen/facility managers who know each other locally.",
        "distribution_channels": ["Local restaurant/food-service associations", "Direct site visits", "Referrals between kitchen/facility managers"],
        "sales_motion": "Founder-led, site-by-site, high-touch — proving cost/waste savings at one site before expanding.",
    },
    "logistics": {
        "who_to_approach_first": "An operations or fleet manager at a company running a real delivery/route operation today, who owns the routing decision directly.",
        "first_customers_source": "Logistics/operations industry associations, direct outreach to companies visibly struggling with delivery costs or delays, and referrals from one proven route.",
        "early_adopter_profile": "A mid-size company with an existing delivery operation but no dedicated route-optimization tooling — feeling the cost of inefficiency but not yet locked into an enterprise TMS contract.",
        "outreach_strategy": "Lead with a concrete, measurable efficiency claim (time or cost saved on a real route) rather than a general platform pitch.",
        "distribution_channels": ["Logistics/operations associations", "Direct outbound to visible delivery operations", "Referrals from a proven pilot route"],
        "sales_motion": "Consultative, evidence-led — one route or hub proven before expanding to the full fleet.",
    },
    "marketplace": {
        "who_to_approach_first": "Whichever side of the marketplace is scarcer/harder to get — recruit that side manually first, then bring the other side to them.",
        "first_customers_source": "Manually recruit a small, concentrated group on the scarce side (a specific city, niche, or community) rather than spreading thin nationally.",
        "early_adopter_profile": "Supply-side partners already active in adjacent channels (forums, local groups, existing informal networks) who are underserved by current tools.",
        "outreach_strategy": "Concierge-style manual matching in the earliest days — do the matching by hand before automating it.",
        "distribution_channels": ["Niche community forums/groups", "Manual/concierge onboarding", "Referrals from the first satisfied supply-side users"],
        "sales_motion": "High-touch manual recruitment on the scarce side, self-serve on the abundant side once liquidity exists.",
    },
    "developer_tools": {
        "who_to_approach_first": "An individual engineer or small engineering team already hitting this problem — not an engineering VP who won't personally use it.",
        "first_customers_source": "Developer communities (relevant Discord/Slack groups, GitHub, technical forums) and content that demonstrates the tool solving a real, specific technical problem.",
        "early_adopter_profile": "A small engineering team at a company past MVP stage but before dedicated platform/infra headcount — feeling the pain but without a build-it-in-house mandate yet.",
        "outreach_strategy": "Technical content (a real worked example, not marketing copy) shared directly into developer communities; let the tool's output speak for itself.",
        "distribution_channels": ["Developer communities/forums", "Open-source/GitHub presence", "Technical content and worked examples"],
        "sales_motion": "Product-led/self-serve first, sales-assisted only once a team wants to expand usage org-wide.",
    },
    "education": {
        "who_to_approach_first": "One teacher, professor, or program lead who can adopt it in a single classroom/cohort without needing district or university-wide sign-off.",
        "first_customers_source": "Educator communities, teaching-focused conferences, and direct outreach to instructors already using informal/manual workarounds for this problem.",
        "early_adopter_profile": "An individual educator or small program with autonomy over their own classroom tools — not a district-level buyer.",
        "outreach_strategy": "Direct relationship-building with individual educators; a single successful classroom becomes the reference for the next one.",
        "distribution_channels": ["Educator communities/associations", "Direct outreach to individual instructors", "Word-of-mouth between educators"],
        "sales_motion": "Bottom-up, teacher-led adoption before any institution-wide procurement conversation.",
    },
    "consumer": {
        "who_to_approach_first": "A small, well-defined early-adopter niche that already actively discusses this problem online — not a broad general audience.",
        "first_customers_source": "Communities where this specific audience already gathers (relevant subreddits, niche social groups, interest-based forums) rather than broad paid ads this early.",
        "early_adopter_profile": "Enthusiasts already trying workarounds or competitor products and vocal about the gaps — they'll give the most useful early feedback and organic word-of-mouth.",
        "outreach_strategy": "Organic community participation and direct engagement with vocal potential users, rather than paid acquisition before product-market fit signals exist.",
        "distribution_channels": ["Niche online communities", "Word-of-mouth/referral", "Organic social content"],
        "sales_motion": "Self-serve signup with a low-friction free tier or trial.",
    },
    "b2b": {
        "who_to_approach_first": "One business owner or operations lead who personally feels the pain and can say yes without a lengthy procurement process.",
        "first_customers_source": "Founder's own network first, then industry-specific business communities/associations and direct outreach to businesses showing visible signs of the problem (job posts, public complaints, manual workaround evidence).",
        "early_adopter_profile": "A small-to-mid-size business past the point of solving this manually with spreadsheets, but too small to be locked into an enterprise incumbent's contract.",
        "outreach_strategy": "Direct, personal outreach and warm introductions — cold email/ads rarely convert a first design partner.",
        "distribution_channels": ["Founder's personal/professional network", "Industry associations/communities", "Direct outbound to businesses with visible pain signals"],
        "sales_motion": "Founder-led sales, high-touch, one design partner at a time until a repeatable pattern emerges.",
    },
    "generic": {
        "who_to_approach_first": "Whoever in your own network already has this exact problem today — the fastest, most honest first customer is someone you can talk to this week.",
        "first_customers_source": "Your own network first; then communities where people with this specific problem already gather online.",
        "early_adopter_profile": "Someone actively feeling this pain right now, not someone who might feel it eventually — urgency matters more than company size at this stage.",
        "outreach_strategy": "Direct, personal outreach — this early, a relationship converts far better than an ad or a cold campaign.",
        "distribution_channels": ["Personal network", "Relevant online communities", "Direct outreach"],
        "sales_motion": "Founder-led, high-touch, one relationship at a time.",
    },
}


def build_go_to_market_intelligence(
    primary_domain: str | None,
    model_category_label: str | None,
    deployment_sectors: list[str] | None,
    funding_level: str,
    startup_description: str | None = None,
    venture_signals: dict | None = None,
    knowledge_pack: dict | None = None,
) -> dict:
    """Produce the structured GTM plan. Always returns a complete dict. Category (via
    `resolve_category`) is only the fallback scaffold now — `venture_signals` (real,
    already-computed facts about THIS venture: prototype/traction evidence states, founder-named
    competitors, deployment sectors — assembled once in app.agents.mentor_synthesis) is the primary
    driver of the first validation step and the personalization notes below, per the Product
    Intelligence Sprint's "venture-first, category-second" mandate.
    """
    category = resolve_category(primary_domain, model_category_label, deployment_sectors, startup_description)
    vocab = _GTM_VOCAB.get(category, _GTM_VOCAB["generic"])
    signals = venture_signals or {}

    is_pre_traction = funding_level in ("early_stage", "developing")
    has_prototype = bool(signals.get("has_prototype"))
    sectors = signals.get("deployment_sectors") or deployment_sectors or []
    top_recommended = signals.get("top_recommended_capability")

    if has_prototype:
        deployment_phrase = f"in {sectors[0]}" if sectors else "with one real customer"
        metric_phrase = (
            top_recommended["validation_question"] if top_recommended and top_recommended.get("validation_question")
            else "a concrete before/after change in the specific workflow you're improving (time, cost, or errors)"
        )
        first_step = (
            f"You already have a working prototype — skip generic discovery interviews and instead deploy it "
            f"{deployment_phrase} for a defined trial window (2-4 weeks), and measure: {metric_phrase}"
        )
    else:
        first_step = "Talk to 5-10 people who match the early-adopter profile below before building anything new — confirm the pain is real and urgent, not assumed."

    validation_roadmap = (
        [
            first_step,
            "Get one unpaid or heavily-discounted pilot commitment in writing (a letter of intent or signed trial) — a verbal 'sounds interesting' is not evidence.",
            "Ship the narrowest version that solves one workflow for that first pilot — resist adding features before this one pilot succeeds.",
            "Convert the pilot to a paying (even nominally-priced) customer before recruiting customer #2 — a free pilot that never converts is a warning sign, not a win.",
        ]
        if is_pre_traction
        else [
            "Document exactly why your existing customers bought, in their own words — this becomes the template for finding more like them.",
            "Identify which acquisition channel actually produced your best customers so far, and double down there before testing new ones.",
            "Get 2-3 customer references willing to talk to prospects — social proof compounds faster than any single sales pitch.",
        ]
    )
    expansion_roadmap = [
        f"Once the first {'pilot' if is_pre_traction else 'segment'} is a proven, repeatable win, expand to adjacent customers who match the same early-adopter profile — resist expanding to a very different segment before this one is solid.",
        "Layer in the distribution channels below one at a time, proving each one works before adding the next — parallel unproven channels usually just spread effort thin.",
        "Only consider paid acquisition once at least one organic/relationship-led channel has a proven, repeatable conversion pattern.",
    ]

    personalization = []
    if signals.get("customer_type"):
        personalization.append(f"You already described your customer as \"{signals['customer_type']}\" — use that exact language in outreach, not the generic buyer description below.")
    if signals.get("known_competitors"):
        personalization.append(
            f"You already listed {', '.join(signals['known_competitors'][:3])} as alternatives — ask your "
            "first prospects directly why they'd pick (or already picked) one of those instead of building "
            "nothing; that answer, not a guess, tells you what to lead with."
        )
    if sectors:
        personalization.append(f"Your stated deployment context ({', '.join(sectors[:3])}) should narrow which of the distribution channels below you try first — don't run all of them at once.")
    comparative = signals.get("comparative_intelligence") or {}
    industry_consensus = comparative.get("common_industry_positioning") if comparative.get("available") else None
    if industry_consensus and industry_consensus.get("confidence") == "high":
        personalization.append(
            f"{industry_consensus['support']} in our reference dataset (citing: "
            f"{', '.join(industry_consensus['citations'][:3])}) — a consistency signal for the positioning "
            "above, not new go-to-market information about those specific companies (source: deterministic "
            "reasoning over retrieved evidence, not a claim about their actual GTM strategy, which this "
            "dataset does not contain)."
        )

    return {
        "gtm_intelligence_version": GTM_INTELLIGENCE_VERSION,
        "who_to_approach_first": vocab["who_to_approach_first"],
        "first_twenty_customers_source": vocab["first_customers_source"],
        "early_adopter_profile": vocab["early_adopter_profile"],
        "outreach_strategy": vocab["outreach_strategy"],
        "distribution_channels": vocab["distribution_channels"],
        "sales_motion": vocab["sales_motion"],
        "validation_roadmap": validation_roadmap,
        "expansion_roadmap": expansion_roadmap,
        "personalization": personalization,
        # Startup Domain Intelligence Sprint, Phase 5 — additive only, `None` when no
        # knowledge_pack is passed (backward compatible with every existing caller).
        "expected_customer_objections": knowledge_pack.get("enterprise_objections") if knowledge_pack else None,
        "buying_process": knowledge_pack.get("buying_process") if knowledge_pack else None,
        # Master Startup Knowledge Base Sprint, Phase 5 — same additive/backward-compatible
        # pattern, surfacing the knowledge pack's newer fields (Phase 2) so ventures in categories
        # this module's own _GTM_VOCAB doesn't have a dedicated persona for (the 13 domains added
        # in Phase 3, which gracefully fall back to the "generic" persona above) still get
        # real category-level acquisition-channel and objection-handling knowledge.
        "smb_objections": knowledge_pack.get("smb_objections") if knowledge_pack else None,
        "customer_acquisition_channels": knowledge_pack.get("customer_acquisition_channels") if knowledge_pack else None,
        "source": (
            f"deterministic — category-level scaffold for '{category}' ventures is the fallback; "
            "venture_signals (this founder's own funding-readiness evidence, named competitors, "
            "deployment context) is the primary driver above — never a claim about this specific "
            "venture's actual customers or traction beyond what the founder themselves reported"
        ),
    }
