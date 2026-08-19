from app.agents.hypothesis_engine import build_hypotheses_for_gaps
from app.ml.funding_readiness import DIMENSIONS


def test_every_dimension_produces_a_structured_hypothesis():
    hypotheses = build_hypotheses_for_gaps(list(DIMENSIONS.keys()))
    assert len(hypotheses) == len(DIMENSIONS)
    for h in hypotheses:
        assert h["source_dimension"] in DIMENSIONS
        assert h["suggestion_label"] == "possibility"
        assert isinstance(h["starting_hypothesis"], str) and h["starting_hypothesis"]
        assert isinstance(h["assumptions"], list)
        assert isinstance(h["alternatives"], list)
        assert isinstance(h["validation_task"], str) and h["validation_task"]


def test_empty_gap_list_produces_no_hypotheses():
    assert build_hypotheses_for_gaps([]) == []


def test_unrecognized_dimension_gets_an_honest_placeholder_not_a_crash():
    hypotheses = build_hypotheses_for_gaps(["not_a_real_dimension"])
    assert len(hypotheses) == 1
    assert hypotheses[0]["source_dimension"] == "not_a_real_dimension"
    assert "not enough is known" in hypotheses[0]["starting_hypothesis"].lower()


def test_preserves_requested_order():
    dims = ["traction", "problem_clarity", "team_completeness"]
    hypotheses = build_hypotheses_for_gaps(dims)
    assert [h["source_dimension"] for h in hypotheses] == dims
