from app.agents.knowledge_audit import audit_category_coverage, audit_knowledge_sources


def _tag(content, category="evidence"):
    return {"content": content, "category": category}


def test_classifies_known_sections_correctly():
    report = {
        "problem_analysis": _tag("A specific problem statement."),
        "competitive_landscape": {"similar_historical_ventures": [_tag("Acme is a similar venture.")]},
        "critical_blind_spots": [{"title": _tag("Traction"), "detail": _tag("No traction yet.")}],
    }
    result = audit_knowledge_sources(report)
    assert result["counts"]["deterministic_reasoning"] >= 1
    assert result["counts"]["retrieved_evidence"] >= 1
    assert result["unclassified_paths"] == []


def test_ai_reasoning_is_reported_as_zero_with_an_explicit_finding():
    report = {"problem_analysis": _tag("A specific problem statement.")}
    result = audit_knowledge_sources(report)
    assert result["counts"]["ai_reasoning"] == 0
    assert "founder_report is composed entirely from the deterministic" in result["finding_ai_reasoning_is_zero_percent"]


def test_unknown_section_is_flagged_not_silently_dropped():
    report = {"some_future_section_not_yet_mapped": _tag("New content.")}
    result = audit_knowledge_sources(report)
    assert result["counts"]["unsupported_generic_advice"] == 1
    assert "founder_report.some_future_section_not_yet_mapped" in result["unclassified_paths"]


def test_percentages_sum_to_roughly_one_hundred():
    report = {
        "problem_analysis": _tag("A."),
        "customer_analysis": _tag("B."),
        "ai_feature_suggestions": [_tag("C.")],
    }
    result = audit_knowledge_sources(report)
    assert abs(sum(result["percentages"].values()) - 100.0) < 0.5


def test_startup_benchmark_industry_positioning_uses_actual_tag_not_static_guess():
    retrieved = {"startup_benchmark": {"industry_positioning": _tag("Most similar ventures are foodtech.", "evidence")}}
    general = {"startup_benchmark": {"industry_positioning": _tag("No retrieval-backed pattern available.", "market_assumption")}}
    r1 = audit_knowledge_sources(retrieved)
    r2 = audit_knowledge_sources(general)
    assert r1["counts"]["retrieved_evidence"] == 1
    assert r2["counts"]["startup_knowledge"] == 1


def test_category_coverage_reports_real_counts_not_a_guess():
    """Master Startup Knowledge Base Sprint, Phase 7: category coverage must be computed from the
    actual taxonomy and the actual set of packs, not asserted as a fixed number."""
    coverage = audit_category_coverage()
    assert coverage["categories_with_dedicated_knowledge_pack"] <= coverage["categories_resolvable_by_taxonomy"]
    assert coverage["coverage_percentage"] == 100.0
    assert coverage["categories_missing_a_dedicated_pack"] == []


def test_knowledge_sources_result_includes_category_coverage_and_quality_measures():
    report = {"problem_analysis": _tag("A specific problem statement.")}
    result = audit_knowledge_sources(report)
    assert "category_coverage" in result
    assert result["knowledge_backed_advice_percentage"] == result["percentages"]["startup_knowledge"]
    assert result["retrieved_evidence_coverage_percentage"] == result["percentages"]["retrieved_evidence"]
    assert result["unsupported_advice_percentage"] == result["percentages"]["unsupported_generic_advice"]


def test_generic_advice_percentage_reuses_consistency_audit_when_provided():
    report = {
        "a": _tag("This could improve your product."),
        "b": _tag("A specific, real observation about this venture."),
    }
    consistency_result = {"generic_boilerplate_hits": [{"path": "founder_report.a", "phrase": "this could improve your product"}]}
    result = audit_knowledge_sources(report, consistency_audit_result=consistency_result)
    assert result["generic_advice_percentage"] == 50.0


def test_generic_advice_percentage_is_none_without_consistency_audit_result():
    report = {"problem_analysis": _tag("A specific problem statement.")}
    result = audit_knowledge_sources(report)
    assert result["generic_advice_percentage"] is None
