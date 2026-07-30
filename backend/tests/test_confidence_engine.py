from app.agents import confidence_engine, evidence_ledger
from app.agents.confidence_engine import (
    combine_confidence,
    label_confidence,
    propagate_confidence,
)


# --- One engine: evidence_ledger delegates, never redefines ------------------------------------


def test_evidence_ledger_reexports_the_same_function_object_not_a_copy():
    assert evidence_ledger.combine_confidence is confidence_engine.combine_confidence


def test_evidence_ledger_reexports_the_same_constants():
    assert evidence_ledger.SOURCE_TYPE_BASE_CONFIDENCE is confidence_engine.SOURCE_TYPE_BASE_CONFIDENCE
    assert evidence_ledger.MODEL_INFERENCE_DISCOUNT == confidence_engine.MODEL_INFERENCE_DISCOUNT


# --- combine_confidence (moved, behavior preserved) ---------------------------------------------


def test_combine_confidence_empty_is_zero():
    assert combine_confidence([]) == 0.0


def test_combine_confidence_single_item_equals_its_base_confidence():
    items = [{"source_type": "user_confirmed", "base_confidence": 0.9}]
    assert combine_confidence(items) == 0.9


def test_combine_confidence_independent_sources_exceed_either_alone():
    items = [
        {"source_type": "user_confirmed", "base_confidence": 0.9},
        {"source_type": "model_inference", "base_confidence": 0.4},
    ]
    combined = combine_confidence(items)
    assert combined > 0.9
    assert combined == round(1 - (1 - 0.9) * (1 - 0.4), 4)


def test_combine_confidence_same_source_type_dedupes_via_max():
    items = [
        {"source_type": "user_confirmed", "base_confidence": 0.9},
        {"source_type": "user_confirmed", "base_confidence": 0.9},
    ]
    assert combine_confidence(items) == 0.9


# --- label_confidence: the one shared status-labeling function ----------------------------------


def test_label_confidence_thresholds():
    assert label_confidence(0.0) == "low"
    assert label_confidence(0.29) == "low"
    assert label_confidence(0.3) == "medium"
    assert label_confidence(0.59) == "medium"
    assert label_confidence(0.6) == "high"
    assert label_confidence(1.0) == "high"


def test_label_confidence_is_monotonic():
    values = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    order = {"low": 0, "medium": 1, "high": 2}
    labels = [order[label_confidence(v)] for v in values]
    assert labels == sorted(labels)


# --- propagate_confidence: the new downstream-propagation primitive -----------------------------


def test_propagate_confidence_no_arguments_is_zero():
    assert propagate_confidence() == 0.0


def test_propagate_confidence_single_argument_is_unchanged():
    assert propagate_confidence(0.73) == 0.73


def test_propagate_confidence_never_exceeds_the_weakest_input():
    result = propagate_confidence(0.9, 0.3)
    assert result <= 0.3 + 0.05  # weakest input plus, at most, the disclosed agreement bonus
    assert result >= 0.3


def test_propagate_confidence_agreement_bonus_only_when_inputs_are_close():
    close = propagate_confidence(0.7, 0.72)
    assert close > 0.7  # small bonus for near-agreement
    far = propagate_confidence(0.9, 0.2)
    assert far == 0.2  # no bonus — inputs are not reinforcing, just coexisting


def test_propagate_confidence_never_exceeds_one():
    assert propagate_confidence(0.99, 0.98, 1.0) <= 1.0


def test_propagate_confidence_is_deterministic_and_order_independent():
    a = propagate_confidence(0.4, 0.6, 0.5)
    b = propagate_confidence(0.6, 0.5, 0.4)
    assert a == b


def test_propagate_confidence_monotonic_in_each_input():
    lower = propagate_confidence(0.5, 0.5)
    higher = propagate_confidence(0.5, 0.6)
    assert higher >= lower


# --- Idempotence / determinism across the whole module ------------------------------------------


def test_combine_confidence_is_idempotent_on_repeated_calls():
    items = [
        {"source_type": "user_confirmed", "base_confidence": 0.9},
        {"source_type": "user_not_sure", "base_confidence": 0.3},
    ]
    first = combine_confidence(items)
    second = combine_confidence(items)
    assert first == second
    # And the input list itself must not be mutated by the call.
    assert items == [
        {"source_type": "user_confirmed", "base_confidence": 0.9},
        {"source_type": "user_not_sure", "base_confidence": 0.3},
    ]
