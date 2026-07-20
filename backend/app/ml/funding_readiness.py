"""Transparent, deterministic funding-readiness rubric.

No public dataset with a defensible funding-readiness target was identified (see
ml/DATASETS.md) — this is a hand-designed scoring rubric, not a trained model, and must never be
described as one. It is explicitly a "readiness assessment," not a probability of receiving
funding. The design is intentionally centralized and versioned so it can be swapped for a
supervised model later without changing its calling contract.

Each dimension carries one of four explicit evidence states (see `EvidenceState`), replacing the
old nullable 0/1/2 model: `confirmed_positive` (evidence exists, still scored 1/2 for quality),
`confirmed_negative` (the founder affirms this genuinely doesn't exist yet — the *only* state that
may ever surface as a weakness elsewhere, e.g. in app.agents.judge), `not_sure_yet` (never a
weakness — routed to the Hypothesis Engine, app.agents.hypothesis_engine), and `not_applicable`
(excluded from scoring entirely; the remaining applicable dimensions' weights are renormalized so
opting a dimension out never lowers the maximum attainable score).
"""

from __future__ import annotations

from enum import Enum

RUBRIC_VERSION = "v1"
MAX_DIMENSION_SCORE = 2


class EvidenceState(str, Enum):
    CONFIRMED_POSITIVE = "confirmed_positive"
    CONFIRMED_NEGATIVE = "confirmed_negative"
    NOT_SURE_YET = "not_sure_yet"
    NOT_APPLICABLE = "not_applicable"


_VALID_STATES = {s.value for s in EvidenceState}


def normalize_evidence_answer(raw: object) -> dict:
    """Normalize one dimension's raw answer into `{"state": <EvidenceState value>, "severity":
    int | None}`. Accepts the current `{state, severity}` object directly, or a legacy 0/1/2/null
    integer for backward compatibility with startups submitted before the four-state model
    existed — used both at the API schema boundary (app.schemas.startup.FundingAnswers) and again
    here for defense-in-depth against any stored/direct-call data that predates that schema.

    Legacy mapping (preserves the old scoring behavior exactly): missing/`None`/anything
    unrecognized -> `not_sure_yet` (an unanswered dimension was always a gap, never a confirmed
    absence); legacy `0` -> `confirmed_negative` (the old UI's explicit "no evidence" choice);
    legacy `1`/`2` -> `confirmed_positive` with that severity.
    """
    if isinstance(raw, dict):
        state = raw.get("state")
        state = state.value if isinstance(state, EvidenceState) else state
        if state not in _VALID_STATES:
            return {"state": EvidenceState.NOT_SURE_YET.value, "severity": None}
        severity = raw.get("severity")
        if state == EvidenceState.CONFIRMED_POSITIVE.value:
            severity = severity if severity in (1, 2) else 1
        else:
            severity = None
        return {"state": state, "severity": severity}
    if raw is None:
        return {"state": EvidenceState.NOT_SURE_YET.value, "severity": None}
    if raw == 0:
        return {"state": EvidenceState.CONFIRMED_NEGATIVE.value, "severity": None}
    if raw in (1, 2):
        return {"state": EvidenceState.CONFIRMED_POSITIVE.value, "severity": raw}
    return {"state": EvidenceState.NOT_SURE_YET.value, "severity": None}

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


def assess_funding_readiness(answers: dict[str, object]) -> dict:
    """Score a startup's funding readiness from the user's per-dimension evidence answers.

    Each answer is normalized via `normalize_evidence_answer` (accepts either the current
    `{state, severity}` object or a legacy 0/1/2/null integer). Unrecognized dimension keys in
    `answers` are ignored.

    Scoring by state: `confirmed_positive` contributes its severity (1 or 2) as today;
    `confirmed_negative` and `not_sure_yet` both contribute 0 (no favourable assumption for
    unconfirmed evidence) but only `not_sure_yet` is listed in `missing_evidence` — a
    `confirmed_negative` is a real, founder-affirmed answer, not a gap, and is surfaced as a
    genuine weakness elsewhere (see app.agents.judge), never routed to the Hypothesis Engine.
    `not_applicable` dimensions are excluded entirely: their weight is redistributed across the
    remaining applicable dimensions so opting a dimension out can never lower the maximum
    attainable score.
    """
    normalized = {name: normalize_evidence_answer(answers.get(name)) for name in DIMENSIONS}
    applicable_weight_sum = sum(
        spec["weight"] for name, spec in DIMENSIONS.items()
        if normalized[name]["state"] != EvidenceState.NOT_APPLICABLE.value
    ) or 1.0

    breakdown = []
    missing_evidence = []
    overall_score = 0.0

    for name, spec in DIMENSIONS.items():
        entry = normalized[name]
        state = entry["state"]

        if state == EvidenceState.NOT_APPLICABLE.value:
            breakdown.append(
                {
                    "dimension": name,
                    "label": spec["label"],
                    "state": state,
                    "raw_score": None,
                    "max_score": MAX_DIMENSION_SCORE,
                    "weight": 0.0,
                    "weighted_contribution": 0.0,
                    "scale_description": "Not applicable to this venture",
                }
            )
            continue

        raw = entry["severity"] if state == EvidenceState.CONFIRMED_POSITIVE.value else 0
        renormalized_weight = spec["weight"] / applicable_weight_sum
        weighted_contribution = (raw / MAX_DIMENSION_SCORE) * renormalized_weight * 100
        overall_score += weighted_contribution

        if state == EvidenceState.NOT_SURE_YET.value:
            missing_evidence.append(name)

        breakdown.append(
            {
                "dimension": name,
                "label": spec["label"],
                "state": state,
                "raw_score": raw,
                "max_score": MAX_DIMENSION_SCORE,
                "weight": round(renormalized_weight, 6),
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
