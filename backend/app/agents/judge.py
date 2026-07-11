"""Judge Agent: deterministic synthesis of the industry and funding-readiness outputs.

This never calls an external LLM and never invents facts. It only reformats and reconciles what
the industry classifier (a model prediction) and the funding-readiness rubric (a deterministic
score derived from user-provided answers) already produced. An optional narrative enhancement
(Gemini, via backend/app/ai/) is layered on top by the orchestrator after this function returns —
see app/agents/orchestrator.py's `_try_llm_narrative` — never inside this module, so `synthesize`
itself has no network dependency and its output is identical whether or not an LLM is configured.
"""

from __future__ import annotations

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
) -> dict:
    """Produce the final Judge summary. Raises ValueError if required fields are missing."""
    if funding_assessment is None or "overall_score" not in funding_assessment:
        raise ValueError("funding_assessment is required and must include overall_score")

    breakdown = funding_assessment.get("breakdown", [])
    missing = set(funding_assessment.get("missing_evidence", []))

    strengths = [
        f"{item['label']}: {item['scale_description']}" for item in breakdown if item["raw_score"] == 2
    ]
    weaknesses = [
        f"{item['label']}: {item['scale_description']}"
        for item in breakdown
        if item["raw_score"] == 0 and item["dimension"] not in missing
    ]
    missing_evidence = [
        next(item["label"] for item in breakdown if item["dimension"] == dim) for dim in missing
    ]
    next_actions = [
        _ACTION_BY_DIMENSION[item["dimension"]]
        for item in breakdown
        if item["raw_score"] in (0,) and item["dimension"] in _ACTION_BY_DIMENSION
    ]

    confidence_level = _confidence_level(industry_prediction, funding_assessment, evidence_check)

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
        "source_attribution": {
            "industry_prediction": industry_model_description,
            "funding_assessment": "deterministic rubric score from user-provided answers",
            "strengths_weaknesses_next_actions": "generated from rubric breakdown via fixed templates",
        },
    }
