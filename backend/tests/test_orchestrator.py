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
    assert result["idea_expansion"] is not None
    assert result["strategic_opportunity"] is not None
    assert result["customer_segment"] is not None
    assert result["customer_segment"]["method"] == "unavailable"  # no customer_rfm supplied
    node_order = [t["node"] for t in result["trace"]]
    # Student 2 nodes (success_prediction ... business_model) are additively wired between
    # funding_readiness and evidence_confidence_check — see app.agents.orchestrator.build_graph.
    # Phase 5 (Student 3) nodes (customer_segmentation ... pitch_deck) are additively wired
    # between the Student 2 chain and evidence_confidence_check.
    assert node_order == [
        "input_validation",
        "industry_classification",
        "venture_positioning",
        "funding_readiness",
        "success_prediction",
        "revenue_estimate",
        "market_analysis",
        "competitor_analysis",
        "customer_persona",
        "business_model",
        "customer_segmentation",
        "recommendation_ranking",
        "innovation",
        "risk_assessment",
        "growth_strategy",
        "pitch_deck",
        "evidence_confidence_check",
        "judge",
        "mentor_synthesis",
        "idea_expansion",
        "strategic_opportunity",
        "decision_synthesis",
        "causal_reasoning",
        "counterfactual_simulation",
        "persistence",
        "final_response",
    ]


def test_decision_synthesis_present_in_judge_summary_end_to_end():
    result = run_pipeline(
        "PayFlux",
        "A payments platform that lets small businesses settle cross-border payments in seconds.",
        {"problem_clarity": 2, "traction": 1},
    )
    assert result["status"] == "COMPLETED"
    decision_synthesis = result["judge_summary"]["decision_synthesis"]
    assert decision_synthesis["decision_synthesis_version"] == "v1"
    assert decision_synthesis["overall_decision"]
    assert decision_synthesis["decision_confidence_label"] in ("low", "medium", "high")
    # Everything else judge.synthesize already returns must remain untouched by this new key.
    assert "evidence_ledger" in result["judge_summary"]
    assert "contradiction_set" in result["judge_summary"]


def test_causal_reasoning_present_in_judge_summary_end_to_end():
    result = run_pipeline(
        "PayFlux",
        "A payments platform that lets small businesses settle cross-border payments in seconds.",
        {"problem_clarity": 2, "traction": 1},
    )
    assert result["status"] == "COMPLETED"
    causal_reasoning = result["judge_summary"]["causal_reasoning"]
    assert causal_reasoning["causal_reasoning_version"] == "v1"
    assert causal_reasoning["primary_chain"] is not None
    assert "decision_synthesis" in result["judge_summary"]


def test_counterfactual_simulation_present_in_judge_summary_end_to_end():
    result = run_pipeline(
        "PayFlux",
        "A payments platform that lets small businesses settle cross-border payments in seconds.",
        {"problem_clarity": 2, "traction": 1},
    )
    assert result["status"] == "COMPLETED"
    counterfactual_simulation = result["judge_summary"]["counterfactual_simulation"]
    assert counterfactual_simulation["counterfactual_simulation_version"] == "v1"
    assert counterfactual_simulation["baseline"] is not None
    assert counterfactual_simulation["scenarios"]


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
