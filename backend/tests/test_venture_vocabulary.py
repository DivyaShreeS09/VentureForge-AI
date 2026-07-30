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


def test_all_resolvable_categories_includes_generic_and_every_keyword_bucket():
    categories = all_resolvable_categories()
    assert "generic" in categories
    assert "healthcare" in categories
    assert "legaltech" in categories
    assert len(categories) == len(set(categories))
