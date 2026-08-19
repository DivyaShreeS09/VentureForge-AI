from app.agents.judge_voice import build_overall_assessment


def _funding(level="developing"):
    return {"level": level}


def _evidence(low_confidence=False):
    return {"low_confidence": low_confidence}


def test_confident_venture_positioning_states_the_domain_plainly():
    vp = {"primary_domain": "fintech", "is_low_confidence": False, "secondary_domains": []}
    text = build_overall_assessment(
        {"predicted_industry": "fintech", "confidence": 0.9}, _funding(), _evidence(), venture_positioning=vp
    )
    assert "This reads to me as a fintech venture" in text
    assert "though" not in text


def test_low_confidence_positioning_hedges_and_names_alternatives_instead_of_stating_fact():
    """The exact bug this fix targets: a low-confidence venture_positioning must never be narrated
    as a plain fact ('This reads to me as a fintech venture.') — it must hedge and, when real
    alternatives are known, name them."""
    vp = {
        "primary_domain": "Food-Cost Management",
        "is_low_confidence": True,
        "secondary_domains": ["Restaurant Operations Technology"],
        "resolution_source": "gemini_recovery_no_taxonomy_match",
    }
    text = build_overall_assessment(
        {"predicted_industry": "fintech", "confidence": 0.24}, _funding(), _evidence(), venture_positioning=vp
    )
    assert "Food-Cost Management" in text
    assert "Restaurant Operations Technology" in text
    assert "not fully certain" in text
    # The raw classifier's discarded guess must never leak into the founder-facing sentence.
    assert "fintech venture" not in text


def test_low_confidence_model_category_fallback_surfaces_raw_alternatives():
    """When positioning fell all the way back to the raw classifier with no Gemini/taxonomy
    corroboration, its own next-ranked guesses are the only honest alternatives available — they
    must be surfaced rather than presenting the top guess alone as settled fact."""
    vp = {
        "primary_domain": "fintech",
        "is_low_confidence": True,
        "secondary_domains": [],
        "resolution_source": "model_category_fallback",
    }
    model_category = {
        "label": "fintech",
        "top_3": [
            {"industry": "fintech", "confidence": 0.335},
            {"industry": "b2b", "confidence": 0.288},
            {"industry": "consumer", "confidence": 0.116},
        ],
    }
    text = build_overall_assessment(
        {"predicted_industry": "fintech", "confidence": 0.335},
        _funding(),
        _evidence(),
        venture_positioning=vp,
        model_category=model_category,
    )
    assert "B2B" in text or "b2b" in text
    assert "consumer" in text
    assert "not fully certain" in text


def test_no_venture_positioning_falls_back_to_raw_industry_prediction():
    """Backward-compatible path: a caller that hasn't computed venture_positioning yet still gets
    the old behavior, unchanged."""
    text = build_overall_assessment(
        {"predicted_industry": "saas", "confidence": 0.9, "is_uncertain": False}, _funding(), _evidence()
    )
    assert "This reads to me as a saas venture" in text or "This reads to me as a SAAS venture" in text


def test_no_industry_prediction_and_no_positioning_discloses_absence():
    text = build_overall_assessment(None, _funding(), _evidence())
    assert "couldn't confidently place this in a specific industry" in text


def test_placeholder_fallback_with_no_model_category_still_discloses_absence():
    """Regression guard: when the classifier is fully unavailable, `resolve_venture_positioning`
    substitutes its own hardcoded placeholder ('General Consumer App') with no real model_category
    behind it. That placeholder must never be narrated as a stated industry fact — the honest
    'couldn't confidently place this' message must still win."""
    vp = {
        "primary_domain": "General Consumer App",
        "is_low_confidence": True,
        "secondary_domains": [],
        "resolution_source": "model_category_fallback",
    }
    text = build_overall_assessment(None, _funding(), _evidence(), venture_positioning=vp, model_category=None)
    assert "couldn't confidently place this in a specific industry" in text
    assert "General Consumer App" not in text
