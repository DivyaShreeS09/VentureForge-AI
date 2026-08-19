import numpy as np

from app.ml.venture_space_analytics import VentureSpaceAnalyticsData, analyze_venture_space


def _data(reference_sims, centroids=None):
    return VentureSpaceAnalyticsData(
        industries=None,
        industry_centroids=centroids or {},
        reference_nn_similarities=np.array(reference_sims),
    )


def test_novelty_score_is_one_minus_max_similarity():
    similarities = np.array([0.1, 0.3, 0.9, 0.2])
    result = analyze_venture_space(similarities, np.array([1.0, 0.0]), None, _data([0.5] * 100))
    assert result["novelty_score"]["value"] == round(1.0 - 0.9, 4)


def test_novelty_percentile_reflects_reference_distribution():
    # max_sim=0.9 is well ABOVE every value in a reference distribution capped at 0.6 -- this
    # venture has an unusually STRONG nearest-neighbor match, i.e. it is the opposite of novel,
    # so its novelty percentile should be ~0 (it beats none of the reference distribution).
    reference = list(np.linspace(0.2, 0.6, 1000))
    similarities = np.array([0.9, 0.1])
    result = analyze_venture_space(similarities, np.array([1.0, 0.0]), None, _data(reference))
    assert result["novelty_score"]["percentile_vs_reference"] == 0.0


def test_competition_density_counts_above_threshold():
    similarities = np.array([0.6, 0.4, 0.55, 0.9, 0.3])
    result = analyze_venture_space(similarities, np.array([1.0, 0.0]), None, _data([0.5] * 100))
    # threshold is 0.5 -> 0.6, 0.55, 0.9 qualify = 3
    assert result["competition_density"]["count"] == 3
    assert result["competition_density"]["fraction_of_corpus"] == round(3 / 5, 4)


def test_innovation_distance_and_market_crowdedness_use_real_industry_centroid():
    centroids = {
        "fintech": {"centroid": np.array([1.0, 0.0]), "size": 500, "fraction_of_corpus": 0.5},
    }
    similarities = np.array([0.5, 0.5])
    query_normalized = np.array([1.0, 0.0])  # identical to the centroid -> distance should be 0
    result = analyze_venture_space(similarities, query_normalized, "fintech", _data([0.5] * 100, centroids))
    assert result["innovation_distance"]["value"] == 0.0
    assert result["market_crowdedness"]["value"] == 0.5
    assert result["market_crowdedness"]["industry"] == "fintech"


def test_innovation_distance_is_none_when_industry_unknown():
    result = analyze_venture_space(np.array([0.5, 0.5]), np.array([1.0, 0.0]), "unknown_industry", _data([0.5] * 100))
    assert result["innovation_distance"] is None
    assert result["market_crowdedness"] is None


def test_opportunity_isolation_is_a_disclosed_composite_not_independent():
    # low density AND high novelty percentile -> isolated
    reference = list(np.linspace(0.2, 0.9, 1000))
    similarities = np.array([0.21, 0.1, 0.15])  # all below threshold=0.5 -> density fraction=0
    result = analyze_venture_space(similarities, np.array([1.0, 0.0]), None, _data(reference))
    assert result["opportunity_isolation"]["is_isolated"] is True
    assert "not an independently computed" in result["opportunity_isolation"]["definition"].lower()


def test_opportunity_isolation_false_when_crowded():
    similarities = np.array([0.9, 0.85, 0.8, 0.7])  # dense
    result = analyze_venture_space(similarities, np.array([1.0, 0.0]), None, _data([0.5] * 100))
    assert result["opportunity_isolation"]["is_isolated"] is False


def test_venture_cluster_is_explicitly_rejected_with_reason():
    result = analyze_venture_space(np.array([0.5, 0.5]), np.array([1.0, 0.0]), None, _data([0.5] * 100))
    assert result["venture_cluster"]["status"] == "rejected"
    assert "silhouette" in result["venture_cluster"]["reason"].lower()


def test_similarity_distribution_reports_real_descriptive_stats():
    similarities = np.array([0.1, 0.2, 0.3, 0.4])
    result = analyze_venture_space(similarities, np.array([1.0, 0.0]), None, _data([0.3, 0.4, 0.5]))
    dist = result["similarity_distribution"]
    assert dist["mean"] == round(float(similarities.mean()), 4)
    assert dist["max"] == round(float(similarities.max()), 4)
