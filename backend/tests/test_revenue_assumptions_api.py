"""Tests for PATCH /api/v1/analyses/{id}/revenue-assumptions (production-hardening phase)."""

import json

from tests.conftest import wait_for_terminal_analysis


def _create_and_analyze(client, description="Software that helps small restaurants track inventory and reduce food waste."):
    startup = client.post(
        "/api/v1/startups",
        json={"name": "WasteLess", "description": description, "funding_answers": {"problem_clarity": 2}},
    ).json()
    started = client.post(f"/api/v1/startups/{startup['id']}/analyze").json()
    analysis = wait_for_terminal_analysis(client, started["id"])
    return startup, analysis


def test_partial_edit_updates_only_the_given_field_and_marks_it_user_supplied(client):
    _, analysis = _create_and_analyze(client)
    response = client.patch(
        f"/api/v1/analyses/{analysis['id']}/revenue-assumptions",
        json={"price_per_customer_usd": 250.0},
    )
    assert response.status_code == 200
    body = response.json()
    fields = body["revenue_estimate"]["assumptions"]
    assert fields["price_per_customer_usd"]["value"] == 250.0
    assert fields["price_per_customer_usd"]["assumption_source"] == "user_supplied"
    # Untouched fields remain whatever they were (suggested default, since none were supplied yet).
    assert fields["initial_customers"]["assumption_source"] == "suggested_default"


def test_complete_edit_marks_all_four_fields_user_supplied(client):
    _, analysis = _create_and_analyze(client)
    response = client.patch(
        f"/api/v1/analyses/{analysis['id']}/revenue-assumptions",
        json={
            "price_per_customer_usd": 99.0,
            "initial_customers": 10,
            "monthly_growth_rate_pct": 5.0,
            "gross_margin_pct": 70.0,
        },
    )
    assert response.status_code == 200
    fields = response.json()["revenue_estimate"]["assumptions"]
    for field in fields.values():
        assert field["assumption_source"] == "user_supplied"


def test_scenarios_are_recomputed_server_side(client):
    _, analysis = _create_and_analyze(client)
    response = client.patch(
        f"/api/v1/analyses/{analysis['id']}/revenue-assumptions",
        json={
            "price_per_customer_usd": 100.0,
            "initial_customers": 10,
            "monthly_growth_rate_pct": 10.0,
            "gross_margin_pct": 50.0,
        },
    )
    scenarios = response.json()["revenue_estimate"]["scenarios"]
    assert scenarios["conservative"]["annual_revenue_usd"] <= scenarios["base"]["annual_revenue_usd"]
    assert scenarios["base"]["annual_revenue_usd"] <= scenarios["optimistic"]["annual_revenue_usd"]


def test_malformed_and_infinite_values_rejected(client):
    # httpx's own `json=` kwarg refuses to serialize NaN/Infinity client-side (it isn't valid
    # JSON), so this sends raw content built with the stdlib `json` module, which does emit the
    # non-standard NaN/Infinity/-Infinity literals many JSON parsers (including Python's own,
    # server-side) still accept — exactly the malformed-but-parseable payload this test needs to
    # prove the *server's* Pydantic validation (allow_inf_nan=False) rejects.
    _, analysis = _create_and_analyze(client)
    for bad_value in (float("nan"), float("inf"), float("-inf")):
        raw = json.dumps({"price_per_customer_usd": bad_value})
        response = client.patch(
            f"/api/v1/analyses/{analysis['id']}/revenue-assumptions",
            content=raw,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422, bad_value


def test_negative_price_customers_and_margin_rejected(client):
    _, analysis = _create_and_analyze(client)
    for field, value in (
        ("price_per_customer_usd", -1.0),
        ("initial_customers", -1),
        ("gross_margin_pct", -1.0),
    ):
        response = client.patch(
            f"/api/v1/analyses/{analysis['id']}/revenue-assumptions", json={field: value}
        )
        assert response.status_code == 422, field


def test_negative_growth_rate_permitted_within_documented_bound(client):
    _, analysis = _create_and_analyze(client)
    response = client.patch(
        f"/api/v1/analyses/{analysis['id']}/revenue-assumptions",
        json={"monthly_growth_rate_pct": -20.0},
    )
    assert response.status_code == 200
    assert response.json()["revenue_estimate"]["assumptions"]["monthly_growth_rate_pct"]["value"] == -20.0


def test_growth_rate_beyond_documented_bound_rejected(client):
    _, analysis = _create_and_analyze(client)
    response = client.patch(
        f"/api/v1/analyses/{analysis['id']}/revenue-assumptions",
        json={"monthly_growth_rate_pct": -150.0},
    )
    assert response.status_code == 422


def test_edit_changes_assumption_source_to_user_supplied_and_appends_history(client):
    _, analysis = _create_and_analyze(client)
    response = client.patch(
        f"/api/v1/analyses/{analysis['id']}/revenue-assumptions",
        json={"price_per_customer_usd": 42.0},
    )
    body = response.json()
    history = body["revenue_assumptions_history"]
    assert len(history) == 1
    assert history[0]["changed_fields"] == ["price_per_customer_usd"]
    assert history[0]["updated_assumptions"]["price_per_customer_usd"] == 42.0
    assert history[0]["updated_at"]


def test_repeated_edits_append_without_losing_prior_history(client):
    _, analysis = _create_and_analyze(client)
    client.patch(f"/api/v1/analyses/{analysis['id']}/revenue-assumptions", json={"price_per_customer_usd": 42.0})
    second = client.patch(
        f"/api/v1/analyses/{analysis['id']}/revenue-assumptions", json={"initial_customers": 20}
    ).json()
    history = second["revenue_assumptions_history"]
    assert len(history) == 2
    assert history[0]["changed_fields"] == ["price_per_customer_usd"]
    assert history[1]["changed_fields"] == ["initial_customers"]
    # The second edit's `previous_assumptions` must include the first edit's value, proving edits
    # compound rather than each starting from a blank slate.
    assert history[1]["previous_assumptions"]["price_per_customer_usd"] == 42.0


def test_persisted_edit_survives_a_fresh_fetch(client):
    _, analysis = _create_and_analyze(client)
    client.patch(f"/api/v1/analyses/{analysis['id']}/revenue-assumptions", json={"price_per_customer_usd": 77.0})

    refetched = client.get(f"/api/v1/analyses/{analysis['id']}").json()
    assert refetched["revenue_estimate"]["assumptions"]["price_per_customer_usd"]["value"] == 77.0
    assert refetched["revenue_estimate"]["assumptions"]["price_per_customer_usd"]["assumption_source"] == "user_supplied"


def test_edit_never_touches_model_category_or_venture_positioning(client):
    _, analysis = _create_and_analyze(client)
    original_model_category = analysis["judge_summary"]["model_category"]
    original_positioning = analysis["judge_summary"]["venture_positioning"]

    response = client.patch(
        f"/api/v1/analyses/{analysis['id']}/revenue-assumptions", json={"price_per_customer_usd": 15.0}
    )
    body = response.json()
    assert body["judge_summary"]["model_category"] == original_model_category
    assert body["judge_summary"]["venture_positioning"] == original_positioning


def test_edit_regenerates_mentor_interpretation_immediately(client):
    """A saved revenue-assumption edit must not leave mentor_interpretation lagging the just-saved
    change — see app.services.analysis_service._regenerate_mentor_interpretation."""
    _, analysis = _create_and_analyze(client)
    original_mentor = analysis["mentor_interpretation"]
    assert original_mentor is not None

    response = client.patch(
        f"/api/v1/analyses/{analysis['id']}/revenue-assumptions",
        json={"price_per_customer_usd": 250.0, "initial_customers": 20},
    )
    body = response.json()
    updated_mentor = body["mentor_interpretation"]
    assert updated_mentor is not None
    assert updated_mentor != original_mentor
    assert updated_mentor["revenue_scenarios"] != original_mentor["revenue_scenarios"]
    assert "mix of founder-supplied" in updated_mentor["evidence_and_uncertainty"]["user_supplied_vs_suggested_summary"]

    refetched = client.get(f"/api/v1/analyses/{analysis['id']}").json()
    assert refetched["mentor_interpretation"]["revenue_scenarios"] == updated_mentor["revenue_scenarios"]


def test_edit_never_reruns_industry_classification_or_success_prediction(client):
    _, analysis = _create_and_analyze(client)
    original_industry_prediction = analysis["industry_prediction"]
    original_success_prediction = analysis["success_prediction"]

    response = client.patch(
        f"/api/v1/analyses/{analysis['id']}/revenue-assumptions", json={"price_per_customer_usd": 15.0}
    )
    body = response.json()
    assert body["industry_prediction"] == original_industry_prediction
    assert body["success_prediction"] == original_success_prediction


def test_invalid_analysis_id_returns_404(client):
    response = client.patch(
        "/api/v1/analyses/00000000-0000-0000-0000-000000000000/revenue-assumptions",
        json={"price_per_customer_usd": 10.0},
    )
    assert response.status_code == 404


def test_empty_body_is_a_valid_no_op(client):
    _, analysis = _create_and_analyze(client)
    response = client.patch(f"/api/v1/analyses/{analysis['id']}/revenue-assumptions", json={})
    assert response.status_code == 200
    assert response.json()["revenue_assumptions_history"][0]["changed_fields"] == []
