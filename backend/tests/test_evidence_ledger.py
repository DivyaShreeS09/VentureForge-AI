from app.agents.evidence_ledger import (
    MODEL_INFERENCE_DISCOUNT,
    SOURCE_TYPE_BASE_CONFIDENCE,
    build_evidence_ledger,
    combine_confidence,
    confidence_for_dimension,
    summarize_ledger,
)
from app.ml.funding_readiness import assess_funding_readiness


def test_confirmed_dimensions_become_user_confirmed_items():
    funding = assess_funding_readiness({"problem_clarity": 2, "traction": 1})
    ledger = build_evidence_ledger(funding)
    by_dim = {item["dimension"]: item for item in ledger}
    assert by_dim["problem_clarity"]["source_type"] == "user_confirmed"
    assert by_dim["problem_clarity"]["base_confidence"] == SOURCE_TYPE_BASE_CONFIDENCE["user_confirmed"]
    assert by_dim["traction"]["source_type"] == "user_confirmed"


def test_confirmed_negative_is_also_user_confirmed_not_penalized():
    funding = assess_funding_readiness({"traction": {"state": "confirmed_negative"}})
    ledger = build_evidence_ledger(funding)
    item = next(i for i in ledger if i["dimension"] == "traction")
    assert item["source_type"] == "user_confirmed"
    assert item["evidence_state"] == "confirmed_negative"


def test_not_sure_yet_becomes_user_not_sure():
    funding = assess_funding_readiness({"traction": {"state": "not_sure_yet"}})
    ledger = build_evidence_ledger(funding)
    item = next(i for i in ledger if i["dimension"] == "traction")
    assert item["source_type"] == "user_not_sure"
    assert item["base_confidence"] == SOURCE_TYPE_BASE_CONFIDENCE["user_not_sure"]


def test_not_applicable_produces_no_item():
    funding = assess_funding_readiness({"traction": {"state": "not_applicable"}})
    ledger = build_evidence_ledger(funding)
    assert not any(i["dimension"] == "traction" for i in ledger)


def test_market_evidence_blank_fields_produce_no_item():
    ledger = build_evidence_ledger(None, market_evidence={"customer_type": "", "target_market": None})
    assert ledger == []


def test_market_evidence_populated_fields_become_items():
    ledger = build_evidence_ledger(
        None,
        market_evidence={"customer_type": "Retail ops managers", "known_competitors": ["Acme", "Beta"]},
    )
    claims = {item["id"]: item for item in ledger}
    assert "market_evidence:customer_type" in claims
    assert "Retail ops managers" in claims["market_evidence:customer_type"]["claim"]
    assert "market_evidence:known_competitors" in claims
    assert "2 known competitor" in claims["market_evidence:known_competitors"]["claim"]


def test_industry_prediction_is_discounted_model_inference():
    ledger = build_evidence_ledger(None, industry_prediction={"predicted_industry": "fintech", "confidence": 0.8})
    item = next(i for i in ledger if i["id"] == "model:industry_prediction")
    assert item["source_type"] == "model_inference"
    assert item["base_confidence"] == round(0.8 * MODEL_INFERENCE_DISCOUNT, 4)


def test_no_industry_prediction_produces_no_model_item():
    ledger = build_evidence_ledger(None, industry_prediction=None)
    assert not any(i["source_type"] == "model_inference" for i in ledger)


def test_combine_confidence_empty_is_zero():
    assert combine_confidence([]) == 0.0


def test_combine_confidence_single_item_equals_its_base_confidence():
    items = [{"id": "a", "claim": "x", "dimension": None, "source_type": "user_confirmed",
              "base_confidence": 0.9, "evidence_state": None, "contradicts": []}]
    assert combine_confidence(items) == 0.9


def test_combine_confidence_independent_sources_raise_above_either_alone():
    items = [
        {"id": "a", "claim": "x", "dimension": None, "source_type": "user_confirmed",
         "base_confidence": 0.9, "evidence_state": None, "contradicts": []},
        {"id": "b", "claim": "y", "dimension": None, "source_type": "model_inference",
         "base_confidence": 0.4, "evidence_state": None, "contradicts": []},
    ]
    combined = combine_confidence(items)
    assert combined > 0.9
    assert combined == round(1 - (1 - 0.9) * (1 - 0.4), 4)


def test_combine_confidence_same_source_type_dedupes_via_max_not_sum():
    items = [
        {"id": "a", "claim": "x", "dimension": "d", "source_type": "user_confirmed",
         "base_confidence": 0.9, "evidence_state": None, "contradicts": []},
        {"id": "b", "claim": "y", "dimension": "d", "source_type": "user_confirmed",
         "base_confidence": 0.9, "evidence_state": None, "contradicts": []},
    ]
    # Two same-source items must not exceed a single item's confidence (no fake corroboration).
    assert combine_confidence(items) == 0.9


def test_confidence_for_dimension_is_zero_when_no_evidence_exists():
    ledger = build_evidence_ledger(assess_funding_readiness({"traction": {"state": "not_applicable"}}))
    assert confidence_for_dimension(ledger, "traction") == 0.0


def test_confidence_for_dimension_matches_the_single_item_it_has():
    funding = assess_funding_readiness({"traction": 2})
    ledger = build_evidence_ledger(funding)
    assert confidence_for_dimension(ledger, "traction") == SOURCE_TYPE_BASE_CONFIDENCE["user_confirmed"]


def test_summarize_ledger_shape_and_counts():
    from app.ml.funding_readiness import DIMENSIONS

    other_dims = {name: {"state": "not_applicable"} for name in DIMENSIONS if name not in ("problem_clarity", "traction")}
    funding = assess_funding_readiness(
        {**other_dims, "problem_clarity": 2, "traction": {"state": "not_sure_yet"}}
    )
    ledger = build_evidence_ledger(funding, market_evidence={"customer_type": "SMB owners"})
    summary = summarize_ledger(ledger)
    assert summary["evidence_ledger_version"] == "v1"
    assert summary["total_items"] == len(ledger)
    assert summary["items_by_source_type"]["user_confirmed"] >= 2
    assert summary["items_by_source_type"]["user_not_sure"] == 1
    assert 0.0 <= summary["overall_confidence"] <= 1.0


def test_never_fabricates_an_item_for_absent_data():
    ledger = build_evidence_ledger(None, market_evidence=None, industry_prediction=None)
    assert ledger == []
