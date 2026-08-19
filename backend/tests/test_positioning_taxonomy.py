from app.ml.positioning_taxonomy import (
    MIN_DISTINCT_CONCEPTS,
    extract_deployment_sectors,
    score_taxonomy,
    taxonomy_is_ambiguous,
)


def test_single_generic_word_is_not_eligible():
    """A single generic shared word must never make a domain an eligible candidate on its own —
    this was the exact bug found in the Phase -1 prototype."""
    result = score_taxonomy("A generic app for people.")
    domains = {c["domain"] for c in result["candidates"]}
    # General Consumer App matches "app" and "people" -> 2 distinct concepts, genuinely eligible.
    assert "General Consumer App" in domains
    for candidate in result["candidates"]:
        assert candidate["distinct_concept_count"] >= MIN_DISTINCT_CONCEPTS or candidate["high_specificity_matches"]


def test_repeated_generic_word_does_not_count_as_multiple_concepts():
    result = score_taxonomy("app app app app app")
    # "app" repeated many times is still exactly one distinct concept -> below the eligibility
    # floor with no high-specificity match -> General Consumer App must not be a candidate.
    domains = {c["domain"] for c in result["candidates"]}
    assert "General Consumer App" not in domains


def test_single_high_specificity_phrase_is_sufficient():
    result = score_taxonomy("A tool for diabetic foot care.")
    domains = {c["domain"]: c for c in result["candidates"]}
    assert "HealthTech Diagnostics" in domains
    assert "diabetic foot" in domains["HealthTech Diagnostics"]["matched_concepts"]


def test_candidates_are_ranked_by_weighted_score_descending():
    result = score_taxonomy(
        "A marketplace where university students can find teammates for hackathons, projects, and startups."
    )
    scores = [c["weighted_score"] for c in result["candidates"]]
    assert scores == sorted(scores, reverse=True)


def test_narrower_domain_wins_tie_break_over_broader_specificity_rank():
    """Construct two eligible candidates with an identical weighted_score and identical
    high-specificity/concept counts — the narrower specificity_rank must win, never insertion
    order."""
    from app.ml.positioning_taxonomy import _rank_key

    broad = {
        "domain": "Zebra Broad Domain",
        "weighted_score": 0.5,
        "high_specificity_matches": [],
        "high_specificity_weight_sum": 0.0,
        "distinct_concept_count": 2,
        "specificity_rank": 9,
        "deployment_sectors": [],
    }
    narrow = {
        "domain": "Aardvark Narrow Domain",
        "weighted_score": 0.5,
        "high_specificity_matches": [],
        "high_specificity_weight_sum": 0.0,
        "distinct_concept_count": 2,
        "specificity_rank": 1,
        "deployment_sectors": [],
    }
    ranked = sorted([broad, narrow], key=lambda c: _rank_key(c, set()))
    # Alphabetically "Aardvark..." would sort first if rank fell through to the alphabetical
    # fallback — but specificity_rank must be compared *before* alphabetical, so the narrower
    # domain (rank 1) wins regardless of its name.
    assert ranked[0]["domain"] == "Aardvark Narrow Domain"


def test_alphabetical_fallback_is_deterministic_not_insertion_order():
    from app.ml.positioning_taxonomy import _rank_key

    a = {
        "domain": "Zzz Domain", "weighted_score": 0.5, "high_specificity_matches": [],
        "high_specificity_weight_sum": 0.0, "distinct_concept_count": 2, "specificity_rank": 3,
        "deployment_sectors": [],
    }
    b = {
        "domain": "Aaa Domain", "weighted_score": 0.5, "high_specificity_matches": [],
        "high_specificity_weight_sum": 0.0, "distinct_concept_count": 2, "specificity_rank": 3,
        "deployment_sectors": [],
    }
    # Insertion order here is [a, b] (Zzz before Aaa) — the sort must still put Aaa first.
    ranked = sorted([a, b], key=lambda c: _rank_key(c, set()))
    assert ranked[0]["domain"] == "Aaa Domain"


def test_deployment_sector_extraction_retains_matched_text():
    sectors = extract_deployment_sectors("A tool for hotels and campuses.")
    by_name = {s["sector"]: s for s in sectors}
    assert "Hotels" in by_name and "hotels" in by_name["Hotels"]["matched_text"]
    assert "Campuses" in by_name and "campuses" in by_name["Campuses"]["matched_text"]


def test_no_eligible_candidates_returns_empty_list_and_is_ambiguous():
    result = score_taxonomy("Xyzzy quux flarp.")
    assert result["candidates"] == []
    assert taxonomy_is_ambiguous(result["candidates"]) is True


def test_robotics_pitch_resolves_to_robotics_not_enterprise_ai():
    """Final AI Quality Sprint, Phase 1: the pre-submission audit found a real warehouse-robotics
    pitch confidently mislabeled as Enterprise AI because no Robotics domain existed at all."""
    result = score_taxonomy(
        "We build autonomous picking robots that use computer vision and robotic arms to fulfill "
        "e-commerce orders inside warehouse fulfillment centers, cutting the number of temporary "
        "pickers a warehouse needs during peak season."
    )
    assert result["candidates"][0]["domain"] == "Robotics & Industrial Hardware"
    assert "Enterprise AI" not in {c["domain"] for c in result["candidates"]}


def test_logistics_pitch_resolves_to_logistics_not_enterprise_ai():
    result = score_taxonomy(
        "We help grocery delivery companies plan smarter last-mile routes across their driver "
        "fleet, cutting delivery time and fuel cost by continuously re-optimizing each driver's "
        "route as new orders come in."
    )
    assert result["candidates"][0]["domain"] == "Logistics & Supply Chain"
    assert "Enterprise AI" not in {c["domain"] for c in result["candidates"]}


def test_retail_subscription_pitch_resolves_to_retail_not_enterprise_ai():
    result = score_taxonomy(
        "We run a subscription box service that uses a short style quiz to curate a personalized "
        "set of clothing items for each subscriber every month, shipped directly from our online "
        "store."
    )
    assert result["candidates"][0]["domain"] == "Retail & E-commerce"
    assert "Enterprise AI" not in {c["domain"] for c in result["candidates"]}


def test_all_scores_retained_for_explainability_even_when_ineligible():
    result = score_taxonomy("An app for people.")
    all_domains = {c["domain"] for c in result["all_scores"]}
    # Every taxonomy domain must have a score record, whether or not it became a candidate.
    from app.ml.positioning_taxonomy import POSITIONING_TAXONOMY

    assert all_domains == set(POSITIONING_TAXONOMY.keys())
