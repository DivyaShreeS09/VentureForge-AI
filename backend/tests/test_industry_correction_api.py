from tests.conftest import wait_for_terminal_analysis


def _create_and_analyze(client, description="Software that helps small restaurants track inventory and reduce food waste."):
    startup = client.post(
        "/api/v1/startups",
        json={"name": "WasteLess", "description": description, "funding_answers": {"problem_clarity": 2}},
    ).json()
    started = client.post(f"/api/v1/startups/{startup['id']}/analyze").json()
    analysis = wait_for_terminal_analysis(client, started["id"])
    return startup, analysis


def test_correction_updates_venture_positioning_to_the_override(client):
    _, analysis = _create_and_analyze(client)
    response = client.post(
        f"/api/v1/analyses/{analysis['id']}/industry-correction",
        json={"primary_domain": "EdTech"},
    )
    assert response.status_code == 200
    body = response.json()
    vp = body["judge_summary"]["venture_positioning"]
    assert vp["primary_domain"] == "EdTech"
    assert vp["resolution_source"] == "user_override"


def test_correction_never_modifies_model_category(client):
    _, analysis = _create_and_analyze(client)
    original_model_category = analysis["judge_summary"]["model_category"]

    response = client.post(
        f"/api/v1/analyses/{analysis['id']}/industry-correction",
        json={"primary_domain": "EdTech"},
    )
    body = response.json()
    assert body["judge_summary"]["model_category"] == original_model_category
    assert body["industry_prediction"] == analysis["industry_prediction"]


def test_correction_accepts_optional_secondary_domains(client):
    _, analysis = _create_and_analyze(client)
    response = client.post(
        f"/api/v1/analyses/{analysis['id']}/industry-correction",
        json={"primary_domain": "EdTech", "secondary_domains": ["Campus & Student Services"]},
    )
    assert response.status_code == 200
    vp = response.json()["judge_summary"]["venture_positioning"]
    assert vp["secondary_domains"] == ["Campus & Student Services"]


def test_correction_records_auditable_history_with_previous_positioning(client):
    _, analysis = _create_and_analyze(client)
    previous_vp = analysis["judge_summary"]["venture_positioning"]

    response = client.post(
        f"/api/v1/analyses/{analysis['id']}/industry-correction",
        json={"primary_domain": "EdTech"},
    )
    body = response.json()
    history = body["positioning_correction_history"]
    assert len(history) == 1
    assert history[0]["previous_positioning"] == previous_vp
    assert history[0]["override"]["primary_domain"] == "EdTech"
    assert history[0]["taxonomy_version"]
    assert history[0]["corrected_at"]


def test_repeated_correction_appends_to_history_without_losing_prior_entries(client):
    _, analysis = _create_and_analyze(client)

    first = client.post(
        f"/api/v1/analyses/{analysis['id']}/industry-correction", json={"primary_domain": "EdTech"}
    ).json()
    assert len(first["positioning_correction_history"]) == 1

    second = client.post(
        f"/api/v1/analyses/{analysis['id']}/industry-correction",
        json={"primary_domain": "Campus & Student Services"},
    ).json()
    history = second["positioning_correction_history"]
    assert len(history) == 2
    assert history[0]["override"]["primary_domain"] == "EdTech"
    assert history[1]["override"]["primary_domain"] == "Campus & Student Services"
    # The second correction's "previous_positioning" must be the *first* correction's result, not
    # the original pre-correction positioning — proving history accumulates, not overwrites.
    assert history[1]["previous_positioning"]["primary_domain"] == "EdTech"
    assert second["judge_summary"]["venture_positioning"]["primary_domain"] == "Campus & Student Services"


def test_correction_regenerates_mentor_interpretation_immediately(client):
    """A founder-submitted positioning correction must not leave mentor_interpretation lagging the
    just-applied change — see app.services.analysis_service._regenerate_mentor_interpretation."""
    _, analysis = _create_and_analyze(client)
    original_mentor = analysis["mentor_interpretation"]
    assert original_mentor is not None

    response = client.post(
        f"/api/v1/analyses/{analysis['id']}/industry-correction",
        json={"primary_domain": "EdTech"},
    )
    body = response.json()
    updated_mentor = body["mentor_interpretation"]
    assert updated_mentor is not None
    assert updated_mentor != original_mentor
    assert "EdTech" in updated_mentor["venture_positioning"]

    # The persisted row (not just the response) reflects the regenerated mentor result.
    refetched = client.get(f"/api/v1/analyses/{analysis['id']}").json()
    assert refetched["mentor_interpretation"]["venture_positioning"] == updated_mentor["venture_positioning"]


def test_correction_never_reruns_industry_classification_or_success_prediction(client):
    _, analysis = _create_and_analyze(client)
    original_industry_prediction = analysis["industry_prediction"]
    original_success_prediction = analysis["success_prediction"]

    response = client.post(
        f"/api/v1/analyses/{analysis['id']}/industry-correction",
        json={"primary_domain": "EdTech"},
    )
    body = response.json()
    assert body["industry_prediction"] == original_industry_prediction
    assert body["success_prediction"] == original_success_prediction


def test_invalid_analysis_id_returns_404(client):
    response = client.post(
        "/api/v1/analyses/00000000-0000-0000-0000-000000000000/industry-correction",
        json={"primary_domain": "EdTech"},
    )
    assert response.status_code == 404


def test_invalid_domain_returns_422(client):
    _, analysis = _create_and_analyze(client)
    response = client.post(
        f"/api/v1/analyses/{analysis['id']}/industry-correction",
        json={"primary_domain": "Not A Real Taxonomy Domain"},
    )
    assert response.status_code == 422


def test_invalid_secondary_domain_returns_422(client):
    _, analysis = _create_and_analyze(client)
    response = client.post(
        f"/api/v1/analyses/{analysis['id']}/industry-correction",
        json={"primary_domain": "EdTech", "secondary_domains": ["Not A Real Domain"]},
    )
    assert response.status_code == 422


def test_missing_primary_domain_returns_422(client):
    _, analysis = _create_and_analyze(client)
    response = client.post(f"/api/v1/analyses/{analysis['id']}/industry-correction", json={})
    assert response.status_code == 422
