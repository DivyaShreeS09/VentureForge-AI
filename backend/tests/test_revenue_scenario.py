from app.ml.revenue_scenario import estimate_revenue_scenario


def test_unavailable_when_required_assumptions_missing():
    result = estimate_revenue_scenario(
        price_per_customer_usd=None,
        initial_customers=None,
        monthly_growth_rate_pct=None,
        gross_margin_pct=None,
    )
    assert result["available"] is False
    assert result["scenarios"] is None
    assert "price_per_customer_usd" in result["missing_assumptions"]
    assert "initial_customers" in result["missing_assumptions"]


def test_returns_three_scenarios_when_available():
    result = estimate_revenue_scenario(
        price_per_customer_usd=50,
        initial_customers=100,
        monthly_growth_rate_pct=10,
        gross_margin_pct=70,
    )
    assert result["available"] is True
    assert set(result["scenarios"].keys()) == {"conservative", "base", "optimistic"}


def test_optimistic_scenario_never_less_than_conservative():
    result = estimate_revenue_scenario(
        price_per_customer_usd=50,
        initial_customers=100,
        monthly_growth_rate_pct=10,
        gross_margin_pct=70,
    )
    conservative = result["scenarios"]["conservative"]["annual_revenue_usd"]
    optimistic = result["scenarios"]["optimistic"]["annual_revenue_usd"]
    assert optimistic >= conservative


def test_zero_growth_rate_is_flat_revenue():
    result = estimate_revenue_scenario(
        price_per_customer_usd=10,
        initial_customers=50,
        monthly_growth_rate_pct=0,
        gross_margin_pct=100,
    )
    base = result["scenarios"]["base"]
    assert base["annual_revenue_usd"] == 10 * 50 * 12


def test_missing_growth_and_margin_are_defaulted_and_listed():
    result = estimate_revenue_scenario(
        price_per_customer_usd=20,
        initial_customers=10,
        monthly_growth_rate_pct=None,
        gross_margin_pct=None,
    )
    assert result["available"] is True
    assert "monthly_growth_rate_pct" in result["missing_assumptions"]
    assert "gross_margin_pct" in result["missing_assumptions"]


def test_result_is_json_serializable():
    import json

    result = estimate_revenue_scenario(50, 100, 10, 70)
    json.dumps(result)
