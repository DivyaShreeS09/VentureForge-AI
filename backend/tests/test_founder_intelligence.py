from app.agents.founder_intelligence import (
    build_critical_blind_spots,
    build_explainability_index,
    build_feature_gap_vs_market,
    build_founder_challenge_mode,
    build_founder_iq_report,
    build_funding_stage_ladder,
    build_investor_intelligence,
    build_investor_questions,
    build_moat_intelligence,
)

_BREAKDOWN_WITH_GAPS = [
    {"dimension": "problem_clarity", "label": "Problem Clarity", "state": "confirmed_positive", "raw_score": 2, "scale_description": "Specific, well-defined problem"},
    {"dimension": "traction", "label": "Traction", "state": "confirmed_negative", "raw_score": 0, "scale_description": "No users/customers"},
    {"dimension": "customer_pain_evidence", "label": "Evidence of Customer Pain", "state": "not_sure_yet", "raw_score": 0, "scale_description": "No evidence provided"},
    {"dimension": "revenue_model_clarity", "label": "Revenue Model Clarity", "state": "not_sure_yet", "raw_score": 0, "scale_description": "Not defined"},
    {"dimension": "market_size_evidence", "label": "Market Size Evidence", "state": "not_sure_yet", "raw_score": 0, "scale_description": "No sizing provided"},
    {"dimension": "team_completeness", "label": "Team Completeness", "state": "confirmed_negative", "raw_score": 0, "scale_description": "Solo, no key skills covered"},
    {"dimension": "competitive_differentiation", "label": "Competitive Differentiation", "state": "not_sure_yet", "raw_score": 0, "scale_description": "No differentiation stated"},
]
_FUNDING_ASSESSMENT_GAPS = {"level": "early_stage", "overall_score": 20.0, "breakdown": _BREAKDOWN_WITH_GAPS}

_BREAKDOWN_NO_GAPS = [
    {"dimension": name, "label": name.replace("_", " ").title(), "state": "confirmed_positive", "raw_score": 2, "scale_description": "Strong"}
    for name in ("problem_clarity", "traction", "customer_pain_evidence", "revenue_model_clarity", "market_size_evidence", "team_completeness", "competitive_differentiation")
]
_FUNDING_ASSESSMENT_NO_GAPS = {"level": "ready", "overall_score": 95.0, "breakdown": _BREAKDOWN_NO_GAPS}


def test_blind_spots_surface_every_gap_dimension():
    spots = build_critical_blind_spots(_FUNDING_ASSESSMENT_GAPS, {"known_competitors": ["Acme"]}, None)
    dimensions = {s["dimension"] for s in spots}
    assert "traction" in dimensions
    assert "customer_pain_evidence" in dimensions
    assert "revenue_model_clarity" in dimensions


def test_blind_spots_flag_missing_competitors_separately():
    spots = build_critical_blind_spots(_FUNDING_ASSESSMENT_NO_GAPS, {"known_competitors": []}, None)
    assert any(s["dimension"] == "named_competitors" for s in spots)


def test_blind_spots_flag_unvalidated_gtm():
    gtm = {"validation_roadmap": ["Talk to 10 restaurant owners about pricing."]}
    spots = build_critical_blind_spots(_FUNDING_ASSESSMENT_NO_GAPS, {"known_competitors": ["Acme"]}, gtm)
    gtm_spot = next(s for s in spots if s["dimension"] == "go_to_market_validation")
    assert "Talk to 10 restaurant owners" in gtm_spot["detail"]


def test_blind_spot_why_investors_care_is_not_generic_across_dimensions():
    """Consistency-audit regression: each dimension's why_investors_care must be distinct, not one
    reused template with only the label substituted."""
    spots = build_critical_blind_spots(_FUNDING_ASSESSMENT_GAPS, {"known_competitors": []}, None)
    reasons = [s["why_investors_care"] for s in spots if s["dimension"] != "named_competitors"]
    assert len(set(reasons)) == len(reasons)


def test_investor_questions_are_grounded_in_real_gap_dimensions():
    questions = build_investor_questions(_FUNDING_ASSESSMENT_GAPS, {"customer_type": "restaurant owners", "known_competitors": []}, None)
    assert questions
    assert all("grounded_in" in q and q["grounded_in"] for q in questions)
    assert any("restaurant owners" in q["question"] for q in questions)


def test_investor_questions_never_invent_a_competitor_name():
    questions = build_investor_questions(_FUNDING_ASSESSMENT_GAPS, {"known_competitors": []}, None)
    vc_question = next(q for q in questions if q["persona"] == "VC" and "stops them" in q["question"])
    assert "well-funded incumbent" in vc_question["question"]


def test_investor_questions_fallback_when_no_gaps_remain():
    questions = build_investor_questions(_FUNDING_ASSESSMENT_NO_GAPS, {}, None)
    assert len(questions) == 1
    assert "no open funding-readiness gaps" in questions[0]["grounded_in"].lower()


def test_challenge_mode_pairs_objection_with_concrete_next_step():
    objections = build_founder_challenge_mode(_FUNDING_ASSESSMENT_GAPS)
    assert objections
    for o in objections:
        assert o["how_to_overcome"]
        assert o["objection_category"].endswith("_objection")


def test_challenge_mode_fallback_when_no_gaps_remain():
    objections = build_founder_challenge_mode(_FUNDING_ASSESSMENT_NO_GAPS)
    assert len(objections) == 1
    assert objections[0]["objection_category"] == "execution_objection"


def test_moat_intelligence_never_fabricates_a_numeric_score():
    result = build_moat_intelligence("A generic tool with no special properties.", {}, None, [])
    for moat in result["moats"]:
        assert moat["tier"] in ("signal_found", "not_yet_established", "not_applicable")
        assert isinstance(moat["basis"], str) and moat["basis"]


def test_moat_intelligence_detects_real_keyword_signal():
    result = build_moat_intelligence(
        "A marketplace connecting freelancers with clients, with a proprietary dataset of past successful matches.",
        {}, None, [],
    )
    moats_by_type = {m["moat_type"]: m for m in result["moats"]}
    assert moats_by_type["network_effects"]["tier"] == "signal_found"
    assert moats_by_type["data_moat"]["tier"] == "signal_found"


def test_moat_not_established_basis_differs_per_moat_type():
    """Consistency-audit regression: the 'no signal' basis text must be moat-specific, not one
    repeated generic sentence."""
    result = build_moat_intelligence("A generic tool with no special properties.", {}, None, [])
    bases = [m["basis"] for m in result["moats"] if m["tier"] == "not_yet_established"]
    assert len(set(bases)) == len(bases)


def test_moat_reuses_regulatory_context_for_regulation_dimension():
    result = build_moat_intelligence(
        "A clinical decision support tool for hospital diagnostics.", {}, "Clinical Decision Support", [],
    )
    regulation = next(m for m in result["moats"] if m["moat_type"] == "regulation")
    assert regulation["tier"] == "signal_found"


def test_feature_gap_vs_market_unavailable_when_retrieval_disabled():
    result = build_feature_gap_vs_market({"recommended_capabilities": []}, {"comparative_intelligence": {"available": False}})
    assert result["available"] is False
    assert result["gaps"] == []


def test_feature_gap_vs_market_only_surfaces_real_overlap():
    feature_gap = {
        "recommended_capabilities": [
            {"label": "Anomaly Alerting", "reason": "why", "validation_question": "q?", "matching_concepts": ["alert", "anomaly"], "importance": "useful"},
        ]
    }
    venture_signals = {
        "comparative_intelligence": {
            "available": True,
            "common_terminology": {"available": True, "terms": [{"term": "alert"}], "provenance": ["VentureX"]},
        }
    }
    result = build_feature_gap_vs_market(feature_gap, venture_signals)
    assert result["available"] is True
    assert len(result["gaps"]) == 1
    assert result["gaps"][0]["capability"] == "Anomaly Alerting"


def test_funding_stage_ladder_progresses_with_real_signals():
    idea_stage = build_funding_stage_ladder({"level": "early_stage"}, {})
    assert idea_stage["current_stage"] == "idea"
    assert idea_stage["next_stage"] == "prototype"

    pilot_stage = build_funding_stage_ladder({"level": "developing"}, {"has_prototype": True, "has_traction": True})
    assert pilot_stage["current_stage"] == "pilot"
    assert pilot_stage["next_stage"] == "revenue"


def test_founder_iq_report_distinguishes_knowledge_gap_from_acknowledged_gap():
    report = build_founder_iq_report(_FUNDING_ASSESSMENT_GAPS)
    assert "knowledge gap" in report["category_scores"]["customers"]["understanding_level"]
    assert "acknowledged gap" in report["category_scores"]["execution"]["understanding_level"]
    assert "customers" in report["knowledge_gaps"]


def test_founder_iq_report_basis_is_not_identical_across_categories():
    """Consistency-audit regression: basis text must cite the specific dimension label(s), not a
    reused generic sentence shared across every category."""
    report = build_founder_iq_report(_FUNDING_ASSESSMENT_GAPS)
    bases = [s["basis"] for s in report["category_scores"].values()]
    assert len(set(bases)) == len(bases)


def test_founder_iq_report_strong_understanding_when_answers_are_solid():
    report = build_founder_iq_report(_FUNDING_ASSESSMENT_NO_GAPS)
    assert report["category_scores"]["business"]["understanding_level"] == "strong understanding"
    assert report["knowledge_gaps"] == []


def test_feature_gap_vs_market_ranks_core_capabilities_first():
    """Startup Domain Intelligence Sprint, Phase 4: priority_rank/business_impact reuse
    capability_library's own importance tier — core capabilities must sort before advanced ones."""
    feature_gap = {
        "recommended_capabilities": [
            {"label": "Advanced Thing", "reason": "why", "validation_question": "q?", "matching_concepts": ["adv"], "importance": "advanced"},
            {"label": "Core Thing", "reason": "why", "validation_question": "q?", "matching_concepts": ["core"], "importance": "core"},
        ]
    }
    venture_signals = {
        "comparative_intelligence": {
            "available": True,
            "common_terminology": {"available": True, "terms": [{"term": "adv"}, {"term": "core"}], "provenance": ["X"]},
        }
    }
    result = build_feature_gap_vs_market(feature_gap, venture_signals)
    assert result["gaps"][0]["capability"] == "Core Thing"
    assert result["gaps"][0]["priority_rank"] == "core"
    assert "prerequisite" in result["gaps"][0]["business_impact"]


def test_investor_intelligence_reuses_investor_questions_not_re_derived():
    questions = [{"persona": "VC", "question": "Why won't they keep using spreadsheets?", "grounded_in": "x"}]
    pack = {"common_competitive_advantages": ["A"], "common_failure_reasons": ["B"]}
    result = build_investor_intelligence(_FUNDING_ASSESSMENT_GAPS, questions, pack)
    assert result["likely_investor_objections"][0]["objection"] == questions[0]["question"]
    assert result["why_similar_ventures_succeed"]["category"] == "general_startup_knowledge"


def test_investor_intelligence_milestones_come_from_real_breakdown():
    result = build_investor_intelligence(_FUNDING_ASSESSMENT_GAPS, [], {"common_competitive_advantages": [], "common_failure_reasons": []})
    milestone_labels = [m["milestone"] for m in result["most_important_milestones"]]
    assert "Traction" in milestone_labels


def test_explainability_index_flags_retrieval_unavailable():
    source_attribution = {"feature_gap_vs_market": "cross-references retrieval"}
    index = build_explainability_index(source_attribution, venture_retrieval_available=False)
    assert "not enabled" in index[0]["confidence_note"]


def test_explainability_index_notes_retrieval_available():
    source_attribution = {"feature_gap_vs_market": "cross-references retrieval"}
    index = build_explainability_index(source_attribution, venture_retrieval_available=True)
    assert "citations" in index[0]["confidence_note"]
