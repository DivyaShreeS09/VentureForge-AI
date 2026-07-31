from app.agents.venture_vocabulary import all_resolvable_categories, article_for, readable_label, resolve_category, vocab_for, with_article


def test_article_for_vowel_and_consonant_words():
    assert article_for("industrials") == "an"
    assert article_for("education") == "an"
    assert article_for("Enterprise AI") == "an"
    assert article_for("b2b") == "a"
    assert article_for("healthcare") == "a"


def test_with_article_composes_correctly():
    assert with_article("industrials") == "an industrials"
    assert with_article("b2b") == "a b2b"


def test_readable_label_uppercases_known_acronyms_only():
    assert readable_label("b2b") == "B2B"
    assert readable_label("Restaurant Operations Technology") == "Restaurant Operations Technology"


def test_resolve_category_matches_healthcare_and_hardware():
    assert resolve_category("Clinical Decision Support", None, []) == "healthcare"
    assert resolve_category("Robotics", "hardware", []) == "hardware"
    assert resolve_category(None, None, []) == "generic"


def test_vocab_for_returns_distinct_vocab_per_category():
    healthcare_vocab = vocab_for("Clinical Decision Support", None, [])
    hardware_vocab = vocab_for("Robotics", "hardware", [])
    generic_vocab = vocab_for(None, None, [])
    assert healthcare_vocab["pilot_noun"] != hardware_vocab["pilot_noun"]
    assert generic_vocab["pilot_noun"] == "a pilot"


def test_master_startup_knowledge_base_sprint_new_domains_resolve_distinctly():
    """Phase 3: new domains must resolve to their own category, not collide with an existing one
    or silently fall through to generic/b2b."""
    assert resolve_category("LegalTech", None, [], "a contract review tool for law firms") == "legaltech"
    assert resolve_category("HRTech", None, [], "an applicant tracking system") == "hrtech"
    assert resolve_category("Insurance", None, [], "we underwrite pet insurance policies") == "insurance"
    assert resolve_category(None, None, [], "we underwrite pet insurance policies") != "fintech"
    assert resolve_category("GovTech", None, [], "a permitting tool for a municipal government agency") == "govtech"
    assert resolve_category("AgTech", None, [], "a precision farming tool for crop monitoring") == "agriculture"


def test_classified_industry_wins_over_incidental_description_keyword():
    """Final AI Quality Sprint, Phase 2: the pre-submission audit found a cybersecurity startup
    whose own description mentioned "healthcare and legal" customers get Healthcare advice instead
    of Cybersecurity. The venture's own already-classified industry/domain must always win over an
    incidental keyword inside the free-text description."""
    description = (
        "An AI-driven phishing simulation and security-awareness training platform for SMBs, "
        "already piloted with a few healthcare and legal services customers."
    )
    # Classified signal alone (no description) already says cybersecurity -> must win outright.
    assert resolve_category("Cybersecurity", "b2b", [], description) == "cybersecurity"
    # Even with only a coarse classified label, the description's OWN cybersecurity vocabulary
    # (phishing, security-awareness) must outrank the incidental "healthcare" customer mention.
    assert resolve_category(None, "b2b", [], description) == "cybersecurity"


def test_specific_category_beats_generic_b2b_catch_all_even_when_b2b_is_the_classified_label():
    """Classifying as "b2b" must never short-circuit resolution before the description is even
    consulted — "b2b" is a last-resort catch-all, not a real signal."""
    assert resolve_category("b2b", "b2b", [], "a contract review tool for law firms") == "legaltech"


def test_confidence_ranking_prefers_more_matched_keywords_not_first_dict_entry():
    """A description matching two categories must resolve to whichever has more real keyword
    matches, not whichever appears first in the dict (previously: first-match-wins)."""
    # "logistics" appears once ("logistics"); "healthcare" appears via a single incidental "health"
    # substring but has fewer real matches than a description genuinely about logistics.
    description = "A logistics platform optimizing fleet routes and last-mile delivery for health food distributors."
    assert resolve_category(None, None, [], description) == "logistics"


def test_coarse_industrials_label_does_not_hijack_a_more_specific_description():
    """Regression: including `model_category_label` in the stage-1 "always wins" haystack let the
    coarse classifier label "industrials" (which substring-matches hardware's "industrial" keyword)
    pull a ClimateTech pitch into the hardware knowledge pack before its own much more specific
    "carbon"/"emissions" description text was ever counted. `model_category_label` must only
    contribute at the confidence-ranked (stage 2) level, same as the description."""
    category = resolve_category(
        "Sustainability Technology",
        "industrials",
        [],
        "We sell carbon-accounting software that helps mid-market manufacturers track and report "
        "their emissions for sustainability disclosures.",
    )
    assert category == "climatetech"


def test_all_resolvable_categories_includes_generic_and_every_keyword_bucket():
    categories = all_resolvable_categories()
    assert "generic" in categories
    assert "healthcare" in categories
    assert "legaltech" in categories
    assert len(categories) == len(set(categories))
