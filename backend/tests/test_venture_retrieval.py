import numpy as np

from app.ml.venture_retrieval import (
    VentureRetrievalIndex,
    build_comparative_intelligence,
    get_retrieval_index,
    retrieve_similar_ventures,
)


class _FakeModel:
    """Deterministic stand-in for SentenceTransformer — never loads a real model, never touches
    the network. Maps a description to a fixed embedding via a simple hash so tests are fast and
    fully offline, matching this repo's global Gemini-isolation convention for other ML/LLM deps."""

    def encode(self, texts, show_progress_bar=False, convert_to_numpy=True):
        return np.array([self._embed(t) for t in texts])

    @staticmethod
    def _embed(text: str) -> list[float]:
        seed = abs(hash(text)) % (2**32)
        rng = np.random.default_rng(seed)
        return rng.normal(size=8).tolist()


def _make_index(records, embeddings):
    return VentureRetrievalIndex(np.array(embeddings), records, _FakeModel())


def test_retrieve_returns_top_k_by_similarity():
    records = [
        {"name": "Acme Canteen", "description": "canteen ordering for offices", "industry": "b2b"},
        {"name": "MediCo", "description": "hospital patient monitoring", "industry": "healthcare"},
        {"name": "PayFast", "description": "instant loans for gig workers", "industry": "fintech"},
    ]
    embeddings = [[1, 0, 0, 0, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0, 0, 0], [0, 0, 1, 0, 0, 0, 0, 0]]

    class _QueryModel(_FakeModel):
        def encode(self, texts, show_progress_bar=False, convert_to_numpy=True):
            return np.array([[1, 0, 0, 0, 0, 0, 0, 0]])

    index = VentureRetrievalIndex(np.array(embeddings), records, _QueryModel())
    results = index.retrieve("a canteen app", k=2)
    assert len(results) == 2
    assert results[0]["name"] == "Acme Canteen"
    assert results[0]["similarity"] > results[1]["similarity"]


def test_retrieve_includes_why_similar_and_never_fabricates_shared_terms():
    records = [{"name": "FoodOps", "description": "canteen waste tracking for corporate campuses", "industry": "b2b"}]
    embeddings = [[1, 0, 0, 0, 0, 0, 0, 0]]

    class _QueryModel(_FakeModel):
        def encode(self, texts, show_progress_bar=False, convert_to_numpy=True):
            return np.array([[1, 0, 0, 0, 0, 0, 0, 0]])

    index = VentureRetrievalIndex(np.array(embeddings), records, _QueryModel())
    results = index.retrieve("canteen waste tracking for schools", k=1)
    assert "canteen" in results[0]["why_similar"]
    assert "waste" in results[0]["why_similar"]


def test_disabled_by_default_returns_unavailable_never_raises(monkeypatch):
    get_retrieval_index.cache_clear()
    result = retrieve_similar_ventures("a smart canteen app")
    assert result["available"] is False
    assert result["neighbors"] == []
    assert "note" in result
    get_retrieval_index.cache_clear()


def test_empty_description_never_fabricates_neighbors():
    result = retrieve_similar_ventures("")
    assert result["available"] is False
    assert result["neighbors"] == []


def test_provenance_disclaimer_always_present_when_available(monkeypatch):
    fake_index = _make_index(
        [{"name": "X", "description": "y", "industry": "b2b"}], [[1, 0, 0, 0, 0, 0, 0, 0]]
    )
    monkeypatch.setattr("app.ml.venture_retrieval.get_retrieval_index", lambda: fake_index)
    result = retrieve_similar_ventures("a test description")
    assert result["available"] is True
    assert "historical" in result["provenance_disclaimer"].lower()
    assert "not verified as current competitors" in result["provenance_disclaimer"].lower()


def test_comparative_intelligence_industry_consensus_has_citations_and_confidence():
    neighbors = [
        {"name": "Alpha", "description": "canteen ordering for offices", "industry": "b2b", "similarity": 0.7, "why_similar": "x"},
        {"name": "Beta", "description": "canteen waste tracking", "industry": "b2b", "similarity": 0.6, "why_similar": "x"},
        {"name": "Gamma", "description": "hospital scheduling", "industry": "healthcare", "similarity": 0.4, "why_similar": "x"},
    ]
    ci = build_comparative_intelligence(neighbors)
    assert ci["available"] is True
    industry = ci["common_industry_positioning"]
    assert industry["value"] == "b2b"
    assert industry["confidence"] == "high"  # 2 of 3 = 0.667 >= the 0.6 threshold
    assert set(industry["citations"]) == {"Alpha", "Beta"}
    assert industry["provenance"] == "deterministic_reasoning_over_retrieved_evidence"


def test_comparative_intelligence_high_confidence_when_majority_strong():
    neighbors = [
        {"name": n, "description": "canteen ordering", "industry": "b2b", "similarity": 0.5, "why_similar": "x"}
        for n in ("A", "B", "C", "D")
    ] + [{"name": "E", "description": "hospital", "industry": "healthcare", "similarity": 0.3, "why_similar": "x"}]
    ci = build_comparative_intelligence(neighbors)
    assert ci["common_industry_positioning"]["confidence"] == "high"


def test_comparative_intelligence_common_terminology_requires_two_ventures():
    neighbors = [
        {"name": "Alpha", "description": "canteen ordering software", "industry": "b2b", "similarity": 0.7, "why_similar": "x"},
        {"name": "Beta", "description": "canteen waste tracking tool", "industry": "b2b", "similarity": 0.6, "why_similar": "x"},
    ]
    ci = build_comparative_intelligence(neighbors)
    terms = {t["term"] for t in ci["common_terminology"]["terms"]}
    assert "canteen" in terms


def test_comparative_intelligence_explicitly_states_unsupported_dimensions():
    neighbors = [{"name": "Alpha", "description": "canteen ordering", "industry": "b2b", "similarity": 0.7, "why_similar": "x"}]
    ci = build_comparative_intelligence(neighbors)
    for dim in ("common_pricing_model", "common_deployment_strategy", "common_go_to_market_motion"):
        assert ci[dim]["available"] is False
        assert ci[dim]["note"]  # must explain why, never silently omitted


def test_comparative_intelligence_geography_and_funding_stage_require_real_metadata():
    """Master Startup Corpus Expansion Sprint, Phase 7: these two dimensions must only be marked
    available when the actually-retrieved neighbors carry that field — never fabricated for
    older-style records that lack it."""
    neighbors_without_metadata = [{"name": "Alpha", "description": "canteen ordering", "industry": "b2b", "similarity": 0.7, "why_similar": "x"}]
    ci = build_comparative_intelligence(neighbors_without_metadata)
    assert ci["common_geography"]["available"] is False
    assert ci["common_funding_stage_pattern"]["available"] is False

    neighbors_with_metadata = [
        {"name": "Alpha", "description": "canteen ordering", "industry": "b2b", "similarity": 0.7, "why_similar": "x", "country": "United States", "funding_stage": "Early"},
        {"name": "Beta", "description": "canteen waste tracking", "industry": "b2b", "similarity": 0.6, "why_similar": "x", "country": "United States", "funding_stage": "Growth"},
    ]
    ci2 = build_comparative_intelligence(neighbors_with_metadata)
    assert ci2["common_geography"]["available"] is True
    assert ci2["common_geography"]["value"] == "United States"
    assert "2 of 2" in ci2["common_geography"]["coverage"]
    assert ci2["common_funding_stage_pattern"]["available"] is True


def test_comparative_intelligence_empty_neighbors_never_fabricates():
    ci = build_comparative_intelligence([])
    assert ci["available"] is False
    for dim in ("common_pricing_model", "common_deployment_strategy", "common_go_to_market_motion", "common_geography", "common_funding_stage_pattern"):
        assert ci[dim]["available"] is False


def test_known_industry_reranks_same_industry_candidate_ahead_of_close_competitor():
    """Master Startup Corpus Expansion Sprint, Phase 6: a small industry-match boost should be
    able to flip the ordering of two NEAR-tied candidates in favor of the one sharing the
    already-known (classifier-predicted) industry — without ever changing the reported
    `similarity` value itself (that stays the true, unboosted cosine similarity)."""
    records = [
        {"name": "SlightlyCloser", "description": "x", "industry": "healthcare"},
        {"name": "SameIndustry", "description": "y", "industry": "fintech"},
    ]

    class _QueryModel(_FakeModel):
        def encode(self, texts, show_progress_bar=False, convert_to_numpy=True):
            return np.array([[1, 0, 0, 0, 0, 0, 0, 0]])

    # SlightlyCloser is marginally more similar by raw cosine similarity than SameIndustry.
    embeddings = [[0.99, 0.01, 0, 0, 0, 0, 0, 0], [0.9, 0.1, 0, 0, 0, 0, 0, 0]]
    index = VentureRetrievalIndex(np.array(embeddings), records, _QueryModel())

    unranked = index.retrieve("query", k=2)
    assert unranked[0]["name"] == "SlightlyCloser"

    reranked = index.retrieve("query", k=2, known_industry="fintech")
    assert reranked[0]["name"] == "SameIndustry"
    # The reported similarity is still the TRUE cosine similarity, never boosted in the output.
    assert reranked[0]["similarity"] < reranked[1]["similarity"]


def test_known_industry_none_behaves_identically_to_no_reranking():
    records = [{"name": "A", "description": "x", "industry": "b2b"}, {"name": "B", "description": "y", "industry": "healthcare"}]
    embeddings = [[1, 0, 0, 0, 0, 0, 0, 0], [0.5, 0.5, 0, 0, 0, 0, 0, 0]]

    class _QueryModel(_FakeModel):
        def encode(self, texts, show_progress_bar=False, convert_to_numpy=True):
            return np.array([[1, 0, 0, 0, 0, 0, 0, 0]])

    index = VentureRetrievalIndex(np.array(embeddings), records, _QueryModel())
    assert index.retrieve("query", k=2) == index.retrieve("query", k=2, known_industry=None)


def test_retrieve_similar_ventures_reports_whether_reranking_was_applied(monkeypatch):
    fake_index = _make_index(
        [{"name": "X", "description": "y", "industry": "b2b"}], [[1, 0, 0, 0, 0, 0, 0, 0]]
    )
    monkeypatch.setattr("app.ml.venture_retrieval.get_retrieval_index", lambda: fake_index)
    result = retrieve_similar_ventures("a test description", known_industry="b2b")
    assert result["industry_reranking_applied"] is True
    result2 = retrieve_similar_ventures("a test description")
    assert result2["industry_reranking_applied"] is False


def test_retrieval_failure_degrades_gracefully_never_raises(monkeypatch):
    class _BrokenIndex:
        def retrieve(self, description, k=5):
            raise RuntimeError("boom")

    monkeypatch.setattr("app.ml.venture_retrieval.get_retrieval_index", lambda: _BrokenIndex())
    result = retrieve_similar_ventures("a test description")
    assert result["available"] is False
    assert result["method"] == "error"
