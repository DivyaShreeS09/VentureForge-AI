from pathlib import Path

import joblib
import pytest
from sklearn.cluster import KMeans
from sklearn.preprocessing import RobustScaler

from app.agents import student3
from app.ml.funding_readiness import assess_funding_readiness
from app.ml.segmentation import SegmentationArtifactUnavailable, load_segmentation_artifact


def test_student3_outputs_are_grounded_and_do_not_claim_traction():
    funding = assess_funding_readiness({"problem_clarity": 2})
    segment = student3.customer_segment(None, funding)
    actions = student3.ranked_actions(funding, None, segment)
    deck = student3.pitch_deck("Nova", "A workflow tool for operations teams.", None, funding, segment, actions)

    assert segment["method"] == "unavailable"
    assert actions[0]["ranking_version"] == "next-action-rules-v1"
    traction = next(slide for slide in deck if slide["title"] == "Traction and evidence")
    assert "Unknown:" in traction["content"][0]


def test_risks_use_supported_categories_and_mitigations():
    risks = student3.risks(assess_funding_readiness({}), None)
    assert {risk["category"] for risk in risks} == {
        "market", "adoption", "competition", "technical", "operations", "financial",
        "regulatory_legal", "execution_team", "privacy_security",
    }
    assert all(risk["mitigation"] for risk in risks)


def test_pitch_deck_labels_unknown_values_and_includes_required_sections():
    funding = assess_funding_readiness({})
    segment = student3.customer_segment(None, funding)
    deck = student3.pitch_deck("Nova", "A workflow tool for operations teams.", None, funding, segment, [])
    titles = {slide["title"] for slide in deck}
    assert {"Business Model", "Go-to-Market", "Financial Outlook", "Team", "Demo Script"}.issubset(titles)
    financials = next(slide for slide in deck if slide["title"] == "Financial Outlook")
    assert financials["evidence_status"] == "unknown"


def test_segmentation_artifact_can_be_loaded_and_rejected_when_version_is_wrong(tmp_path):
    artifact_path = tmp_path / "segmentation_artifact.joblib"
    scaler = RobustScaler().fit([[0, 0, 0], [1, 1, 1]])
    model = KMeans(n_clusters=2, random_state=42, n_init=1).fit([[0, 0, 0], [1, 1, 1]])
    payload = {
        "schema_version": "1.0",
        "model_version": "v1",
        "feature_order": ["recency_days", "frequency", "monetary"],
        "selected_model_name": "kmeans",
        "selected_n_clusters": 4,
        "segment_label_mapping": {0: "Cluster 0", 1: "Cluster 1"},
        "scaler": scaler,
        "clustering_model": model,
        "cluster_profiles": [{"cluster_id": 0}, {"cluster_id": 1}],
    }
    joblib.dump(payload, artifact_path)

    loaded = load_segmentation_artifact(artifact_path)
    assert loaded["model_version"] == "v1"

    incompatible = dict(payload)
    incompatible["schema_version"] = "2.0"
    incompatible_path = tmp_path / "incompatible.joblib"
    joblib.dump(incompatible, incompatible_path)

    with pytest.raises(SegmentationArtifactUnavailable, match="schema version"):
        load_segmentation_artifact(incompatible_path)


def test_customer_segment_degrades_gracefully_without_customer_rfm():
    funding = assess_funding_readiness({"problem_clarity": 2})
    segment = student3.customer_segment(None, funding, customer_rfm=None)

    assert segment["method"] == "unavailable"
    assert "not supplied" in segment["limitations"][0]


def test_ranking_changes_when_inputs_change():
    funding = assess_funding_readiness({"problem_clarity": 2, "traction": 1})
    baseline_segment = student3.customer_segment(None, funding, customer_rfm=None)
    baseline_actions = student3.ranked_actions(funding, None, baseline_segment)

    richer_funding = assess_funding_readiness({"problem_clarity": 2, "traction": 2, "revenue_model_clarity": 2})
    richer_segment = student3.customer_segment(None, richer_funding, customer_rfm=None)
    richer_actions = student3.ranked_actions(richer_funding, None, richer_segment)

    assert baseline_actions[0]["title"] != richer_actions[0]["title"]
