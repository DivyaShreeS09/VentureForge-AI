from app.agents.industry_knowledge_packs import _PACKS, _REQUIRED_FIELDS, get_industry_knowledge_pack, supported_categories


def test_every_pack_has_every_required_field_and_no_invented_statistics():
    for category, pack in _PACKS.items():
        for field in _REQUIRED_FIELDS:
            assert field in pack, f"{category} missing {field}"
        # No dollar figures presented as fact anywhere in the pack — every fact must be
        # qualitative, never a specific invented price/statistic.
        joined = " ".join(" ".join(v) if isinstance(v, list) else v for v in pack.values())
        assert "$" not in joined, f"{category} pack contains a dollar figure"


def test_resolves_to_correct_category():
    pack = get_industry_knowledge_pack("Restaurant Operations Technology", "foodtech", ["Restaurants"], "canteen inventory system")
    assert pack["category"] == "foodtech"
    assert "kitchen" in pack["buying_process"].lower() or "site" in pack["buying_process"].lower()


def test_unknown_category_falls_back_to_generic_pack():
    pack = get_industry_knowledge_pack(None, None, [], "a completely novel business concept")
    assert pack["category"] == "generic"
    assert pack["buying_process"]


def test_never_claims_a_specific_real_company():
    pack = get_industry_knowledge_pack("Fintech", "fintech", [], "a payments startup")
    joined = str(pack)
    for banned in ("Stripe", "Salesforce", "Epic Systems", "Airbnb"):
        assert banned not in joined


def test_master_startup_knowledge_base_sprint_new_categories_resolve_correctly():
    """Phase 3: new domains must resolve to their own dedicated pack, not fall back to generic or
    collide with an existing category."""
    cases = [
        ("LegalTech", "legaltech", [], "a contract review tool for law firms"),
        ("HRTech", "hrtech", [], "an applicant tracking and recruiting platform"),
        ("PropTech", "proptech", [], "a property management tool for landlords"),
        ("Insurance", "insurance", [], "an underwriting and claims processing tool for insurers"),
        ("GovTech", "govtech", [], "a permitting tool for a government agency"),
        ("Agriculture", "agriculture", [], "a precision farming tool for crop monitoring"),
        ("Gaming", "gaming", [], "a live-ops tool for a game studio"),
    ]
    for primary_domain, model_label, sectors, description in cases:
        pack = get_industry_knowledge_pack(primary_domain, model_label, sectors, description)
        assert pack["category"] != "generic", f"{description!r} incorrectly fell back to generic"


def test_hardware_category_has_its_own_dedicated_pack():
    """hardware previously fell back to the generic pack even though venture_vocabulary already
    resolved a 'hardware' category — a real pre-existing gap this sprint closed."""
    pack = get_industry_knowledge_pack("Hardware", "hardware", [], "an industrial robotics company")
    assert pack["category"] == "hardware"
    assert "trial" in pack["pilot_strategy"].lower()


def test_all_packs_expose_the_phase_2_expanded_field_set():
    expanded_fields = (
        "typical_customer", "smb_objections", "sales_cycle", "customer_acquisition_channels",
        "retention_strategy", "expansion_triggers", "enterprise_readiness_checklist",
        "regulatory_considerations", "technical_stack_expectations", "typical_differentiation",
        "common_feature_roadmap",
    )
    for field in expanded_fields:
        assert field in _REQUIRED_FIELDS
    for category in supported_categories():
        pack = _PACKS[category]
        for field in expanded_fields:
            assert pack.get(field), f"{category} missing non-empty {field}"
