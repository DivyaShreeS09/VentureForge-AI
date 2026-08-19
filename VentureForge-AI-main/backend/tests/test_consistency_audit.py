from app.agents.consistency_audit import audit_founder_report


def _tag(content, category="evidence"):
    return {"content": content, "category": category}


def test_passes_a_clean_report():
    report = {
        "problem_analysis": _tag("A specific, well-defined problem statement here for testing."),
        "customer_analysis": _tag("A distinct sentence about the customer segment being targeted."),
    }
    result = audit_founder_report(report)
    assert result["passed"] is True
    assert result["invalid_category_tags"] == []
    assert result["duplicate_or_near_duplicate_pairs"] == []
    assert result["generic_boilerplate_hits"] == []


def test_flags_invalid_category_tag():
    report = {"problem_analysis": {"content": "Some text here about the problem statement.", "category": "not_a_real_category"}}
    result = audit_founder_report(report)
    assert result["passed"] is False
    assert "founder_report.problem_analysis" in result["invalid_category_tags"]


def test_flags_exact_duplicate_sentences_across_sections():
    duplicate_sentence = "This venture needs to validate its pricing model with real customers."
    report = {
        "section_a": _tag(duplicate_sentence),
        "section_b": _tag(duplicate_sentence),
    }
    result = audit_founder_report(report)
    assert result["passed"] is False
    pair = result["duplicate_or_near_duplicate_pairs"][0]
    assert pair.get("exact_duplicate") is True


def test_flags_near_duplicate_sentences_across_sections():
    report = {
        "section_a": _tag("Talk to five real restaurant owners about their current inventory process."),
        "section_b": _tag("Talk to five real restaurant owners about their current inventory workflow."),
    }
    result = audit_founder_report(report)
    assert result["passed"] is False
    assert len(result["duplicate_or_near_duplicate_pairs"]) == 1


def test_does_not_flag_sentences_with_ordinary_shared_vocabulary():
    report = {
        "section_a": _tag("Pricing should be validated with three prospective customers before launch."),
        "section_b": _tag("Competitive differentiation is unclear without naming a single alternative."),
    }
    result = audit_founder_report(report)
    assert result["duplicate_or_near_duplicate_pairs"] == []


def test_flags_generic_boilerplate_phrase():
    report = {"section_a": _tag("This could improve your product significantly over time.")}
    result = audit_founder_report(report)
    assert result["passed"] is False
    assert result["generic_boilerplate_hits"][0]["phrase"] == "this could improve your product"


def test_recursively_finds_tagged_items_in_nested_lists_and_dicts():
    report = {
        "nested": {
            "items": [
                _tag("First distinct sentence about the market opportunity here."),
                _tag("Second distinct sentence about the competitive landscape here."),
            ]
        }
    }
    result = audit_founder_report(report)
    assert result["n_tagged_items_checked"] == 2


def test_flags_a_specific_figure_not_tagged_as_evidence():
    report = {"pricing": _tag("Recommended price: $5917.42 per month.", "market_assumption")}
    result = audit_founder_report(report)
    assert len(result["unsupported_claims"]) == 1
    assert result["unsupported_claims"][0]["category"] == "market_assumption"


def test_does_not_flag_small_process_counts_as_unsupported_claims():
    report = {
        "roadmap": _tag("Talk to 5 people over the next 2 weeks about days 1-30.", "ai_recommendation"),
    }
    result = audit_founder_report(report)
    assert result["unsupported_claims"] == []


def test_evidence_tagged_figures_are_never_flagged():
    report = {"metric": _tag("Funding readiness score: 42.50 out of 100.", "evidence")}
    result = audit_founder_report(report)
    assert result["unsupported_claims"] == []


def test_flags_contradictory_negation_between_near_duplicate_sentences():
    report = {
        "a": _tag("Traction confirmed: real paying customers exist for this product right now.", "evidence"),
        "b": _tag("Traction not confirmed: no real paying customers exist for this product right now.", "evidence"),
    }
    result = audit_founder_report(report)
    assert len(result["possible_contradictions"]) == 1


def test_strict_category_breakdown_maps_five_tags_correctly():
    report = {
        "a": _tag("evidence sentence here about the venture status.", "evidence"),
        "b": _tag("inference sentence here about the venture status.", "inference"),
        "c": _tag("recommendation sentence here about the venture status.", "ai_recommendation"),
        "d": _tag("assumption sentence here about the venture status.", "market_assumption"),
        "e": _tag("experiment sentence here about the venture status.", "experiment_suggestion"),
    }
    result = audit_founder_report(report)
    breakdown = result["strict_category_breakdown"]
    assert breakdown == {"Evidence": 1, "Inference": 1, "Recommendation": 1, "Unknown": 1, "Experiment": 1}
