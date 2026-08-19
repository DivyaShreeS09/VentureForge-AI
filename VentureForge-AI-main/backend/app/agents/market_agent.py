"""Market Intelligence Agent (Student 2).

Deterministic and evidence-bound by design: this module never invents a TAM/SAM/SOM figure,
growth rate, or "current market trend" — no live market data source is wired into this system, and
presenting an LLM's guess as researched market sizing would be fabrication (see the repo-wide
"do not fabricate market size" rule). Every field is derived only from: (a) the industry
classifier's own prediction, (b) user-submitted `market_evidence`, and (c) the deterministic
funding-readiness rubric's `market_size_evidence`/`customer_pain_evidence` dimensions. Anything not
derivable from those sources is reported as an evidence gap with a concrete recommended action,
not guessed.
"""

from __future__ import annotations

AGENT_VERSION = "v1-deterministic"

_STAGE_MATURITY = {
    "idea": "pre-market — no live market feedback yet",
    "mvp": "early market entry — initial user feedback stage",
    "early_traction": "emerging market position — early paying customers",
    "growth": "established market position — scaling within a validated segment",
}


def generate_market_analysis(
    industry_prediction: dict | None,
    funding_assessment: dict,
    market_evidence: dict,
) -> dict:
    target_market = (market_evidence or {}).get("target_market")
    geography = (market_evidence or {}).get("geography")
    customer_type = (market_evidence or {}).get("customer_type")
    startup_stage = (market_evidence or {}).get("startup_stage")

    industry_is_uncertain = (industry_prediction or {}).get("is_uncertain", True)

    evidence_gaps: list[str] = []
    recommended_validation_actions: list[str] = []

    if target_market:
        market_summary = f"You're going after {target_market}"
    else:
        market_summary = "You haven't named a specific market yet"
        evidence_gaps.append("target_market")
        recommended_validation_actions.append(
            "Define the specific target market segment (not just the industry classification)."
        )

    if geography:
        market_summary += f", starting in {geography}"
    else:
        evidence_gaps.append("geography")
        recommended_validation_actions.append("Specify the geographic market(s) being targeted.")

    if industry_is_uncertain:
        market_summary += " — I'd hold my read on the broader industry loosely for now."
    else:
        market_summary += "."

    if customer_type:
        market_summary += f" The buyer I'd focus on: {customer_type}."
    else:
        evidence_gaps.append("customer_type")
        recommended_validation_actions.append("Describe the primary customer type (B2B, B2C, enterprise, etc.).")

    breakdown = {item["dimension"]: item for item in funding_assessment.get("breakdown", [])}
    market_size_evidence = breakdown.get("market_size_evidence", {})
    customer_pain_evidence = breakdown.get("customer_pain_evidence", {})

    opportunity_drivers: list[str] = []
    constraints: list[str] = []

    if market_size_evidence.get("raw_score") == 2:
        opportunity_drivers.append("You've already backed up how big this opportunity is — that's real work most founders skip.")
    elif market_size_evidence.get("raw_score") in (0, None):
        constraints.append("You haven't sized this market yet, so I can't tell you how big the opportunity really is.")
        evidence_gaps.append("market_size_evidence")
        recommended_validation_actions.append("Produce a sourced TAM/SAM/SOM estimate rather than an unsupported figure.")

    if customer_pain_evidence.get("raw_score") == 2:
        opportunity_drivers.append("You have real documented evidence people feel this pain — that's the foundation everything else builds on.")
    elif customer_pain_evidence.get("raw_score") in (0, None):
        constraints.append("There's no documented evidence yet that people actually feel this pain — worth confirming before you go further.")
        evidence_gaps.append("customer_pain_evidence")

    if startup_stage and startup_stage in _STAGE_MATURITY:
        market_maturity = _STAGE_MATURITY[startup_stage]
    elif startup_stage:
        market_maturity = f"I don't recognize \"{startup_stage}\" as a stage, so I'm treating it as unknown for now."
        evidence_gaps.append("startup_stage")
    else:
        market_maturity = "You haven't told me what stage you're at yet, so I can't place this in the market's maturity curve."
        evidence_gaps.append("startup_stage")

    known_fields_present = sum(1 for v in (target_market, geography, customer_type, startup_stage) if v)
    if known_fields_present >= 3 and not industry_is_uncertain:
        confidence = "medium"
    else:
        confidence = "low"

    return {
        "agent_version": AGENT_VERSION,
        "market_summary": market_summary,
        "opportunity_drivers": opportunity_drivers,
        "constraints": constraints,
        "evidence_gaps": sorted(set(evidence_gaps)),
        "market_maturity": market_maturity,
        "confidence": confidence,
        "source_attribution": {
            "market_summary": "user-submitted market_evidence + industry classifier output",
            "opportunity_drivers_constraints": "deterministic funding-readiness rubric breakdown (market_size_evidence, customer_pain_evidence)",
            "market_maturity": "user-submitted startup_stage",
        },
        "recommended_validation_actions": recommended_validation_actions,
        "disclaimer": (
            "I don't have a live research feed to pull real market data from — everything above "
            "comes from what you've told me so far, not outside research. Treat it as a starting "
            "read, not a market report."
        ),
    }
