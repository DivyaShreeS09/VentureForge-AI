"""CLI entrypoint for the mentor prototype (Phase -1 of the approved architecture plan).

Usage (from the repo root):
    python -m ml.prototypes.mentor_prototype.run_case --case campus
    python -m ml.prototypes.mentor_prototype.run_case --all

Prints real, generated JSON output for one or all of the 5 golden cases — nothing here is hand
-authored prose. Not imported by, and does not modify, any backend/frontend/production file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CASES_DIR = Path(__file__).resolve().parent / "cases"

# Reuse the real trained industry classifier for `model_category` — genuinely real ML output, not
# simulated. Requires backend/ on sys.path, mirroring backend's own repo-root sys.path pattern.
if str(_REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "backend"))

from app.ml.predictor import predict_industry  # noqa: E402

from .gemini_reviewer import review as gemini_review  # noqa: E402
from .hypothesis_engine import build_hypotheses_for_gaps  # noqa: E402
from .judge_rules import resolve_venture_positioning  # noqa: E402

_DIMENSION_LABELS = {
    "problem_clarity": "Problem Clarity",
    "customer_pain_evidence": "Evidence of Customer Pain",
    "market_size_evidence": "Market Size Evidence",
    "product_maturity": "Product Maturity",
    "traction": "Traction",
    "revenue_model_clarity": "Revenue Model Clarity",
    "team_completeness": "Team Completeness",
    "competitive_differentiation": "Competitive Differentiation",
}


def run_case(case_name: str) -> dict:
    fixture = json.loads((_CASES_DIR / f"{case_name}.json").read_text())
    name, description, evidence = fixture["name"], fixture["description"], fixture["evidence"]

    ml_result = predict_industry(name, description)
    model_category = {
        "label": ml_result["predicted_industry"],
        "confidence": ml_result["confidence"],
        "top_3": [{"industry": ml_result["predicted_industry"], "confidence": ml_result["confidence"]}]
        + [{"industry": a["industry"], "confidence": a["confidence"]} for a in ml_result["alternatives"][:2]],
        "is_uncertain": ml_result["is_uncertain"],
    }

    positioning_result = resolve_venture_positioning(description, model_category, gemini_review)
    primary_domain = positioning_result["venture_positioning"]["primary_domain"]

    weaknesses = []
    strengths = []
    not_sure_yet_dims = []
    for dim, answer in evidence.items():
        state = answer["state"]
        label = _DIMENSION_LABELS[dim]
        if state == "confirmed_negative":
            weaknesses.append(f"{label}: founder confirmed this is not yet in place.")
        elif state == "confirmed_positive" and answer.get("severity") == 2:
            strengths.append(f"{label}: strong evidence provided.")
        elif state == "not_sure_yet":
            not_sure_yet_dims.append(dim)
        # not_applicable dimensions are intentionally excluded from both scoring and both lists.

    hypotheses = build_hypotheses_for_gaps(not_sure_yet_dims, primary_domain)

    return {
        "case": case_name,
        "input": {"name": name, "description": description},
        **positioning_result,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "suggested_possibilities": hypotheses,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--case", choices=[p.stem for p in _CASES_DIR.glob("*.json")])
    group.add_argument("--all", action="store_true")
    args = parser.parse_args()

    cases = [p.stem for p in sorted(_CASES_DIR.glob("*.json"))] if args.all else [args.case]
    results = {case: run_case(case) for case in cases}
    print(json.dumps(results if args.all else results[cases[0]], indent=2, default=str))


if __name__ == "__main__":
    main()
