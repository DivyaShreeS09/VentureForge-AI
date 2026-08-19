from app.ml.capability_library import classify_capabilities, get_capabilities_for_domain
from app.ml.positioning_taxonomy import POSITIONING_TAXONOMY


def _ids(bucket: list[dict]) -> list[str]:
    return [c["id"] for c in bucket]


def test_deterministic_fallback_supports_every_controlled_domain():
    for domain in POSITIONING_TAXONOMY:
        capabilities = get_capabilities_for_domain(domain)
        assert capabilities, f"domain {domain!r} has no capability library entry or fallback"


def test_unknown_domain_falls_back_to_generic_capabilities():
    capabilities = get_capabilities_for_domain("Not A Real Domain")
    assert capabilities == get_capabilities_for_domain(None)


def test_campus_resource_monitoring_classifies_real_time_monitoring_as_present():
    description = (
        "An autonomous system that monitors electricity, water, and occupancy across a campus or "
        "hotel and flags waste in real time."
    )
    result = classify_capabilities(description, "Smart Facilities Technology", is_low_confidence=False)
    assert "real_time_utility_monitoring" in _ids(result["present_capabilities"])
    assert len(result["recommended_capabilities"]) >= 1
    # "flags waste in real time" also matches anomaly_alerting's own concepts, so its dependents
    # (predictive_maintenance, automated_hvac_control) are eligible here, not premature — but a
    # capability appearing in *any* bucket must never appear in more than one bucket.
    all_ids = (
        _ids(result["present_capabilities"]) + _ids(result["recommended_capabilities"])
        + _ids(result["premature_capabilities"]) + _ids(result["not_relevant_capabilities"])
    )
    assert len(all_ids) == len(set(all_ids))


def test_diabetic_foot_platform_recommends_clinician_review_before_autonomous_diagnosis():
    description = "An AI platform for early diabetic-foot risk detection."
    result = classify_capabilities(description, "HealthTech Diagnostics", is_low_confidence=False)
    assert "risk_flagging" in _ids(result["present_capabilities"])
    recommended_ids = set(_ids(result["recommended_capabilities"]))
    assert "clinician_review_workflow" in recommended_ids
    assert "autonomous_diagnosis" in _ids(result["premature_capabilities"])
    assert "autonomous_diagnosis" not in recommended_ids


def test_restaurant_inventory_recommends_pos_integration_only_after_manual_logging_present():
    description = "Software that helps small restaurants track inventory and reduce food waste."
    result = classify_capabilities(description, "Restaurant Operations Technology", is_low_confidence=False)
    present_ids = set(_ids(result["present_capabilities"]))
    assert "manual_inventory_logging" in present_ids
    assert "waste_tracking" in present_ids
    # pos_integration's only prerequisite (manual_inventory_logging) is present, so it must be
    # eligible (recommended or not_relevant), never premature.
    assert "pos_integration" not in _ids(result["premature_capabilities"])
    assert "automated_reorder_suggestions" in _ids(result["premature_capabilities"])


def test_student_marketplace_recommends_only_relevant_capabilities():
    description = "A marketplace where university students can find teammates for hackathons, projects, and startups."
    result = classify_capabilities(description, "Peer Collaboration Marketplaces", is_low_confidence=False)
    present_ids = set(_ids(result["present_capabilities"]))
    assert "profile_and_skill_matching" in present_ids
    assert "single_event_pilot_mode" in present_ids
    assert "payments_and_monetization" in _ids(result["premature_capabilities"])


def test_vague_productivity_idea_keeps_recommendations_minimal():
    description = "An app for helping people be more productive."
    result = classify_capabilities(description, "General Consumer App", is_low_confidence=True)
    assert len(result["recommended_capabilities"]) <= 1


def test_present_capabilities_are_never_recommended_again():
    description = "Software that helps small restaurants track inventory and reduce food waste."
    result = classify_capabilities(description, "Restaurant Operations Technology", is_low_confidence=False)
    present_ids = set(_ids(result["present_capabilities"]))
    recommended_ids = set(_ids(result["recommended_capabilities"]))
    assert present_ids.isdisjoint(recommended_ids)
