from app.ml.funding_readiness import DIMENSIONS, assess_funding_readiness


def test_all_missing_scores_zero():
    result = assess_funding_readiness({})
    assert result["overall_score"] == 0.0
    assert result["level"] == "early_stage"
    assert set(result["missing_evidence"]) == set(DIMENSIONS.keys())


def test_all_strong_scores_one_hundred():
    answers = {name: 2 for name in DIMENSIONS}
    result = assess_funding_readiness(answers)
    assert result["overall_score"] == 100.0
    assert result["level"] == "ready"
    assert result["missing_evidence"] == []


def test_missing_dimension_gets_no_favourable_assumption():
    answers = {name: 2 for name in DIMENSIONS}
    del answers["team_completeness"]
    result = assess_funding_readiness(answers)
    assert result["overall_score"] < 100.0
    assert "team_completeness" in result["missing_evidence"]
    contribution = next(b for b in result["breakdown"] if b["dimension"] == "team_completeness")
    assert contribution["raw_score"] == 0


def test_invalid_value_treated_as_missing():
    answers = {"problem_clarity": 5}  # out of range
    result = assess_funding_readiness(answers)
    assert "problem_clarity" in result["missing_evidence"]


def test_deterministic_across_calls():
    answers = {"problem_clarity": 1, "traction": 2}
    first = assess_funding_readiness(answers)
    second = assess_funding_readiness(answers)
    assert first == second


def test_level_boundaries():
    from app.ml.funding_readiness import _level_for_score

    assert _level_for_score(0) == "early_stage"
    assert _level_for_score(39.99) == "early_stage"
    assert _level_for_score(40) == "developing"
    assert _level_for_score(69.99) == "developing"
    assert _level_for_score(70) == "ready"
    assert _level_for_score(100) == "ready"
