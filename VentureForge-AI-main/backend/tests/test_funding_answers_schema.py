"""Schema-level migration tests for app.schemas.startup.FundingAnswers (Phase 0 + correction):

Two distinct trust levels apply, depending on payload shape:
- Legacy scalar (0/1/2/None, or any other malformed scalar) -> tolerant, never raises, normalized
  via app.ml.funding_readiness.normalize_evidence_answer (see the legacy-integer tests below).
- Current structured `{state, severity}` object -> validated strictly on DimensionEvidence; an
  unknown `state` or a `severity` that doesn't match its `state` fails validation outright, never
  silently repaired (see the strict-validation tests below).
"""

import pytest
from pydantic import ValidationError

from app.schemas.startup import DimensionEvidence, FundingAnswers


# --- Legacy-tolerant scalar coercion (never raises) --------------------------------------------


def test_accepts_legacy_integers():
    answers = FundingAnswers(problem_clarity=0, traction=1, team_completeness=2)
    assert answers.problem_clarity.state == "confirmed_negative"
    assert answers.traction.state == "confirmed_positive"
    assert answers.traction.severity == 1
    assert answers.team_completeness.severity == 2


def test_accepts_legacy_none():
    answers = FundingAnswers(problem_clarity=None)
    assert answers.problem_clarity.state == "not_sure_yet"


def test_missing_field_defaults_to_not_sure_yet():
    answers = FundingAnswers()
    assert answers.problem_clarity.state == "not_sure_yet"
    assert answers.problem_clarity.severity is None


def test_out_of_range_legacy_integer_falls_back_to_not_sure_yet():
    answers = FundingAnswers(problem_clarity=99)
    assert answers.problem_clarity.state == "not_sure_yet"


def test_legacy_string_scalar_falls_back_to_not_sure_yet():
    answers = FundingAnswers(problem_clarity="not-a-real-legacy-value")
    assert answers.problem_clarity.state == "not_sure_yet"


def test_model_dump_is_json_serializable_dict():
    answers = FundingAnswers(problem_clarity=2)
    dumped = answers.model_dump()
    assert dumped["problem_clarity"] == {"state": "confirmed_positive", "severity": 2}
    assert isinstance(dumped["problem_clarity"]["state"], str)


# --- Current structured payload (validated strictly, never silently repaired) ------------------


def test_accepts_current_state_object():
    answers = FundingAnswers(problem_clarity={"state": "confirmed_positive", "severity": 2})
    assert answers.problem_clarity.state == "confirmed_positive"
    assert answers.problem_clarity.severity == 2


def test_not_applicable_and_not_sure_yet_accepted_directly():
    answers = FundingAnswers(
        traction={"state": "not_applicable"},
        market_size_evidence={"state": "not_sure_yet"},
    )
    assert answers.traction.state == "not_applicable"
    assert answers.market_size_evidence.state == "not_sure_yet"


def test_structured_unknown_state_fails_validation():
    with pytest.raises(ValidationError):
        FundingAnswers(problem_clarity={"state": "definitely_not_a_state"})


def test_structured_out_of_range_severity_fails_validation_not_repaired():
    """The Phase 0.5 correction: a malformed *structured* payload must never be silently
    downgraded to not_sure_yet — it must fail validation, distinguishing it from the legacy-int
    tolerance above."""
    with pytest.raises(ValidationError):
        FundingAnswers(problem_clarity={"state": "confirmed_positive", "severity": 99})


def test_confirmed_positive_missing_severity_fails_validation():
    with pytest.raises(ValidationError):
        FundingAnswers(problem_clarity={"state": "confirmed_positive"})


@pytest.mark.parametrize("state", ["confirmed_negative", "not_sure_yet", "not_applicable"])
def test_non_positive_states_reject_a_severity_value(state):
    with pytest.raises(ValidationError):
        FundingAnswers(problem_clarity={"state": state, "severity": 1})


def test_dimension_evidence_rejects_out_of_range_severity_directly():
    with pytest.raises(ValidationError):
        DimensionEvidence(state="confirmed_positive", severity=5)


def test_dimension_evidence_rejects_severity_on_non_positive_state_directly():
    with pytest.raises(ValidationError):
        DimensionEvidence(state="confirmed_negative", severity=1)
