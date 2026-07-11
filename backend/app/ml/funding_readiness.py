"""Transparent, deterministic funding-readiness rubric.

No public dataset with a defensible funding-readiness target was identified (see
ml/DATASETS.md) — this is a hand-designed scoring rubric, not a trained model, and must never be
described as one. It is explicitly a "readiness assessment," not a probability of receiving
funding. The design is intentionally centralized and versioned so it can be swapped for a
supervised model later without changing its calling contract.

Each dimension is scored 0 (no evidence), 1 (some evidence), or 2 (strong evidence) by the user.
Missing answers are scored 0 — no favourable assumption is made for absent data — and are
reported separately as missing evidence.
"""

from __future__ import annotations

RUBRIC_VERSION = "v1"
MAX_DIMENSION_SCORE = 2

# Centralized, versioned weights (must sum to 1.0). Each entry documents its 0/1/2 scale meaning.
DIMENSIONS: dict[str, dict] = {
    "problem_clarity": {
        "weight": 0.14,
        "label": "Problem Clarity",
        "scale": {0: "Problem not clearly stated", 1: "Problem stated but broad", 2: "Specific, well-defined problem"},
    },
    "customer_pain_evidence": {
        "weight": 0.13,
        "label": "Evidence of Customer Pain",
        "scale": {0: "No evidence provided", 1: "Anecdotal evidence", 2: "Documented evidence (interviews/data)"},
    },
    "market_size_evidence": {
        "weight": 0.12,
        "label": "Market Size Evidence",
        "scale": {0: "No sizing provided", 1: "Rough estimate", 2: "Sourced TAM/SAM/SOM"},
    },
    "product_maturity": {
        "weight": 0.12,
        "label": "Product Maturity",
        "scale": {0: "Idea only", 1: "Prototype/MVP", 2: "Live product with users"},
    },
    "traction": {
        "weight": 0.14,
        "label": "Traction",
        "scale": {0: "No users/customers", 1: "Early pilot users", 2: "Paying customers / recurring usage"},
    },
    "revenue_model_clarity": {
        "weight": 0.11,
        "label": "Revenue Model Clarity",
        "scale": {0: "Not defined", 1: "Roughly defined", 2: "Clear pricing and unit economics"},
    },
    "team_completeness": {
        "weight": 0.12,
        "label": "Team Completeness",
        "scale": {0: "Solo, no key skills covered", 1: "Partial team", 2: "Founding team covers core skills"},
    },
    "competitive_differentiation": {
        "weight": 0.12,
        "label": "Competitive Differentiation",
        "scale": {0: "No differentiation stated", 1: "Some differentiation", 2: "Clear, defensible differentiation"},
    },
}

_WEIGHT_SUM = round(sum(d["weight"] for d in DIMENSIONS.values()), 6)
if _WEIGHT_SUM != 1.0:
    raise AssertionError(f"funding readiness rubric weights must sum to 1.0, got {_WEIGHT_SUM}")

LEVEL_THRESHOLDS = [
    (70, "ready"),
    (40, "developing"),
    (0, "early_stage"),
]


def _level_for_score(score: float) -> str:
    for threshold, level in LEVEL_THRESHOLDS:
        if score >= threshold:
            return level
    return "early_stage"


def assess_funding_readiness(answers: dict[str, int | None]) -> dict:
    """Score a startup's funding readiness from user-provided 0/1/2 dimension answers.

    Unrecognized keys are ignored; missing or unrecognized-value dimensions score 0 and are
    listed in `missing_evidence`.
    """
    breakdown = []
    missing_evidence = []
    overall_score = 0.0

    for name, spec in DIMENSIONS.items():
        raw = answers.get(name)
        if raw is None or raw not in (0, 1, 2):
            missing_evidence.append(name)
            raw = 0
        normalized = raw / MAX_DIMENSION_SCORE
        weighted_contribution = normalized * spec["weight"] * 100
        overall_score += weighted_contribution
        breakdown.append(
            {
                "dimension": name,
                "label": spec["label"],
                "raw_score": raw,
                "max_score": MAX_DIMENSION_SCORE,
                "weight": spec["weight"],
                "weighted_contribution": round(weighted_contribution, 2),
                "scale_description": spec["scale"][raw],
            }
        )

    overall_score = round(overall_score, 2)
    breakdown.sort(key=lambda b: b["weighted_contribution"], reverse=True)

    return {
        "rubric_version": RUBRIC_VERSION,
        "overall_score": overall_score,
        "level": _level_for_score(overall_score),
        "breakdown": breakdown,
        "missing_evidence": missing_evidence,
        "disclaimer": (
            "This is a deterministic readiness assessment based on a hand-designed rubric, not a "
            "trained probability model and not investment advice."
        ),
    }
