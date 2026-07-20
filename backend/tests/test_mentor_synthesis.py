from app.agents.founder_guidance import build_founder_guidance_items
from app.agents.mentor_schemas import MentorInterpretation
from app.agents.mentor_synthesis import build_deterministic_mentor

_FUNDING_ASSESSMENT = {
    "rubric_version": "v1",
    "overall_score": 35.0,
    "level": "early_stage",
    "breakdown": [
        {"dimension": "problem_clarity", "label": "Problem Clarity", "state": "confirmed_positive", "raw_score": 2, "max_score": 2, "weight": 0.14, "weighted_contribution": 14.0, "scale_description": "Specific, well-defined problem"},
        {"dimension": "traction", "label": "Traction", "state": "confirmed_negative", "raw_score": 0, "max_score": 2, "weight": 0.14, "weighted_contribution": 0.0, "scale_description": "No users/customers"},
        {"dimension": "customer_pain_evidence", "label": "Evidence of Customer Pain", "state": "confirmed_negative", "raw_score": 0, "max_score": 2, "weight": 0.13, "weighted_contribution": 0.0, "scale_description": "No evidence provided"},
        {"dimension": "revenue_model_clarity", "label": "Revenue Model Clarity", "state": "not_sure_yet", "raw_score": 0, "max_score": 2, "weight": 0.11, "weighted_contribution": 0.0, "scale_description": "Not defined"},
        {"dimension": "market_size_evidence", "label": "Market Size Evidence", "state": "not_sure_yet", "raw_score": 0, "max_score": 2, "weight": 0.12, "weighted_contribution": 0.0, "scale_description": "No sizing provided"},
    ],
    "missing_evidence": ["revenue_model_clarity", "market_size_evidence"],
    "disclaimer": "deterministic rubric",
}

_JUDGE_SUMMARY = {
    "strengths": ["Problem Clarity: Specific, well-defined problem"],
    "weaknesses": ["Traction: No users/customers", "Evidence of Customer Pain: No evidence provided"],
    "missing_evidence": ["Market Size Evidence", "Revenue Model Clarity"],
    "suggested_possibilities": [
        {"source_dimension": "revenue_model_clarity", "suggestion_label": "possibility", "starting_hypothesis": "x", "assumptions": [], "alternatives": [], "validation_task": "y"},
    ],
    "model_category": {"label": "b2b", "confidence": 0.5, "top_3": [], "local_explanation": None, "is_uncertain": False},
    "venture_positioning": {
        "primary_domain": "Restaurant Operations Technology", "secondary_domains": [], "deployment_sectors": ["Restaurants"],
        "confidence": 0.8, "is_low_confidence": False, "resolution_source": "taxonomy_dominant",
    },
    "founder_guidance_items": build_founder_guidance_items(_FUNDING_ASSESSMENT),
}


def _build(**overrides):
    kwargs = dict(
        startup_name="WasteLess",
        startup_description="Software that helps small restaurants track inventory and reduce food waste.",
        judge_summary=_JUDGE_SUMMARY,
        funding_assessment=_FUNDING_ASSESSMENT,
    )
    kwargs.update(overrides)
    return build_deterministic_mentor(**kwargs)


def test_output_validates_against_the_mentor_schema():
    result = _build()
    validated = MentorInterpretation.model_validate(result)
    assert validated.source == "deterministic"


def test_idea_understanding_uses_submitted_fields():
    result = _build()
    assert "WasteLess" in result["idea_understanding"]["summary"]
    assert "Restaurant Operations Technology" in result["idea_understanding"]["business_context"]


def test_confirmed_strengths_carry_through_unchanged():
    result = _build()
    assert result["strengths"] == ["Problem Clarity: Specific, well-defined problem"]


def test_real_weaknesses_is_a_deprecated_passthrough_not_merged():
    """Phase 1 correction: `real_weaknesses` is deprecated/backward-compat only — no merging, no
    coaching logic lives here anymore. See founder_guidance_items for the structured replacement.
    """
    result = _build()
    assert result["real_weaknesses"] == _JUDGE_SUMMARY["weaknesses"]


def test_hypotheses_become_suggested_possibilities_not_weaknesses():
    result = _build()
    assert result["suggested_possibilities"] == _JUDGE_SUMMARY["suggested_possibilities"]
    assert not any("Revenue Model Clarity" in w for w in result["real_weaknesses"])


def test_founder_guidance_items_never_use_confirmed_risk_for_todays_dimensions():
    """confirmed_negative must never automatically mean confirmed_risk — see
    app.agents.founder_guidance. None of today's 8 rubric dimensions ever produce that category."""
    result = _build()
    categories = {item["category"] for item in result["founder_guidance_items"]}
    assert "confirmed_risk" not in categories


def test_founder_guidance_items_stage_aware_examples():
    """Locks in the four explicit stage-aware examples from the corrected plan."""
    result = _build()
    by_dimension = {item["dimension"]: item for item in result["founder_guidance_items"]}
    # No traction at idea/prototype stage -> validation opportunity, not a bare risk label.
    assert by_dimension["traction"]["category"] == "validation_opportunity"
    # Unknown/undefined pricing -> a discovery/pricing task.
    assert by_dimension["revenue_model_clarity"]["category"] == "discovery_question"


def test_founder_guidance_item_has_required_fields():
    result = _build()
    required = {
        "dimension", "category", "status", "title", "observation", "why_it_matters",
        "next_step", "example", "priority", "evidence_state", "source",
    }
    for item in result["founder_guidance_items"]:
        assert required <= set(item)
        assert "_weight" not in item
        assert item["category"] in {
            "strength", "improvement_opportunity", "discovery_question",
            "validation_opportunity", "confirmed_risk", "future_enhancement",
        }


def test_feature_gap_analysis_from_controlled_library():
    result = _build()
    gap = result["feature_gap_analysis"]
    assert {"present_capabilities", "recommended_capabilities", "premature_capabilities", "not_relevant_capabilities"} <= set(gap)


def test_mvp_recommendation_is_dependency_aware_and_scoped():
    result = _build()
    mvp = result["mvp_recommendation"]
    assert "pos_integration" not in mvp["included_capabilities"]
    assert len(mvp["included_capabilities"]) <= 2


def test_low_confidence_positioning_produces_no_premature_mvp():
    low_confidence_judge = {
        **_JUDGE_SUMMARY,
        "venture_positioning": {**_JUDGE_SUMMARY["venture_positioning"], "is_low_confidence": True},
    }
    result = _build(judge_summary=low_confidence_judge)
    assert result["mvp_recommendation"]["included_capabilities"] == []


def test_validation_actions_precede_implementation_when_evidence_is_weak():
    result = _build()
    assert len(result["validation_plan"]) >= 1
    assert result["validation_plan"][0]["priority"] == 1
    # Confirmed-negative gaps (traction/customer_pain) must be validated ahead of not_sure_yet gaps.
    dims = [a["source_gap"] for a in result["validation_plan"]]
    assert dims.index("traction") < dims.index("market_size_evidence")


def test_roadmap_has_three_dependency_aware_periods():
    result = _build()
    periods = [p["period"] for p in result["roadmap_30_60_90"]]
    assert periods == ["days_1_30", "days_31_60", "days_61_90"]
    assert "discovery" in result["roadmap_30_60_90"][0]["focus"].lower()


def test_top_next_actions_between_3_and_5():
    result = _build()
    assert 3 <= len(result["top_next_actions"]) <= 5


def test_evidence_and_uncertainty_includes_all_required_caveats():
    result = _build()
    evidence = result["evidence_and_uncertainty"]
    assert evidence["model_category_caveat"]
    assert evidence["historical_pattern_signal_caveat"]
    assert isinstance(evidence["low_confidence_flags"], list)
    assert evidence["user_supplied_vs_suggested_summary"]
    assert evidence["unresolved_questions"] == ["Market Size Evidence", "Revenue Model Clarity"]


def test_no_field_disappears_when_optional_agent_outputs_are_missing():
    result = _build(
        success_prediction=None, revenue_estimate=None, market_intelligence=None,
        competitor_analysis=None, customer_personas=None, business_model=None, market_evidence=None,
    )
    validated = MentorInterpretation.model_validate(result)
    assert validated.mvp_recommendation is not None
    assert validated.roadmap_30_60_90
    assert validated.evidence_and_uncertainty is not None
