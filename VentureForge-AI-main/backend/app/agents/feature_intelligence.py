"""Feature Intelligence (Product Intelligence Sprint, Phase 5).

Deterministic, additive — distinct in purpose from app.ml.capability_library (which sequences
*what to build next, in dependency order*, for MVP scoping). This module proposes *differentiation
and monetization* feature ideas across 8 fixed categories (AI feature, automation, analytics,
integrations, premium tier, enterprise feature, future roadmap item, monetization opportunity),
each with a concrete idea and an explicit reason it would improve the product — never a bare
"needs differentiation" statement. Category-flavored via app.agents.venture_vocabulary's existing
8-bucket resolver so two ventures in different domains get genuinely different ideas, never a
fabricated claim about what this specific venture already has or lacks technically.
"""

from __future__ import annotations

from app.agents.venture_vocabulary import resolve_category

FEATURE_INTELLIGENCE_VERSION = "v1"

_FEATURE_IDEAS: dict[str, dict[str, dict]] = {
    "healthcare": {
        "ai_feature": {"idea": "Risk-trend forecasting that flags a patient/case likely to worsen before the next scheduled check-in.", "why": "Turns the product from a passive record into something that actively catches problems earlier, which is the core value clinicians pay for."},
        "automation": {"idea": "Auto-populate structured case notes from the clinician's existing workflow instead of manual re-entry.", "why": "Clinician time is the scarcest resource in healthcare adoption — removing manual entry directly raises willingness to keep using the tool."},
        "analytics": {"idea": "A simple outcomes dashboard showing trend-over-time per patient cohort, not just per-patient snapshots.", "why": "Institutional buyers evaluate tools on aggregate outcome evidence, not individual cases — this is what turns a pilot into a renewal."},
        "integrations": {"idea": "A read-only integration with the clinic's existing EHR/records system.", "why": "Clinicians won't adopt a second system they must manually re-enter data into — integration removes the single biggest adoption blocker."},
        "premium_tier": {"idea": "A higher tier with multi-site aggregation for clinics/hospital groups running more than one location.", "why": "Multi-site institutions have larger budgets and a clear reason to pay more for cross-site visibility."},
        "enterprise_feature": {"idea": "Role-based access control and an audit log for who viewed/changed patient-related data.", "why": "Enterprise healthcare buyers require this for compliance sign-off — its absence is a hard blocker to a larger deal, not a nice-to-have."},
        "future_roadmap": {"idea": "Expand from single-condition risk flagging to a broader panel of conditions once the first is clinically validated.", "why": "Proves the platform, not just the first use case, which is what justifies expansion revenue from an existing account."},
        "monetization_opportunity": {"idea": "Per-clinician or per-site licensing rather than a flat platform fee.", "why": "Aligns price with the value delivered (more clinicians/sites using it = more value captured), which is easier for a buyer to justify internally than a flat fee."},
    },
    "fintech": {
        "ai_feature": {"idea": "Anomaly detection on transaction patterns to flag likely errors or fraud before they compound.", "why": "Directly reduces financial risk for the customer, which is the strongest value driver in fintech buying decisions."},
        "automation": {"idea": "Automated reconciliation between your data and the customer's existing accounting/ledger system.", "why": "Manual reconciliation is the single biggest recurring time cost in finance operations — automating it is a concrete, provable ROI."},
        "analytics": {"idea": "A cash-flow or exposure forecast view built from the customer's own historical data.", "why": "Finance buyers make decisions on forward-looking numbers, not historical snapshots alone."},
        "integrations": {"idea": "A direct integration with the customer's existing bank/payment processor or accounting software.", "why": "Fintech tools that require manual data export/import lose to any competitor offering a direct connection."},
        "premium_tier": {"idea": "A tier with configurable approval workflows for larger teams needing multi-person sign-off.", "why": "Larger finance teams need controls smaller ones don't — this is a natural, defensible upsell boundary."},
        "enterprise_feature": {"idea": "SOC 2-style audit logging and granular permissioning.", "why": "Enterprise finance buyers' security/compliance review will stall without this — it's a deal-qualifying feature, not a differentiator alone."},
        "future_roadmap": {"idea": "Expand from single-currency/single-market support to multi-currency once the core workflow is proven in one market.", "why": "Signals a credible path to a larger addressable market without diluting focus before product-market fit."},
        "monetization_opportunity": {"idea": "Usage-based pricing tied to transaction volume rather than a flat seat fee.", "why": "Scales revenue with the customer's own growth, which finance buyers find easier to approve than a fixed cost that doesn't track value."},
    },
    "hardware": {
        "ai_feature": {"idea": "Predictive maintenance that forecasts failure from sensor trends rather than only alerting after a threshold is crossed.", "why": "Prevents costly downtime instead of just reporting it, which is the actual budget line hardware/facilities buyers care about."},
        "automation": {"idea": "Automatic response actions (not just alerts) for well-understood, low-risk anomaly patterns.", "why": "Reduces the operational burden on already-stretched facilities/ops staff, which is the main adoption friction in this category."},
        "analytics": {"idea": "Cross-site benchmarking so one facility's performance can be compared against others in the same portfolio.", "why": "Portfolio-level buyers make budget decisions by comparing sites — single-site-only analytics can't support that conversation."},
        "integrations": {"idea": "Integration with the facility's existing building-management or SCADA system rather than a fully separate system.", "why": "Facilities teams resist adding another standalone system — integrating with what they already run removes that resistance."},
        "premium_tier": {"idea": "A tier offering multi-site portfolio management for operators running several facilities.", "why": "Portfolio operators have materially larger budgets than single-site buyers and a clear reason to pay for aggregation."},
        "enterprise_feature": {"idea": "Role-based access and change-history logging for who adjusted a physical system setting.", "why": "Facilities/industrial buyers require accountability logging for safety and compliance sign-off."},
        "future_roadmap": {"idea": "Move from monitoring-only to closed-loop automated control once alert-response trust is established.", "why": "Automated control is the highest-value tier but only credible after the monitoring/alerting layer has earned operator trust."},
        "monetization_opportunity": {"idea": "Per-site or per-sensor pricing rather than a flat platform fee.", "why": "Matches price to physical footprint, which is how facilities buyers already think about cost (per building, per unit)."},
    },
    "cybersecurity": {
        "ai_feature": {"idea": "AI-assisted triage that ranks findings by real exploitability, not just raw severity score.", "why": "Security teams are drowning in low-value alerts — ranking by real risk is what makes the tool actually actionable instead of more noise."},
        "automation": {"idea": "Automated re-testing after a fix is deployed, without re-running a full manual assessment.", "why": "Continuous verification is the difference between a one-time audit and an ongoing security posture — it's what justifies a subscription instead of a one-off engagement."},
        "analytics": {"idea": "A trend view showing whether the customer's overall exposure is improving or worsening release over release.", "why": "Security buyers report upward to leadership on trend, not just point-in-time findings — this is what a champion needs to justify the budget."},
        "integrations": {"idea": "Direct integration into the customer's CI/CD pipeline so checks run pre-merge, not after the fact.", "why": "Catching issues before merge is dramatically cheaper to fix and is the actual adoption bar for engineering teams."},
        "premium_tier": {"idea": "A tier with compliance-mapped reporting (e.g. mapped to SOC 2 or ISO 27001 controls).", "why": "Compliance-driven buyers need output mapped to a specific framework, not just a generic findings list — that mapping alone justifies a higher tier."},
        "enterprise_feature": {"idea": "SSO, role-based access, and a full audit trail of who viewed or resolved which finding.", "why": "Security-conscious enterprise buyers apply the same access-control bar to the security tool itself — its absence is disqualifying."},
        "future_roadmap": {"idea": "Expand from one attack-surface type (e.g. web app) to adjacent ones (API, cloud config) once the first is proven.", "why": "Broader coverage is valuable but only credible once the first surface type has real, defensible accuracy."},
        "monetization_opportunity": {"idea": "Price per asset/environment scanned rather than a flat platform fee.", "why": "Matches cost to the customer's actual attack surface, which is how security budgets are already sized internally."},
    },
    "foodtech": {
        "ai_feature": {"idea": "Demand forecasting that predicts tomorrow's order volume per item from historical ordering patterns.", "why": "Over/under-preparing food is the direct cost driver in this category — a better forecast is money saved, not a nice-to-have."},
        "automation": {"idea": "Automated low-stock/reorder alerts tied to actual consumption rather than a fixed schedule.", "why": "Removes manual inventory checks, which is the single most time-consuming task for kitchen/ops staff."},
        "analytics": {"idea": "A waste-tracking dashboard broken down by item, so the kitchen sees exactly what's being over-ordered.", "why": "Turns an abstract 'reduce waste' goal into a specific, actionable list — the concrete evidence a manager needs to change ordering habits."},
        "integrations": {"idea": "Integration with the site's existing POS or payment system rather than a fully separate ordering flow.", "why": "Kitchen/ops staff won't maintain two separate systems — integration removes the main adoption barrier."},
        "premium_tier": {"idea": "A multi-site tier for operators running canteens/kitchens across several corporate campuses.", "why": "Multi-site operators have materially larger budgets and a real need to compare performance across locations."},
        "enterprise_feature": {"idea": "Role-based access and an audit trail for who changed menu pricing or inventory records.", "why": "Corporate-facilities and catering-contract buyers expect this level of accountability before signing a larger contract."},
        "future_roadmap": {"idea": "Expand from ordering/waste tracking to a broader operations suite (staffing, procurement) once the core workflow is proven at one site.", "why": "Proves the core value first — adding scope before the first workflow is trusted risks diluting the product."},
        "monetization_opportunity": {"idea": "Per-site or per-meal-volume pricing rather than a flat platform fee.", "why": "Matches price to the actual scale of food service being managed, which is how facilities/catering budgets are already thought about."},
    },
    "logistics": {
        "ai_feature": {"idea": "Route optimization that re-plans in real time as new orders or delays come in, not just at day-start.", "why": "Static routes lose value the moment reality diverges from the plan — real-time replanning is what actually saves fuel/time."},
        "automation": {"idea": "Automated driver/dispatcher notifications for route changes instead of manual phone calls.", "why": "Manual dispatch coordination is the biggest time sink in last-mile operations — automating it is a direct, provable time saving."},
        "analytics": {"idea": "An on-time-delivery and cost-per-delivery dashboard broken down by route/driver.", "why": "Operations managers are measured on exactly these numbers — giving them directly is what makes the tool part of their weekly review, not a side tool."},
        "integrations": {"idea": "Integration with the customer's existing order-management or e-commerce platform.", "why": "Logistics tools that require manual order re-entry lose to anything that plugs directly into the existing order flow."},
        "premium_tier": {"idea": "A tier with multi-hub/multi-region route optimization for operators beyond a single depot.", "why": "Multi-hub operators have materially more complex routing needs and larger budgets to match."},
        "enterprise_feature": {"idea": "Role-based access and a full audit trail for route/schedule changes.", "why": "Enterprise logistics buyers require this for accountability and dispute resolution — its absence blocks larger contracts."},
        "future_roadmap": {"idea": "Expand from route optimization to broader fleet management (maintenance, driver scheduling) once the core routing value is proven.", "why": "Routing is the clearest first wedge; broader fleet features are a credible next step only once that wedge is trusted."},
        "monetization_opportunity": {"idea": "Per-vehicle or per-delivery pricing rather than a flat platform fee.", "why": "Matches cost to the customer's actual delivery volume, which is how logistics budgets are already structured."},
    },
    "marketplace": {
        "ai_feature": {"idea": "Smart matching/ranking between supply and demand sides based on past successful matches.", "why": "Better matching is the core value a marketplace provides — improving it directly improves both sides' outcomes and retention."},
        "automation": {"idea": "Automated onboarding/verification for new supply-side participants.", "why": "Manual vetting caps how fast the supply side can grow, which is usually the binding constraint on marketplace liquidity."},
        "analytics": {"idea": "Supply/demand liquidity dashards showing where the marketplace is thin by category or region.", "why": "Tells the team exactly where to focus manual recruitment next, rather than guessing."},
        "integrations": {"idea": "Payment/payout integration so transactions can settle inside the platform rather than off-platform.", "why": "Off-platform payment is both a revenue leak (no take-rate) and a trust/dispute-resolution risk."},
        "premium_tier": {"idea": "A featured/priority-placement tier for supply-side participants willing to pay for visibility.", "why": "Directly monetizes the scarce, high-value side of the marketplace without charging the side you're still trying to grow."},
        "enterprise_feature": {"idea": "Bulk/API access for larger supply-side partners managing many listings at once.", "why": "Larger partners won't manage listings one at a time manually — this is required to win them at all, not just to compete on price."},
        "future_roadmap": {"idea": "Expand into adjacent categories once liquidity is proven in the first one.", "why": "Marketplace liquidity doesn't transfer automatically across categories — proving one first de-risks expansion."},
        "monetization_opportunity": {"idea": "A transaction take-rate rather than (or in addition to) a subscription fee.", "why": "Aligns revenue directly with marketplace volume, which is the metric that actually reflects the value being created."},
    },
    "developer_tools": {
        "ai_feature": {"idea": "AI-assisted suggestions (e.g. auto-generated config, code, or query suggestions) grounded in the user's own project context.", "why": "Reduces time-to-value for a technical user, which is the single biggest driver of developer-tool adoption and word-of-mouth."},
        "automation": {"idea": "Automated setup/scaffolding so a new user reaches a working state without manual configuration.", "why": "Developer tools live or die on time-to-first-success — every manual setup step is a drop-off point."},
        "analytics": {"idea": "Usage/error analytics surfaced back to the team using the tool, not just to you.", "why": "Gives the buying team's own justification for continued/expanded use — internal champions need this to defend the tool internally."},
        "integrations": {"idea": "Native integration with the CI/CD or existing toolchain the team already uses.", "why": "Developer tools that require workflow changes lose to ones that slot into the existing pipeline."},
        "premium_tier": {"idea": "A team/organization tier with shared configuration and centralized billing.", "why": "Individual-developer usage rarely converts to meaningful revenue alone — the team tier is where real monetization happens."},
        "enterprise_feature": {"idea": "SSO and audit logging for organization-wide deployment.", "why": "Without SSO, a security/IT review blocks org-wide rollout regardless of how good the tool is for individual developers."},
        "future_roadmap": {"idea": "Expand from a single integration/language/framework to the next most-requested one once the first is solid.", "why": "Signals a credible platform trajectory without spreading engineering effort before the first integration is proven."},
        "monetization_opportunity": {"idea": "Usage-based pricing (API calls, builds, seats-active) rather than a flat fee.", "why": "Matches cost to actual usage, which technical buyers evaluate more favorably than a flat fee unrelated to value received."},
    },
    "education": {
        "ai_feature": {"idea": "Adaptive difficulty/pacing based on individual learner performance.", "why": "Personalization is the single biggest differentiator over static content in education products."},
        "automation": {"idea": "Automated grading/progress tracking for the instructor.", "why": "Instructor time is the real constraint on classroom adoption — automating grading is a direct, provable time-saver."},
        "analytics": {"idea": "A simple instructor-facing dashboard showing which learners are falling behind, in real time.", "why": "Gives the instructor a reason to keep using the tool daily, not just at term start."},
        "integrations": {"idea": "Integration with the school/university's existing LMS (e.g. roster sync, grade passback).", "why": "Instructors won't maintain data in two systems — LMS integration removes the main adoption barrier."},
        "premium_tier": {"idea": "A program/department tier with cross-classroom reporting.", "why": "Department leads have larger budgets and a real use case (comparing classrooms) that a single teacher doesn't."},
        "enterprise_feature": {"idea": "FERPA-aligned data handling and administrator-level access controls.", "why": "Institution-wide procurement will not proceed without this — it's a gate, not a differentiator."},
        "future_roadmap": {"idea": "Expand from one subject/course to adjacent subjects once the first is adopted and validated.", "why": "Proves pedagogical value before committing engineering effort to breadth."},
        "monetization_opportunity": {"idea": "Per-student or per-classroom pricing rather than a flat institutional fee.", "why": "Scales naturally with institution size, which is easier to justify to a budget owner than an arbitrary flat rate."},
    },
    "consumer": {
        "ai_feature": {"idea": "Personalized recommendations based on the individual user's own usage history.", "why": "Personalization is what turns a one-time-use tool into a daily habit, which is the actual retention driver in consumer products."},
        "automation": {"idea": "Smart defaults/auto-fill based on the user's prior choices.", "why": "Reduces friction on repeat use, which is the main lever for consumer retention."},
        "analytics": {"idea": "A simple personal-progress or usage-history view for the user themselves.", "why": "Gives users their own reason to return (seeing their own progress), independent of any feature you add for you."},
        "integrations": {"idea": "Integration with a platform users already use daily (calendar, messaging, etc.).", "why": "Meeting users where they already are lowers the activation barrier far more than a fully standalone app."},
        "premium_tier": {"idea": "A premium tier unlocking advanced personalization or removing usage limits.", "why": "Freemium-to-paid conversion needs a genuinely more valuable premium experience, not just fewer restrictions."},
        "enterprise_feature": {"idea": "A team/family sharing plan if usage naturally extends beyond one person.", "why": "Opens a second monetization path without requiring a full enterprise sales motion."},
        "future_roadmap": {"idea": "Expand from the single core use case to an adjacent one once daily-use habit is proven.", "why": "Adding breadth before habit-formation risks diluting the one thing users actually come back for."},
        "monetization_opportunity": {"idea": "A freemium model with a clear, valuable premium unlock rather than a hard paywall from day one.", "why": "Lets users experience real value before paying, which is how most successful consumer products build a funnel."},
    },
    "b2b": {
        "ai_feature": {"idea": "AI-generated summaries or recommendations drawn from the customer's own operational data.", "why": "Turns raw data the customer already has into decisions they can act on immediately, which is what justifies a software budget line."},
        "automation": {"idea": "Automate the single most time-consuming manual step in the customer's current workflow.", "why": "B2B buyers justify purchases on hours saved — automating the worst manual step is the most direct ROI story."},
        "analytics": {"idea": "A manager-facing reporting view summarizing team/operational performance.", "why": "Gives the economic buyer (often not the daily user) their own reason to keep approving the renewal."},
        "integrations": {"idea": "Integration with the tool the customer already uses for this workflow today.", "why": "B2B buyers rarely rip out an existing system — integrating alongside it is usually the only realistic path to adoption."},
        "premium_tier": {"idea": "A tier with advanced permissions/workflow customization for larger teams.", "why": "Larger teams have needs (permissions, customization) smaller teams don't, which is a natural, defensible upsell line."},
        "enterprise_feature": {"idea": "SSO, audit logging, and admin-level user management.", "why": "This is what a security/procurement review checks for — its absence blocks larger deals regardless of core product quality."},
        "future_roadmap": {"idea": "Expand from the first team/department to adjacent departments once the first deployment is a proven success.", "why": "A proven single-department deployment is the reference case that justifies wider internal expansion."},
        "monetization_opportunity": {"idea": "Per-seat or per-workflow pricing that scales with the customer's own team size.", "why": "Ties revenue growth to the customer's own growth, which is easier to expand within an existing account than renegotiating a flat fee."},
    },
    "generic": {
        "ai_feature": {"idea": "A recommendation or forecasting feature built from data the product already collects.", "why": "Uses information you already have to deliver more value without asking the user for anything new."},
        "automation": {"idea": "Automate the most repetitive manual step in the current user workflow.", "why": "The clearest, most provable ROI story in any product is 'this used to take you X minutes, now it takes zero.'"},
        "analytics": {"idea": "A simple dashboard showing the user their own usage/progress over time.", "why": "Gives users an independent reason to return, beyond the core workflow alone."},
        "integrations": {"idea": "Integration with the tool your users already rely on for an adjacent part of their workflow.", "why": "Reduces the number of separate tools a user must juggle, which is a common reason products get dropped."},
        "premium_tier": {"idea": "A premium tier unlocking a genuinely higher-value capability, not just higher limits.", "why": "A real premium tier needs to feel like more value, not just fewer restrictions, to convert well."},
        "enterprise_feature": {"idea": "Basic role-based access control and an activity log.", "why": "This is the minimum bar for any team/organization-level buyer to even consider the product."},
        "future_roadmap": {"idea": "Expand to an adjacent use case once the current core workflow is proven with real users.", "why": "Proving one workflow first avoids diluting focus before product-market fit exists."},
        "monetization_opportunity": {"idea": "Usage-based or tiered pricing that scales with the value delivered, not a single flat price.", "why": "Makes it easier for both very small and very large customers to find a price point that fits them."},
    },
}


def build_feature_intelligence(
    primary_domain: str | None,
    model_category_label: str | None,
    deployment_sectors: list[str] | None,
    differentiation_is_weak: bool,
    startup_description: str | None = None,
    venture_signals: dict | None = None,
) -> dict:
    """Produce 8 concrete, category-flavored feature ideas, each with a `why`, plus one
    venture-specific `next_build_recommendation`. Always returns a complete dict —
    differentiation_is_weak only changes the framing note, never whether ideas are produced.

    The 8 category ideas below are intentionally kept as a fallback scaffold, not the primary
    signal — `next_build_recommendation` is built from `venture_signals["top_present_capability"]`/
    `["top_recommended_capability"]` (app.ml.capability_library's already-computed, per-venture
    present-vs-missing classification, itself keyed off THIS founder's own description, not a
    fixed template) whenever available, so the single most prominent recommendation is grounded in
    what this specific founder already has versus what's actually buildable next for them.
    """
    category = resolve_category(primary_domain, model_category_label, deployment_sectors, startup_description)
    ideas = _FEATURE_IDEAS.get(category, _FEATURE_IDEAS["generic"])
    signals = venture_signals or {}

    comparative = signals.get("comparative_intelligence") or {}
    terminology = comparative.get("common_terminology") if comparative.get("available") else None
    retrieved_terminology_context = (
        {
            "terms": terminology["terms"],
            "provenance": terminology["provenance"],
            "note": (
                "Descriptive context only — these are terms real similar ventures use in their own "
                "descriptions, not a claim about which features they actually built (this dataset "
                "has no feature-level data)."
            ),
        }
        if terminology and terminology.get("available")
        else None
    )

    present = signals.get("top_present_capability")
    recommended = signals.get("top_recommended_capability")
    if recommended:
        next_build_recommendation = {
            "idea": recommended["label"],
            "why": recommended.get("reason") or recommended.get("description", ""),
            "how_to_validate": recommended.get("validation_question", ""),
            "builds_on": (
                f"You already have {present['label']} in place ({present.get('reason', '')}) — this is the next capability that's actually buildable given that."
                if present else
                "No existing capability was detected in your description yet — validate the core workflow itself before adding this."
            ),
        }
    else:
        next_build_recommendation = {
            "idea": None,
            "why": "Not enough evidence in your description yet to name a specific next capability with confidence.",
            "how_to_validate": "Describe your actual current workflow in more detail (what a user does step by step today) so this recommendation can be grounded in it rather than guessed.",
            "builds_on": (
                f"You already have {present['label']} in place ({present.get('reason', '')})." if present else ""
            ),
        }

    return {
        "feature_intelligence_version": FEATURE_INTELLIGENCE_VERSION,
        "differentiation_is_weak": differentiation_is_weak,
        "next_build_recommendation": next_build_recommendation,
        "retrieved_terminology_context": retrieved_terminology_context,
        "framing_note": (
            "Differentiation is a real gap right now — the ideas below are concrete starting "
            "points, not just a restatement of the gap."
            if differentiation_is_weak
            else "Differentiation looks reasonable already — the ideas below are still worth "
            "considering as the product matures."
        ),
        "ai_feature": ideas["ai_feature"],
        "automation": ideas["automation"],
        "analytics": ideas["analytics"],
        "integrations": ideas["integrations"],
        "premium_tier": ideas["premium_tier"],
        "enterprise_feature": ideas["enterprise_feature"],
        "future_roadmap": ideas["future_roadmap"],
        "monetization_opportunity": ideas["monetization_opportunity"],
        "source": (
            f"category-level feature/differentiation pattern for '{category}' ventures "
            "(deterministic, keyed off venture_positioning/model_category) — concrete starting "
            "ideas to adapt, never a claim about what this specific venture already has"
        ),
    }
