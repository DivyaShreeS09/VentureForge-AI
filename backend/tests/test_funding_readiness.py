from app.ml.funding_readiness import DIMENSIONS, EvidenceState, assess_funding_readiness


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


# --- Four explicit evidence states (Phase 0) --------------------------------------------------


def test_confirmed_positive_scores_by_severity():
    answers = {"problem_clarity": {"state": "confirmed_positive", "severity": 2}}
    result = assess_funding_readiness(answers)
    item = next(b for b in result["breakdown"] if b["dimension"] == "problem_clarity")
    assert item["state"] == "confirmed_positive"
    assert item["raw_score"] == 2
    assert "problem_clarity" not in result["missing_evidence"]


def test_confirmed_negative_scores_zero_but_is_not_missing_evidence():
    answers = {"problem_clarity": {"state": "confirmed_negative"}}
    result = assess_funding_readiness(answers)
    item = next(b for b in result["breakdown"] if b["dimension"] == "problem_clarity")
    assert item["state"] == "confirmed_negative"
    assert item["raw_score"] == 0
    assert "problem_clarity" not in result["missing_evidence"]


def test_not_sure_yet_scores_zero_and_is_missing_evidence():
    answers = {"problem_clarity": {"state": "not_sure_yet"}}
    result = assess_funding_readiness(answers)
    item = next(b for b in result["breakdown"] if b["dimension"] == "problem_clarity")
    assert item["state"] == "not_sure_yet"
    assert item["raw_score"] == 0
    assert "problem_clarity" in result["missing_evidence"]


def test_not_applicable_excluded_from_scoring_and_missing_evidence():
    answers = {"problem_clarity": {"state": "not_applicable"}}
    result = assess_funding_readiness(answers)
    item = next(b for b in result["breakdown"] if b["dimension"] == "problem_clarity")
    assert item["state"] == "not_applicable"
    assert item["raw_score"] is None
    assert item["weight"] == 0.0
    assert "problem_clarity" not in result["missing_evidence"]


def test_not_applicable_never_lowers_max_attainable_score():
    """Marking a dimension not_applicable and maxing every remaining dimension must still reach
    100 — its weight is redistributed across the applicable dimensions, never left unclaimed."""
    answers = {name: {"state": "confirmed_positive", "severity": 2} for name in DIMENSIONS}
    answers["team_completeness"] = {"state": "not_applicable"}
    result = assess_funding_readiness(answers)
    assert result["overall_score"] == 100.0
    assert result["level"] == "ready"


def test_all_not_applicable_does_not_crash():
    answers = {name: {"state": "not_applicable"} for name in DIMENSIONS}
    result = assess_funding_readiness(answers)
    assert result["overall_score"] == 0.0
    assert result["missing_evidence"] == []


def test_legacy_int_and_none_values_still_normalize_correctly():
    """Backward compatibility: startups created before the four-state model existed stored plain
    0/1/2/null values — these must still score identically to their four-state equivalents."""
    legacy = assess_funding_readiness({"problem_clarity": 0, "traction": 2, "market_size_evidence": None})
    explicit = assess_funding_readiness(
        {
            "problem_clarity": {"state": "confirmed_negative"},
            "traction": {"state": "confirmed_positive", "severity": 2},
            "market_size_evidence": {"state": "not_sure_yet"},
        }
    )
    assert legacy["overall_score"] == explicit["overall_score"]
    assert legacy["missing_evidence"] == explicit["missing_evidence"]


def test_malformed_evidence_value_is_handled_safely_as_not_sure_yet():
    answers = {
        "problem_clarity": {"state": "not_a_real_state"},
        "traction": "unexpected-string",
        "team_completeness": {"state": "confirmed_positive", "severity": 99},
    }
    result = assess_funding_readiness(answers)
    problem = next(b for b in result["breakdown"] if b["dimension"] == "problem_clarity")
    traction = next(b for b in result["breakdown"] if b["dimension"] == "traction")
    team = next(b for b in result["breakdown"] if b["dimension"] == "team_completeness")
    assert problem["state"] == EvidenceState.NOT_SURE_YET.value
    assert traction["state"] == EvidenceState.NOT_SURE_YET.value
    # An out-of-range severity on an otherwise-valid confirmed_positive state falls back to 1
    # rather than crashing or silently accepting an invalid score.
    assert team["raw_score"] == 1
