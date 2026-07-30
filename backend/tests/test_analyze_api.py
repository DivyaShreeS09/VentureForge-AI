from tests.conftest import wait_for_terminal_analysis


def _create_startup(client, **overrides):
    payload = {
        "name": "PayFlux",
        "description": "A payments platform that lets small businesses settle cross-border payments in seconds.",
        "funding_answers": {"problem_clarity": 2, "traction": 1},
    }
    payload.update(overrides)
    return client.post("/api/v1/startups", json=payload).json()


def test_analyze_starts_immediately_and_then_completes(client):
    startup = _create_startup(client)
    response = client.post(f"/api/v1/startups/{startup['id']}/analyze")
    assert response.status_code == 201
    started = response.json()
    # Act IV (The Forging): the endpoint returns immediately, before the real background run has
    # necessarily produced anything yet — it must never claim a result it doesn't have.
    assert started["status"] in ("RUNNING", "COMPLETED")
    assert started["startup_id"] == startup["id"]

    body = wait_for_terminal_analysis(client, started["id"])
    assert body["status"] == "COMPLETED"
    assert body["startup_id"] == startup["id"]
    assert body["industry_prediction"]["predicted_industry"]
    assert body["funding_assessment"]["overall_score"] >= 0
    assert body["judge_summary"]["overall_assessment"]
    assert body["student3_outputs"]["customer_segment"]["method"] == "unavailable"
    # Persisted trace covers every node through "persistence" itself (Act IV persists the
    # cumulative state as soon as each node's own real update arrives, including persistence's
    # own step this time; the trailing "final_response" node is intentionally never even run —
    # see _execute_analysis_stream — since it changes nothing a founder needs to see). 22 steps:
    # input_validation, industry_classification, venture_positioning, funding_readiness, the 6
    # additive Student 2 nodes, the 6 additive Phase 5 (Student 3) nodes, evidence_confidence_check,
    # judge, mentor_synthesis, idea_expansion, strategic_opportunity, decision_synthesis,
    # causal_reasoning, counterfactual_simulation, persistence.
    assert isinstance(body["workflow_trace"], list) and len(body["workflow_trace"]) == 25
    # Once terminal, current_node/current_stage still reflect the real last node reached (never
    # cleared to null) — a late page load must still show where the run finished.
    assert body["current_node"] == "persistence"


def test_analyze_unknown_startup_returns_404(client):
    response = client.post("/api/v1/startups/00000000-0000-0000-0000-000000000000/analyze")
    assert response.status_code == 404


def test_analysis_is_retrievable_after_creation(client):
    startup = _create_startup(client)
    started = client.post(f"/api/v1/startups/{startup['id']}/analyze").json()
    analysis = wait_for_terminal_analysis(client, started["id"])

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


def test_models_status_surfaces_real_evaluation_metrics(client):
    """Product Intelligence Sprint (Phase 9): real, already-computed held-out test-set metrics
    (see ml/models/*/metadata.json) must be surfaced through this endpoint, not left buried on
    disk where nothing in the product ever reads them."""
    response = client.get("/api/v1/models/status")
    body = response.json()
    if body["industry_classifier_loaded"]:
        metrics = body["industry_classifier_test_metrics"]
        assert metrics is not None
        assert 0.0 <= metrics["accuracy"] <= 1.0
        assert "macro_f1" in metrics
    if body["success_predictor_loaded"]:
        metrics = body["success_predictor_test_metrics"]
        assert metrics is not None
        assert "roc_auc" in metrics
        assert "confusion_matrix" in metrics
        assert body["success_predictor_disclaimer"]
