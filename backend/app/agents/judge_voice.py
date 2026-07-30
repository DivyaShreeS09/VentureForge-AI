"""Founder-facing narration helpers (Sprint 8 — "The Mentor").

Every function here turns an already-computed deterministic/ML output into mentor-voiced prose.
Nothing here invents a fact, changes a score, or reclassifies anything — these are pure
presentation/reasoning-quality rewrites over data other modules already produced. The goal is that
no sentence here ever exposes a rubric label, a quoted model prediction, a raw score, or backend
terminology (see the Sprint 8 audit for the full list of prior offenders this replaces).
"""

from __future__ import annotations

from app.agents.venture_vocabulary import readable_label as _normalize_acronym
from app.agents.venture_vocabulary import with_article

_READINESS_PHRASE: dict[str, str] = {
    "ready": "genuinely ready for investor conversations",
    "developing": "making real progress, with a handful of gaps still worth closing before you pitch",
    "early_stage": "still early — the right next moves are about validating the idea, not pitching it yet",
}


def _readable_label(label: str) -> str:
    return _normalize_acronym(label.replace("_", " "))


def build_overall_assessment(
    industry_prediction: dict | None,
    funding_assessment: dict,
    evidence_check: dict,
    venture_positioning: dict | None = None,
    model_category: dict | None = None,
) -> str:
    """The one paragraph a founder sees summarizing where things stand — mentor voice, not a
    rubric readout. Reads `industry_prediction`/`funding_assessment`/`evidence_check` for their
    real values only; never quotes a model label or prints a raw score.

    Critical Fix (Product Intelligence Sprint): this used to narrate directly from the raw,
    uncorrected `industry_prediction['predicted_industry']` even when the Judge's own
    `venture_positioning` resolution (app.agents.venture_positioning.resolve_venture_positioning)
    had already recovered to a better-reasoned label — so a weak classifier guess could still
    dominate the founder-facing summary sentence even though it never dominates the structured
    data. `venture_positioning` is now the primary source whenever it is available; the raw
    `industry_prediction` path below only remains for callers that don't yet compute it. When the
    Judge's own resolution is itself flagged low-confidence, this now says so honestly and names
    the real alternative(s) it has on hand — never a single confident label presented as fact.
    """
    # A `model_category_fallback` resolution with no `model_category` behind it at all means the
    # industry classifier was fully unavailable and `resolve_venture_positioning` substituted its
    # own hardcoded placeholder ("General Consumer App") rather than any real signal — that must
    # never be narrated as a stated fact (regression caught by
    # tests/test_error_handling.py::test_industry_classifier_unavailable_does_not_crash_analyze).
    # Every other resolution_source (taxonomy-based, Gemini-recovered, user-overridden, or a
    # `model_category_fallback` backed by a real — if weak — classifier prediction) is genuine
    # signal worth narrating, hedged appropriately below.
    is_placeholder_fallback = (
        venture_positioning is not None
        and venture_positioning.get("resolution_source") == "model_category_fallback"
        and not model_category
    )
    if venture_positioning is not None and venture_positioning.get("primary_domain") and not is_placeholder_fallback:
        primary = _readable_label(venture_positioning["primary_domain"])
        is_low_confidence = bool(venture_positioning.get("is_low_confidence"))
        alternatives = [_readable_label(d) for d in (venture_positioning.get("secondary_domains") or []) if d]
        if not alternatives and venture_positioning.get("resolution_source") == "model_category_fallback":
            # The Judge fell all the way back to the raw classifier with no taxonomy or Gemini
            # corroboration — its own next-ranked guesses are the only real alternatives on hand.
            alternatives = [
                _readable_label(t["industry"])
                for t in (model_category or {}).get("top_3", [])[1:3]
                if t.get("industry")
            ]

        industry_sentence = f"This reads to me as {with_article(primary)} venture"
        if is_low_confidence:
            if alternatives:
                alt_text = " or ".join(alternatives)
                industry_sentence += (
                    f", though I'm not fully certain — {alt_text} read plausibly too from what's "
                    "here, so I'd treat this as a working hypothesis rather than a settled fact"
                )
            else:
                industry_sentence += ", though I'd hold that loosely until more evidence comes in"
        industry_sentence += "."
    elif industry_prediction is not None:
        # Backward-compatible path for any caller that hasn't computed venture_positioning yet.
        industry_sentence = (
            f"This reads to me as {with_article(_readable_label(industry_prediction['predicted_industry']))} venture"
        )
        if industry_prediction.get("is_uncertain"):
            industry_sentence += ", though I'd hold that loosely until more evidence comes in"
        industry_sentence += "."
    else:
        industry_sentence = "I couldn't confidently place this in a specific industry from what was submitted — that's fine, it just means the read below leans more on your own answers than on a pattern match."

    readiness_phrase = _READINESS_PHRASE.get(funding_assessment["level"], _readable_label(funding_assessment["level"]))
    readiness_sentence = f"Overall, you're {readiness_phrase}."

    caveat = ""
    if evidence_check.get("low_confidence"):
        caveat = " I'd treat the industry read above as a working hypothesis rather than a settled fact for now."

    return f"{industry_sentence} {readiness_sentence}{caveat}".strip()
