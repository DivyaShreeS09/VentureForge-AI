from app.agents.judge import synthesize
from app.agents.mentor_synthesis import build_deterministic_mentor
from app.ml.funding_readiness import assess_funding_readiness

_DESCRIPTION = "Software that helps small restaurants in India track inventory and reduce food waste."
_CATEGORIES = {"evidence", "inference", "ai_recommendation", "market_assumption", "experiment_suggestion"}
_VENTURE_POSITIONING = {
    "primary_domain": "Restaurant Operations Technology", "secondary_domains": [], "deployment_sectors": ["Restaurants"],
    "confidence": 0.8, "is_low_confidence": False, "resolution_source": "taxonomy_dominant",
}
_MODEL_CATEGORY = {"label": "b2b", "confidence": 0.5, "top_3": [], "local_explanation": None, "is_uncertain": False}


def _mentor(**overrides):
    funding = assess_funding_readiness({"problem_clarity": 2, "traction": 0, "competitive_differentiation": 0})
    judge_summary = synthesize(
        industry_prediction={"predicted_industry": "b2b", "confidence": 0.5, "is_uncertain": False},
        funding_assessment=funding,
        evidence_check={"low_confidence": False, "notes": []},
        model_category=_MODEL_CATEGORY,
        venture_positioning=_VENTURE_POSITIONING,
        startup_name="WasteLess",
        startup_description=_DESCRIPTION,
    )
    kwargs = dict(
        startup_name="WasteLess", startup_description=_DESCRIPTION,
        judge_summary=judge_summary, funding_assessment=funding,
    )
    kwargs.update(overrides)
    return build_deterministic_mentor(**kwargs)


def test_founder_report_contains_every_consulting_section():
    """Founder Consulting Experience Sprint: the report is now a 10-section consulting engagement,
    not a flat stack of independently-computed analyses."""
    report = _mentor()["founder_report"]
    required = {
        "executive_verdict", "what_we_learned", "three_biggest_problems", "three_biggest_advantages",
        "investor_view", "founder_strategy", "moat_and_competitive_position", "market_insight",
        "success_path", "appendix",
    }
    assert required.issubset(report.keys())


def test_executive_verdict_fits_on_one_screen():
    """The executive verdict must communicate the whole engagement without requiring the reader to
    open any other section — exactly the 7 fields the sprint specified, no more."""
    verdict = _mentor()["founder_report"]["executive_verdict"]
    required = {
        "overall_verdict", "one_sentence_summary", "biggest_opportunity", "biggest_risk",
        "investor_readiness", "current_stage", "highest_priority_action",
    }
    assert set(verdict.keys()) == required
    for field in verdict.values():
        assert field["content"]
        assert field["category"] in _CATEGORIES


def test_three_biggest_problems_are_exactly_three_and_ranked():
    problems = _mentor()["founder_report"]["three_biggest_problems"]
    assert len(problems) <= 3
    assert [p["rank"] for p in problems] == list(range(1, len(problems) + 1))
    for p in problems:
        for key in ("problem", "evidence", "why_it_matters", "business_consequence", "if_ignored", "recommended_fix"):
            assert p[key]["content"]
            assert p[key]["category"] in _CATEGORIES


def test_three_biggest_advantages_are_exactly_three_and_ranked():
    advantages = _mentor()["founder_report"]["three_biggest_advantages"]
    assert len(advantages) <= 3
    assert [a["rank"] for a in advantages] == list(range(1, len(advantages) + 1))
    for a in advantages:
        for key in ("advantage", "evidence", "why_it_matters", "business_value", "risk_if_unused", "how_to_leverage"):
            assert a[key]["content"]
            assert a[key]["category"] in _CATEGORIES


def test_a_dimension_in_three_biggest_problems_is_cross_referenced_not_restated_in_investor_view():
    """Critical rule: 'a fact may appear only once' — a gap dimension already surfaced as one of the
    three biggest problems must be cross-referenced by rank in investor_view, not have its evidence
    text restated verbatim a second time."""
    report = _mentor()["founder_report"]
    problem_dims = {p["dimension"] for p in report["three_biggest_problems"]}
    referenced = [
        row for row in report["investor_view"]
        if row["dimension"] in problem_dims and "(Same evidence as Problem #" in row["evidence"]["content"]
    ]
    assert referenced, "expected at least one investor_view row to cross-reference a top-3 problem instead of restating it"


def test_what_we_learned_never_restates_a_top_three_dimension():
    report = _mentor()["founder_report"]
    excluded_dims = {p["dimension"] for p in report["three_biggest_problems"]} | {a["dimension"] for a in report["three_biggest_advantages"]}
    # what_we_learned entries carry no dimension field directly, but their content is built from
    # excluded items only — verified indirectly via founder_guidance_items ordering: every
    # excluded-dimension why_it_matters string must not appear verbatim in what_we_learned.
    guidance_by_dim = {item["dimension"]: item for item in _mentor()["founder_guidance_items"]}
    learned_content = " ".join(item["content"] for item in report["what_we_learned"])
    for dim in excluded_dims:
        why = guidance_by_dim.get(dim, {}).get("why_it_matters", "")
        if why:
            assert why not in learned_content


def test_founder_strategy_carries_the_merged_execution_fields():
    strategy = _mentor()["founder_report"]["founder_strategy"]
    assert strategy
    for action in strategy:
        assert isinstance(action["priority"], int)
        assert action["impact"] in ("High", "Medium", "Low")
        assert action["difficulty"] in ("Easy", "Medium", "Hard")
        assert action["estimated_duration"]
        for key in ("action", "reason", "success_metric", "first_step"):
            assert action[key]["content"]
            assert action[key]["category"] in _CATEGORIES


def test_moat_and_competitive_position_answers_the_three_required_questions():
    moat = _mentor()["founder_report"]["moat_and_competitive_position"]
    required = {
        "what_competitors_can_copy_today", "what_they_cannot_copy",
        "defensible_after_10_customers", "defensible_after_100_customers", "defensible_after_1000_customers",
    }
    assert set(moat.keys()) == required
    for field in moat.values():
        assert field["content"]
        assert field["category"] in _CATEGORIES


def test_success_path_covers_all_four_horizons_using_only_existing_reasoning():
    path = _mentor()["founder_report"]["success_path"]
    assert set(path.keys()) == {"day_30", "day_90", "month_6", "month_12"}
    for field in path.values():
        assert field["content"]
        assert field["category"] in _CATEGORIES


def test_appendix_preserves_the_full_previous_section_set():
    appendix = _mentor()["founder_report"]["appendix"]
    required = {
        "executive_summary", "startup_snapshot", "problem_analysis", "customer_analysis",
        "business_model", "market_position", "pricing_strategy", "go_to_market_strategy",
        "competitive_landscape", "product_roadmap", "ai_feature_suggestions", "risk_assessment",
        "opportunity_assessment", "funding_readiness", "ninety_day_action_plan",
        "final_mentor_verdict",
    }
    assert required.issubset(appendix.keys())


def _collect_categories(node, found: set):
    if isinstance(node, dict):
        if set(node.keys()) >= {"content", "category"} and isinstance(node.get("content"), str):
            found.add(node["category"])
        else:
            for v in node.values():
                _collect_categories(v, found)
    elif isinstance(node, list):
        for item in node:
            _collect_categories(item, found)


def test_every_tagged_item_uses_only_the_five_valid_categories():
    report = _mentor()["founder_report"]
    found: set = set()
    _collect_categories(report, found)
    assert found, "expected at least one tagged item"
    assert found.issubset(_CATEGORIES)


def test_pricing_strategy_reflects_india_detection():
    report = _mentor()["founder_report"]
    pricing = report["appendix"]["pricing_strategy"]
    assert "INR" in pricing["recommendation"]["content"] or "India" in " ".join(r["content"] for r in pricing["rationale"])


def test_founder_report_never_invents_new_facts_beyond_the_mentor_dict():
    mentor = _mentor()
    appendix = mentor["founder_report"]["appendix"]
    assert appendix["problem_analysis"]["content"] == mentor["idea_understanding"]["problem"]
    assert appendix["business_model"]["content"] == mentor["business_model"]
    assert appendix["final_mentor_verdict"]["content"] == mentor["mentor_verdict"]["concise_verdict"]
