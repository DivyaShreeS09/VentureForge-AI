"""Judge-owned venture-positioning resolution (Phase 0.5, corrected).

Two distinct outputs exist for a startup's category (see the approved architecture plan §2):

  - `model_category`: the untouched trained industry-classifier output (app.ml.predictor),
    relabeled here as technical evidence — never changed by this module.
  - `venture_positioning`: a founder-facing identity drawn from the broader controlled taxonomy
    (app.ml.positioning_taxonomy), resolved by `resolve_venture_positioning` below.

`resolve_venture_positioning` is the **sole final authority** for `venture_positioning`. Gemini
never decides the result directly — but per the mandatory correction to this module, the Judge's
own deterministic rule set *may* select Gemini's recommended domain in a genuinely ambiguous case,
under an explicit, fully pre-defined eligibility test (rule 4 below). This is a real, testable
branch of the Judge's own logic, not Gemini writing the field: every condition is checked against
already-computed, typed data (the taxonomy's own eligible candidates and scores), and
`gemini_recommendation.rationale` is never one of those conditions — see rule 6.

Deterministic rule set, applied in order:

1. `user_override` always wins outright.
2. No eligible taxonomy candidates -> fall back to `model_category`, `is_low_confidence=True`.
3. A clearly dominant taxonomy candidate (not ambiguous per
   `app.ml.positioning_taxonomy.taxonomy_is_ambiguous`) -> use it unchanged. Gemini is not
   consulted in this branch at all (and, per app.agents.nodes.venture_positioning_node, is not
   even invoked over the network when the taxonomy signal is this clean).
4. Ambiguous taxonomy -> Gemini's structured recommendation may influence the decision only when
   ALL of the following hold:
     a. `recommended_primary_domain` is itself one of the taxonomy's own eligible candidates
        (never an ineligible or zero-evidence domain — rule 5);
     b. that candidate's weighted score is within `AMBIGUITY_MARGIN` of taxonomy rank 1's score
        (i.e. it is itself part of the ambiguous top tier, not an arbitrary lower-ranked guess);
     c. `gemini_recommendation.confidence >= GEMINI_AGREEMENT_CONFIDENCE_FLOOR`;
     d. the recommendation already passed `GeminiPositioningRecommendation` schema/enum
        validation (guaranteed by construction — an invalid response never reaches this function
        at all, see app.agents.positioning_reviewer).
   If all four hold and Gemini's domain differs from taxonomy rank 1, the Judge deterministically
   selects it (`resolution_source="gemini_agreement_within_ambiguity_margin"`) and a
   `correction_rationale` is mandatory. If Gemini's domain matches rank 1, or any condition fails,
   the taxonomy's rank-1 candidate is kept, always flagged `is_low_confidence=True`.
6. `gemini_recommendation.rationale` is never read, parsed, or scored by any branch above — it is
   carried through purely as separate, display-only text (see app.agents.judge.synthesize).
7. Whenever the Judge selects a domain other than taxonomy rank 1 (rules 1 or 4), a non-empty
   `correction_rationale` is mandatory and `resolution_source` names the deterministic rule used.
"""

from __future__ import annotations

from app.ai.schemas import GeminiPositioningRecommendation
from app.ml.positioning_taxonomy import AMBIGUITY_MARGIN, taxonomy_is_ambiguous

GEMINI_AGREEMENT_CONFIDENCE_FLOOR = 0.6


def _find_candidate(candidates: list[dict], domain: str) -> dict | None:
    return next((c for c in candidates if c["domain"] == domain), None)


def build_model_category(industry_prediction: dict | None) -> dict | None:
    """Relabel the untouched industry-classifier output as `model_category` — see Output 1 in the
    architecture plan. No value here is changed; only the field names are normalized so the
    frontend/API can present it distinctly from `venture_positioning`.
    """
    if industry_prediction is None:
        return None
    return {
        "label": industry_prediction.get("predicted_industry"),
        "confidence": industry_prediction.get("confidence"),
        "top_3": [
            {"industry": industry_prediction.get("predicted_industry"), "confidence": industry_prediction.get("confidence")}
        ]
        + [
            {"industry": alt.get("industry"), "confidence": alt.get("confidence")}
            for alt in (industry_prediction.get("alternatives") or [])[:2]
        ],
        "local_explanation": industry_prediction.get("explanation"),
        "is_uncertain": industry_prediction.get("is_uncertain", False),
    }


def resolve_venture_positioning(
    taxonomy_result: dict,
    model_category: dict | None,
    gemini_recommendation: GeminiPositioningRecommendation | None = None,
    user_override: str | None = None,
) -> dict:
    """Decide the final `venture_positioning` and record why. Returns:

        {
          "venture_positioning": {primary_domain, secondary_domains, deployment_sectors,
                                   confidence, is_low_confidence, resolution_source},
          "correction_rationale": str | None,
        }
    """
    candidates = taxonomy_result.get("candidates", [])
    sectors = [s["sector"] for s in taxonomy_result.get("deployment_sectors", [])]

    if user_override is not None:
        secondary = [c["domain"] for c in candidates if c["domain"] != user_override][:2]
        return {
            "venture_positioning": {
                "primary_domain": user_override,
                "secondary_domains": secondary,
                "deployment_sectors": sectors,
                "confidence": 1.0,
                "is_low_confidence": False,
                "resolution_source": "user_override",
            },
            "correction_rationale": "Founder-provided correction overrides the deterministic/advisory resolution.",
        }

    if not candidates:
        # No taxonomy candidate met the eligibility bar at all — fall back to the raw model
        # category rather than guess a founder-facing identity, flagged low-confidence.
        fallback_label = (model_category or {}).get("label") or "General Consumer App"
        return {
            "venture_positioning": {
                "primary_domain": fallback_label,
                "secondary_domains": [],
                "deployment_sectors": sectors,
                "confidence": (model_category or {}).get("confidence", 0.0),
                "is_low_confidence": True,
                "resolution_source": "model_category_fallback",
            },
            "correction_rationale": (
                "No taxonomy candidate met the eligibility bar (at least 2 distinct matched "
                "concepts, or 1 high-specificity match); falling back to the raw model category "
                "rather than guessing a founder-facing identity, flagged low-confidence."
            ),
        }

    top = candidates[0]
    is_ambiguous = taxonomy_is_ambiguous(candidates)

    # Rule 3: a clearly dominant candidate is used unchanged. Gemini is never consulted here —
    # dominance alone settles it, and app.agents.nodes.venture_positioning_node doesn't even
    # invoke Gemini over the network in this case.
    if not is_ambiguous:
        return {
            "venture_positioning": {
                "primary_domain": top["domain"],
                "secondary_domains": [c["domain"] for c in candidates[1:3]],
                "deployment_sectors": sectors,
                "confidence": top["weighted_score"],
                "is_low_confidence": False,
                "resolution_source": "taxonomy_dominant",
            },
            "correction_rationale": None,
        }

    # Rule 4: taxonomy is ambiguous. Gemini's recommendation may only change the outcome if it
    # names an already-eligible candidate (rule 5), that candidate is itself within the ambiguity
    # margin of rank 1, and Gemini's own confidence clears the floor — all three checked against
    # typed, already-validated data; `rationale` is never inspected (rule 6).
    primary_domain = top["domain"]
    resolution_source = "taxonomy_ambiguous_fallback"
    correction_rationale: str | None = None

    if gemini_recommendation is not None:
        gemini_domain = gemini_recommendation.recommended_primary_domain
        gemini_candidate = _find_candidate(candidates, gemini_domain)
        within_margin = gemini_candidate is not None and (
            top["weighted_score"] - gemini_candidate["weighted_score"] <= AMBIGUITY_MARGIN
        )
        high_confidence = gemini_recommendation.confidence >= GEMINI_AGREEMENT_CONFIDENCE_FLOOR

        if gemini_candidate is not None and within_margin and high_confidence:
            if gemini_domain != top["domain"]:
                primary_domain = gemini_domain
                resolution_source = "gemini_agreement_within_ambiguity_margin"
                correction_rationale = (
                    f"Taxonomy signal was ambiguous (top candidate '{top['domain']}' scored "
                    f"{top['weighted_score']:.3f} vs. a near-tied '{gemini_domain}' at "
                    f"{gemini_candidate['weighted_score']:.3f}, within the {AMBIGUITY_MARGIN} "
                    f"ambiguity margin). Gemini's structured recommendation named an already-"
                    f"eligible candidate with confidence {gemini_recommendation.confidence:.2f} "
                    f"(>= {GEMINI_AGREEMENT_CONFIDENCE_FLOOR}) — the Judge Agent's deterministic "
                    "rule set selected it. Gemini did not decide this directly; it only satisfied "
                    "a pre-defined, deterministic eligibility rule the Judge Agent applies to any "
                    "input meeting these same conditions."
                )
            else:
                resolution_source = "taxonomy_gemini_confirmed"
                correction_rationale = (
                    "Gemini's structured recommendation agreed with the top-scoring taxonomy "
                    "candidate, strengthening an otherwise ambiguous decision."
                )
        # Any failed condition (ineligible domain, outside the ambiguity margin, or low
        # confidence) means Gemini's recommendation is disregarded entirely — fall through to the
        # plain ambiguous-taxonomy fallback below, exactly as if Gemini had not been invoked.

    if correction_rationale is None:
        correction_rationale = (
            "Taxonomy signal was ambiguous or below the confidence threshold; the top-scoring "
            "candidate was kept but flagged low-confidence rather than treated as certain."
        )

    chosen_candidate = _find_candidate(candidates, primary_domain) or top
    return {
        "venture_positioning": {
            "primary_domain": primary_domain,
            "secondary_domains": [c["domain"] for c in candidates if c["domain"] != primary_domain][:2],
            "deployment_sectors": sectors,
            "confidence": chosen_candidate["weighted_score"],
            "is_low_confidence": True,
            "resolution_source": resolution_source,
        },
        "correction_rationale": correction_rationale,
    }
