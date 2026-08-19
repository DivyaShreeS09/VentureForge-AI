from app.agents.regulatory_context import classify_regulatory_context


def test_no_match_for_a_plain_marketplace_idea():
    result = classify_regulatory_context(
        "A marketplace connecting independent truckers with small manufacturers needing freight.",
        "Logistics", [],
    )
    assert result is None


def test_healthcare_keyword_in_description_fires_even_without_taxonomy_match():
    result = classify_regulatory_context(
        "A telehealth app that connects patients with clinicians for remote diagnosis.", "Consumer Health", [],
    )
    assert result["category"] == "healthcare"
    assert "clinical validation" in result["note"].lower()


def test_healthcare_taxonomy_domain_fires_even_without_keyword():
    result = classify_regulatory_context("A dashboard for reviewing flagged cases.", "HealthTech Diagnostics", [])
    assert result["category"] == "healthcare"


def test_insurance_keyword_fires():
    result = classify_regulatory_context(
        "We underwrite pet insurance policies directly to consumers nationwide.", "Insurance", [],
    )
    assert result["category"] == "insurance"
    assert "licensing" in result["note"].lower()


def test_finance_keyword_fires():
    result = classify_regulatory_context(
        "A payroll advance app that lets gig workers access earned wages daily.", "Fintech", [],
    )
    assert result["category"] == "finance"


def test_legal_keyword_fires():
    result = classify_regulatory_context(
        "An AI tool that gives small businesses legal advice on contract review.", "LegalTech", [],
    )
    assert result["category"] == "legal"


def test_children_and_consent_requires_both_minor_and_sensitive_data_keyword():
    fires = classify_regulatory_context(
        "A smart mirror that uses facial recognition to detect depression risk in teenagers and "
        "alerts parents.",
        "Consumer Hardware", [],
    )
    assert fires["category"] == "children_and_consent"

    no_fire = classify_regulatory_context(
        "An app that helps teenagers find part-time jobs near their school.", "EdTech", [],
    )
    assert no_fire is None


def test_canteen_is_not_falsely_flagged_as_a_minors_and_consent_match():
    """Regression test (Master Product Differentiation Sprint): 'canteens'/'canteen' contains the
    substring 'teen'/'teens', which previously matched the minor-keyword check via plain substring
    search — found when app.agents.founder_intelligence's Moat Intelligence check (which reuses
    this classifier) flagged a routine college-canteen inventory startup as touching a children-
    and-consent regulatory category. 'teen'/'teens' must only match as whole words."""
    result = classify_regulatory_context(
        "A smart inventory and demand-forecasting system for college canteens, using a prototype "
        "we already built to track daily food usage and reduce waste.",
        "Restaurant Operations Technology", ["Restaurants", "College Campuses"],
    )
    assert result is None


def test_safety_critical_keyword_fires():
    result = classify_regulatory_context(
        "An autonomous vehicle navigation stack for last-mile delivery.", "Robotics", [],
    )
    assert result["category"] == "safety_critical"


def test_surveillance_and_privacy_keyword_fires_without_minors():
    result = classify_regulatory_context(
        "A workplace tool that uses facial recognition to track employee attendance.", "HR Tech", [],
    )
    assert result["category"] == "surveillance_and_privacy"


def test_returns_only_one_category_when_multiple_keywords_match():
    result = classify_regulatory_context(
        "A clinical app for teenagers that uses biometric monitoring and alerts parents without consent.",
        "Consumer Health", [],
    )
    # children_and_consent outranks healthcare in _CATEGORY_ORDER.
    assert result["category"] == "children_and_consent"


def test_explicit_disclaimer_is_not_falsely_flagged():
    result = classify_regulatory_context(
        "A plain-language contract explainer tool for small business owners, explicitly not "
        "offering legal advice.",
        "LegalTech", [],
    )
    assert result is None


def test_every_category_has_likelihood_and_impact():
    for description, domain in [
        ("A telehealth clinical diagnosis app.", "HealthTech Diagnostics"),
        ("We underwrite insurance policies.", "Insurance"),
    ]:
        result = classify_regulatory_context(description, domain, [])
        assert result["likelihood"] in ("high", "medium")
        assert result["impact"] in ("high", "medium")
        assert result["mitigation"]
