from app.ml.revenue_scenario import estimate_revenue_scenario


def test_zero_supplied_assumptions_still_returns_available_scenarios():
    """Phase A correction: available=False no longer exists — a scenario is always produced,
    every field falling back to a labeled suggested default."""
    result = estimate_revenue_scenario(
        price_per_customer_usd=None,
        initial_customers=None,
        monthly_growth_rate_pct=None,
        gross_margin_pct=None,
    )
    assert result["available"] is True
    assert result["scenarios"] is not None
    assert set(result["missing_assumptions"]) == {
        "price_per_customer_usd", "initial_customers", "monthly_growth_rate_pct", "gross_margin_pct",
    }
    for field in result["missing_assumptions"]:
        assert result["assumptions"][field]["assumption_source"] == "suggested_default"
        assert result["assumptions"][field]["editable"] is True


def test_fully_user_supplied_assumptions_are_labeled_as_such():
    result = estimate_revenue_scenario(
        price_per_customer_usd=50, initial_customers=100, monthly_growth_rate_pct=10, gross_margin_pct=70
    )
    assert result["available"] is True
    assert result["missing_assumptions"] == []
    for field in ("price_per_customer_usd", "initial_customers", "monthly_growth_rate_pct", "gross_margin_pct"):
        assert result["assumptions"][field]["assumption_source"] == "user_supplied"
    assert set(result["scenarios"].keys()) == {"conservative", "base", "optimistic"}


def test_partially_supplied_assumptions_mix_provenance_per_field():
    result = estimate_revenue_scenario(
        price_per_customer_usd=20, initial_customers=10, monthly_growth_rate_pct=None, gross_margin_pct=None
    )
    assert result["assumptions"]["price_per_customer_usd"]["assumption_source"] == "user_supplied"
    assert result["assumptions"]["initial_customers"]["assumption_source"] == "user_supplied"
    assert result["assumptions"]["monthly_growth_rate_pct"]["assumption_source"] == "suggested_default"
    assert result["assumptions"]["gross_margin_pct"]["assumption_source"] == "suggested_default"
    assert set(result["missing_assumptions"]) == {"monthly_growth_rate_pct", "gross_margin_pct"}


def test_domain_default_used_when_primary_domain_recognized():
    result = estimate_revenue_scenario(
        None, None, None, None, primary_domain="Restaurant Operations Technology"
    )
    assert result["default_basis"] == "domain_default"
    assert result["assumptions"]["price_per_customer_usd"]["value"] == 99.0


def test_model_category_fallback_used_when_domain_unrecognized():
    result = estimate_revenue_scenario(None, None, None, None, primary_domain=None, model_category_label="b2b")
    assert result["default_basis"] == "model_category_default"


def test_unknown_domain_and_category_falls_back_to_generic_discovery_stage():
    result = estimate_revenue_scenario(
        None, None, None, None, primary_domain="Not A Real Domain", model_category_label="not_a_real_category"
    )
    assert result["default_basis"] == "generic_discovery_stage_default"
    assert "discovery-stage" in result["assumptions"]["price_per_customer_usd"]["explanation"]


def test_scenario_ordering_conservative_lte_base_lte_optimistic():
    result = estimate_revenue_scenario(
        price_per_customer_usd=50, initial_customers=100, monthly_growth_rate_pct=10, gross_margin_pct=70
    )
    conservative = result["scenarios"]["conservative"]["annual_revenue_usd"]
    base = result["scenarios"]["base"]["annual_revenue_usd"]
    optimistic = result["scenarios"]["optimistic"]["annual_revenue_usd"]
    assert conservative <= base <= optimistic


def test_scenario_ordering_holds_for_negative_growth_rate_too():
    """A multiplier-based scenario spread inverts ordering for negative growth — the additive
    delta must preserve conservative <= base <= optimistic regardless of sign."""
    result = estimate_revenue_scenario(
        price_per_customer_usd=50, initial_customers=100, monthly_growth_rate_pct=-10, gross_margin_pct=70
    )
    conservative = result["scenarios"]["conservative"]["annual_revenue_usd"]
    base = result["scenarios"]["base"]["annual_revenue_usd"]
    optimistic = result["scenarios"]["optimistic"]["annual_revenue_usd"]
    assert conservative <= base <= optimistic


def test_zero_growth_rate_is_flat_revenue():
    result = estimate_revenue_scenario(
        price_per_customer_usd=10, initial_customers=50, monthly_growth_rate_pct=0, gross_margin_pct=100
    )
    base = result["scenarios"]["base"]
    assert base["annual_revenue_usd"] == 10 * 50 * 12


def test_negative_user_supplied_value_is_treated_as_not_supplied():
    """A negative price/customer count should never be computed as a fact — it falls back to the
    suggested default rather than producing a nonsensical negative scenario."""
    result = estimate_revenue_scenario(
        price_per_customer_usd=-50, initial_customers=-10, monthly_growth_rate_pct=10, gross_margin_pct=70
    )
    assert result["assumptions"]["price_per_customer_usd"]["assumption_source"] == "suggested_default"
    assert result["assumptions"]["initial_customers"]["assumption_source"] == "suggested_default"
    assert result["scenarios"]["base"]["annual_revenue_usd"] >= 0


def test_assumptions_used_backward_compat_alias_present():
    result = estimate_revenue_scenario(50, 100, 10, 70)
    assert result["assumptions_used"] == {
        "price_per_customer_usd": 50, "initial_customers": 100, "monthly_growth_rate_pct": 10, "gross_margin_pct": 70,
    }


def test_result_is_json_serializable():
    import json

    result = estimate_revenue_scenario(50, 100, 10, 70)
    json.dumps(result)

    result_all_defaults = estimate_revenue_scenario(None, None, None, None)
    json.dumps(result_all_defaults)
