"""Deterministic Judge Agent decision rules for `venture_positioning` (prototype).

Neither the taxonomy resolver nor Gemini decides the final positioning — this module is the sole
authority, per the approved architecture. It reads only structured/typed fields from the Gemini
reviewer (never the rationale text) and applies one explicit rule set.
"""

from __future__ import annotations

from .taxonomy_matcher import extract_deployment_sectors, score_taxonomy, taxonomy_is_ambiguous

MAX_SECONDARY_DOMAINS = 2


def resolve_venture_positioning(
    description: str,
    model_category: dict,
    gemini_reviewer_fn,
    user_override: str | None = None,
) -> dict:
    """Runs the full resolution: deterministic taxonomy scoring, conditional advisory Gemini
    review, then the Judge's deterministic decision. Returns every intermediate signal distinctly
    — never collapsed into one field.
    """
    taxonomy_candidates = score_taxonomy(description)
    deployment_sectors = extract_deployment_sectors(description)

    needs_review = (
        model_category.get("is_uncertain", True)
        or taxonomy_is_ambiguous(taxonomy_candidates)
    )

    gemini_recommendation = None
    if needs_review and user_override is None:
        gemini_recommendation = gemini_reviewer_fn(description, model_category, taxonomy_candidates)

    top_taxonomy = taxonomy_candidates[0] if taxonomy_candidates else None
    correction_rationale = None

    if user_override is not None:
        primary_domain = user_override
        secondary_domains = [c["domain"] for c in taxonomy_candidates[1:1 + MAX_SECONDARY_DOMAINS]]
        correction_rationale = "Founder-submitted correction overrides the resolved positioning."
    elif not needs_review:
        # Taxonomy is unambiguous and the ML model itself was confident — no reviewer was invoked,
        # use the taxonomy top candidate directly.
        primary_domain = top_taxonomy["domain"] if top_taxonomy else "General Consumer App"
        secondary_domains = [c["domain"] for c in taxonomy_candidates[1:1 + MAX_SECONDARY_DOMAINS] if c["score"] > 0]
    elif gemini_recommendation is not None and top_taxonomy and gemini_recommendation["recommended_primary_domain"] == top_taxonomy["domain"]:
        # Reviewer agrees with the top taxonomy candidate -> confident resolution despite the
        # trigger condition.
        primary_domain = top_taxonomy["domain"]
        secondary_domains = list(dict.fromkeys(
            gemini_recommendation["recommended_secondary_domains"]
            + [c["domain"] for c in taxonomy_candidates[1:1 + MAX_SECONDARY_DOMAINS] if c["score"] > 0]
        ))[:MAX_SECONDARY_DOMAINS]
        correction_rationale = (
            f"Taxonomy top candidate and reviewer recommendation agreed on '{primary_domain}'."
        )
    elif gemini_recommendation is not None and gemini_recommendation["confidence"] >= 0.6:
        # Reviewer disagrees with taxonomy but is itself confident -> Judge prefers the reviewer's
        # structured recommendation, and records why.
        primary_domain = gemini_recommendation["recommended_primary_domain"]
        secondary_domains = gemini_recommendation["recommended_secondary_domains"][:MAX_SECONDARY_DOMAINS]
        top_label = top_taxonomy["domain"] if top_taxonomy else "none"
        correction_rationale = (
            f"Taxonomy top candidate ('{top_label}') and reviewer recommendation "
            f"('{primary_domain}') disagreed; reviewer confidence ({gemini_recommendation['confidence']:.2f}) "
            "cleared the threshold, so the Judge's rule set preferred it."
        )
    elif top_taxonomy and top_taxonomy["score"] > 0:
        # No confident reviewer signal (not invoked, or invoked but unconfident) -> fall back to
        # the taxonomy top candidate, flagged low-confidence rather than guessed.
        primary_domain = top_taxonomy["domain"]
        secondary_domains = [c["domain"] for c in taxonomy_candidates[1:1 + MAX_SECONDARY_DOMAINS] if c["score"] > 0]
        correction_rationale = (
            "No signal confidently resolved this — falling back to the strongest taxonomy match "
            "flagged low-confidence rather than guessing."
        )
    else:
        # Nothing matched at all -> honest low-confidence generic fallback, never fabricated.
        primary_domain = "General Consumer App"
        secondary_domains = []
        correction_rationale = (
            "No taxonomy candidate scored above zero and no confident reviewer recommendation "
            "was available — defaulted to the most generic category, flagged low-confidence."
        )

    is_low_confidence = needs_review and (
        gemini_recommendation is None or gemini_recommendation["confidence"] < 0.6
    ) and user_override is None

    return {
        "model_category": model_category,
        "taxonomy_candidates": taxonomy_candidates,
        "gemini_structured_recommendation": gemini_recommendation,
        "user_override": user_override,
        "venture_positioning": {
            "primary_domain": primary_domain,
            "secondary_domains": secondary_domains,
            "deployment_sectors": deployment_sectors,
        },
        "is_low_confidence": is_low_confidence,
        "correction_rationale": correction_rationale,
    }
