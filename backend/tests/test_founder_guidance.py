from app.agents.founder_guidance import build_founder_guidance_items, finalize_priority, score_item


def _breakdown_item(dimension, label, state, raw_score, weight, scale_description):
    return {
        "dimension": dimension, "label": label, "state": state, "raw_score": raw_score,
        "max_score": 2, "weight": weight, "weighted_contribution": 0.0, "scale_description": scale_description,
    }


def test_confirmed_positive_severity_2_is_strength():
    funding = {"breakdown": [_breakdown_item("problem_clarity", "Problem Clarity", "confirmed_positive", 2, 0.14, "Specific, well-defined problem")]}
    items = build_founder_guidance_items(funding)
    assert items[0]["category"] == "strength"


def test_confirmed_positive_severity_1_is_improvement_opportunity():
    funding = {"breakdown": [_breakdown_item("problem_clarity", "Problem Clarity", "confirmed_positive", 1, 0.14, "Problem stated but broad")]}
    items = build_founder_guidance_items(funding)
    assert items[0]["category"] == "improvement_opportunity"


def test_not_sure_yet_is_always_discovery_question():
    funding = {"breakdown": [_breakdown_item(dim, dim, "not_sure_yet", 0, 0.1, "x") for dim in (
        "problem_clarity", "customer_pain_evidence", "market_size_evidence", "product_maturity",
        "traction", "revenue_model_clarity", "team_completeness", "competitive_differentiation",
    )]}
    items = build_founder_guidance_items(funding)
    assert all(item["category"] == "discovery_question" for item in items)


def test_not_applicable_dimension_produces_no_item():
    funding = {"breakdown": [_breakdown_item("traction", "Traction", "not_applicable", None, 0.0, "Not applicable to this venture")]}
    assert build_founder_guidance_items(funding) == []


def test_confirmed_negative_never_maps_to_confirmed_risk_for_any_of_the_8_dimensions():
    dims = [
        "problem_clarity", "customer_pain_evidence", "market_size_evidence", "product_maturity",
        "traction", "revenue_model_clarity", "team_completeness", "competitive_differentiation",
    ]
    funding = {"breakdown": [_breakdown_item(dim, dim, "confirmed_negative", 0, 0.1, "x") for dim in dims]}
    items = build_founder_guidance_items(funding)
    assert all(item["category"] != "confirmed_risk" for item in items)


def test_stage_softens_language_without_changing_category():
    funding = {"breakdown": [_breakdown_item("traction", "Traction", "confirmed_negative", 0, 0.14, "No users/customers")]}
    idea_stage = build_founder_guidance_items(funding, market_evidence={"startup_stage": "Idea"})[0]
    growth_stage = build_founder_guidance_items(funding, market_evidence={"startup_stage": "Growth"})[0]
    assert idea_stage["category"] == growth_stage["category"] == "validation_opportunity"
    assert "completely normal this early on" in idea_stage["why_it_matters"]
    assert "completely normal this early on" not in growth_stage["why_it_matters"]


def test_priority_is_deterministic_and_1_indexed():
    funding = {
        "breakdown": [
            _breakdown_item("traction", "Traction", "confirmed_negative", 0, 0.14, "No users/customers"),
            _breakdown_item("problem_clarity", "Problem Clarity", "confirmed_positive", 2, 0.14, "Specific, well-defined problem"),
        ]
    }
    items = build_founder_guidance_items(funding)
    priorities = sorted(item["priority"] for item in items)
    assert priorities == list(range(1, len(items) + 1))
    # A validation_opportunity item must outrank a strength item.
    by_category = {item["category"]: item for item in items}
    assert by_category["validation_opportunity"]["priority"] < by_category["strength"]["priority"]


def test_required_fields_present_on_every_item():
    funding = {"breakdown": [_breakdown_item("traction", "Traction", "confirmed_negative", 0, 0.14, "No users/customers")]}
    required = {
        "dimension", "category", "status", "title", "observation", "why_it_matters",
        "next_step", "example", "priority", "evidence_state", "source",
    }
    item = build_founder_guidance_items(funding)[0]
    assert required <= set(item)
    assert item["source"] == "deterministic"


def test_finalize_priority_does_not_mutate_input_items():
    original = [{"dimension": "a", "category": "strength", "_weight": 0.1, "priority": 0}]
    result = finalize_priority(original, strip_internal=True)
    assert "_weight" in original[0]  # input untouched
    assert "_weight" not in result[0]
    assert result[0] is not original[0]


def test_score_item_ranks_confirmed_risk_above_strength():
    assert score_item("confirmed_risk", 0.0) > score_item("strength", 1.0)
