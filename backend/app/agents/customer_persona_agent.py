"""Customer Persona Agent (Student 2).

Builds a persona only from submitted or derived evidence — never invents demographics (age,
income, specific job titles) without supporting evidence, since the submission form does not
collect them and no external data source is integrated. Every field is explicitly tagged as one
of: evidence-backed (directly from user input), inference (derived from another field, e.g.
industry), assumption (a stated placeholder that must be validated), or unknown.
"""

from __future__ import annotations

AGENT_VERSION = "v1-deterministic"


def generate_customer_persona(
    market_evidence: dict,
    industry_prediction: dict | None,
) -> dict:
    customer_type = (market_evidence or {}).get("customer_type")
    target_market = (market_evidence or {}).get("target_market")
    industry_label = (industry_prediction or {}).get("predicted_industry")

    field_provenance: dict[str, str] = {}

    if customer_type:
        role_or_context = customer_type
        field_provenance["role_or_context"] = "evidence-backed (user-submitted customer_type)"
    elif industry_label:
        role_or_context = f"a professional or buyer within the '{industry_label}' industry"
        field_provenance["role_or_context"] = "inference (derived from industry classifier output)"
    else:
        role_or_context = "unknown"
        field_provenance["role_or_context"] = "unknown"

    if target_market:
        goal = f"Achieve a better outcome within '{target_market}' than their current approach allows"
        field_provenance["goal"] = "inference (derived from user-submitted target_market)"
    else:
        goal = "unknown — requires customer discovery interviews"
        field_provenance["goal"] = "unknown"

    pain_point = "unknown — no direct evidence of a specific pain point was submitted"
    field_provenance["pain_point"] = "unknown"

    current_alternative = "unknown — see competitor_analysis for candidate alternatives"
    field_provenance["current_alternative"] = "unknown"

    decision_criteria = "unknown — requires customer interviews to identify what drives adoption"
    field_provenance["decision_criteria"] = "unknown"

    adoption_barrier = "unknown — requires customer interviews"
    field_provenance["adoption_barrier"] = "unknown"

    likely_channel = "unknown — requires go-to-market research"
    field_provenance["likely_channel"] = "unknown"

    assumptions_requiring_validation = [
        field for field, source in field_provenance.items() if source in ("unknown", "assumption")
        or source.startswith("inference")
    ]

    persona = {
        "persona_name": "Primary Target Customer",
        "customer_type": customer_type or "unknown",
        "role_or_context": role_or_context,
        "goal": goal,
        "pain_point": pain_point,
        "current_alternative": current_alternative,
        "decision_criteria": decision_criteria,
        "adoption_barrier": adoption_barrier,
        "likely_channel": likely_channel,
        "evidence_source": "user-submitted market_evidence + industry classifier output",
        "confidence": "low" if not customer_type else "medium",
        "field_provenance": field_provenance,
        "assumptions_requiring_validation": assumptions_requiring_validation,
    }

    return {
        "agent_version": AGENT_VERSION,
        "personas": [persona],
        "disclaimer": (
            "No demographic data (age, income, job title) is invented — this system has no source "
            "for it. Fields not directly backed by submitted evidence are marked 'unknown' or "
            "'inference' and must be validated with real customer interviews."
        ),
    }
