def _create_startup(client, **overrides):
    payload = {
        "name": "PayFlux",
        "description": "A payments platform that lets small businesses settle cross-border payments in seconds.",
        "funding_answers": {"problem_clarity": 2, "traction": 1},
    }
    payload.update(overrides)
    return client.post("/api/v1/startups", json=payload).json()


def test_analyze_success_returns_full_result(client):
    startup = _create_startup(client)
    response = client.post(f"/api/v1/startups/{startup['id']}/analyze")
    assert response.status_code == 201
    body = response.json()

    assert body["status"] == "COMPLETED"
    assert body["startup_id"] == startup["id"]
    assert body["industry_prediction"]["predicted_industry"]
    assert body["funding_assessment"]["overall_score"] >= 0
    assert body["judge_summary"]["overall_assessment"]
    # Persisted trace covers every node up through "judge" — persistence saves the state as of
    # its own invocation, so its own step and the trailing final_response step aren't included.
    # 11 nodes: input_validation, industry_classification, funding_readiness, the 6 additive
    # Student 2 nodes, evidence_confidence_check, judge.
    assert isinstance(body["workflow_trace"], list) and len(body["workflow_trace"]) == 11


def test_analyze_unknown_startup_returns_404(client):
    response = client.post("/api/v1/startups/00000000-0000-0000-0000-000000000000/analyze")
    assert response.status_code == 404


def test_analysis_is_retrievable_after_creation(client):
    startup = _create_startup(client)
    analysis = client.post(f"/api/v1/startups/{startup['id']}/analyze").json()

    response = client.get(f"/api/v1/analyses/{analysis['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == analysis["id"]
    assert response.json()["industry_prediction"] == analysis["industry_prediction"]


def test_analysis_not_found_returns_404(client):
    response = client.get("/api/v1/analyses/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


def test_models_status_reflects_real_artifact(client):
    response = client.get("/api/v1/models/status")
    assert response.status_code == 200
    body = response.json()
    assert "industry_classifier_loaded" in body
    assert body["funding_rubric_version"] == "v1"
