from app.agents.industry_knowledge_packs import get_industry_knowledge_pack
from app.agents.startup_benchmark import build_startup_benchmark

_PACK = get_industry_knowledge_pack("Restaurant Operations Technology", "foodtech", ["Restaurants"], "canteen inventory")


def test_unavailable_retrieval_never_fabricates_industry_positioning():
    result = build_startup_benchmark({"available": False}, _PACK)
    assert result["retrieved_ventures_available"] is False
    assert result["industry_positioning_pattern"] is None


def test_every_non_positioning_field_is_labeled_general_startup_knowledge():
    retrieval = {
        "available": True,
        "neighbors": [{"name": "Acme", "industry": "foodtech", "similarity": 0.8}],
        "comparative_intelligence": {"available": True, "common_industry_positioning": {"available": False}},
    }
    result = build_startup_benchmark(retrieval, _PACK)
    for field in ("pricing_approach", "customer_acquisition_pattern", "typical_pilot_strategy", "common_mistakes", "typical_first_customer", "growth_path"):
        assert result[field]["source"] == "general_startup_knowledge"


def test_industry_positioning_is_retrieved_evidence_when_available():
    retrieval = {
        "available": True,
        "neighbors": [{"name": "Acme", "industry": "foodtech", "similarity": 0.8}],
        "comparative_intelligence": {
            "available": True,
            "common_industry_positioning": {"available": True, "support": "Most similar ventures are foodtech", "citations": ["Acme"]},
        },
    }
    result = build_startup_benchmark(retrieval, _PACK)
    assert result["industry_positioning_pattern"]["source"] == "retrieved_evidence"
    assert result["retrieved_ventures_used"][0]["name"] == "Acme"


def test_never_fabricates_a_competitor_name():
    result = build_startup_benchmark({"available": False}, _PACK)
    assert result["retrieved_ventures_used"] == []
