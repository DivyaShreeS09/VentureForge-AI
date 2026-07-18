from app.agents.orchestrator import run_pipeline


def test_valid_input_completes_successfully():
    result = run_pipeline(
        "PayFlux",
        "A payments platform that lets small businesses settle cross-border payments in seconds.",
        {"problem_clarity": 2, "traction": 1},
    )
    assert result["status"] == "COMPLETED"
    assert result["error"] is None
    assert result["industry_prediction"] is not None
    assert result["funding_assessment"] is not None
    assert result["judge_summary"] is not None
    node_order = [t["node"] for t in result["trace"]]
    # Student 2 nodes (success_prediction ... business_model) are additively wired between
    # funding_readiness and evidence_confidence_check — see app.agents.orchestrator.build_graph.
    assert node_order == [
        "input_validation",
        "industry_classification",
        "funding_readiness",
        "success_prediction",
        "revenue_estimate",
        "market_analysis",
        "competitor_analysis",
        "customer_persona",
        "business_model",
        "evidence_confidence_check",
        "judge",
        "persistence",
        "final_response",
    ]


def test_invalid_input_short_circuits_before_ml_nodes():
    result = run_pipeline("", "too short", {})
    assert result["status"] == "FAILED"
    assert result["error"]
    node_order = [t["node"] for t in result["trace"]]
    assert node_order == ["input_validation", "invalid_input", "persistence", "final_response"]
    assert "industry_prediction" not in result


def test_persist_fn_is_called_with_final_state():
    captured = {}

    def persist(state):
        captured["status"] = state["status"]

    run_pipeline("Nova", "A subscription analytics dashboard for retail teams.", {}, persist_fn=persist)
    assert captured["status"] == "COMPLETED"


def test_missing_funding_answers_defaults_gracefully():
    result = run_pipeline("Nova", "A subscription analytics dashboard for retail teams.", {})
    assert result["funding_assessment"]["overall_score"] == 0.0
    assert result["status"] == "COMPLETED"
