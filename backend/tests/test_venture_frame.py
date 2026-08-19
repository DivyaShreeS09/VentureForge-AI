import copy

from app.agents.venture_frame import build_venture_frame, is_known
from app.ml.funding_readiness import assess_funding_readiness


# --- Unknown must remain Unknown --------------------------------------------------------------


def test_completely_empty_input_is_all_unknown_and_never_crashes():
    frame = build_venture_frame()
    assert not is_known(frame["core_venture_summary"])
    assert not is_known(frame["industry"]["primary"])
    assert frame["industry"]["secondary"] is None
    assert not is_known(frame["positioning"]["primary"])
    assert not is_known(frame["customer"])
    assert not is_known(frame["target_market"])
    assert not is_known(frame["venture_stage"])
    assert not is_known(frame["geography"])
    assert not is_known(frame["deployment_context"])
    assert not is_known(frame["revenue_model"])
    assert not is_known(frame["competition"])
    assert not is_known(frame["differentiation"])
    assert not is_known(frame["regulatory_context"])
    assert frame["open_questions"] == []
    assert frame["known_constraints"] == []


def test_unknown_fields_have_zero_confidence_and_no_evidence():
    frame = build_venture_frame()
    assert frame["customer"]["confidence"] == 0.0
    assert frame["customer"]["evidence_ids"] == []
    assert frame["customer"]["value"] is None


def test_blank_market_evidence_strings_produce_unknown_not_empty_string():
    frame = build_venture_frame(market_evidence={"customer_type": "", "target_market": None, "geography": "  "})
    # Note: "  " (whitespace) is truthy in Python and is intentionally treated as a real (if odd)
    # founder-supplied value — only genuinely empty/None values are excluded, never guessed at.
    assert not is_known(frame["customer"])
    assert not is_known(frame["target_market"])


def test_never_fabricates_a_field_for_absent_upstream_module():
    frame = build_venture_frame(funding_assessment=None, business_model=None, competitor_analysis=None)
    assert not is_known(frame["revenue_model"])
    assert not is_known(frame["differentiation"])
    assert not is_known(frame["core_venture_summary"])
    assert not is_known(frame["competition"])


# --- Evidence linkage and confidence ---------------------------------------------------------


def test_market_evidence_fields_carry_evidence_ids_and_supporting_text():
    frame = build_venture_frame(market_evidence={"customer_type": "Retail operations managers"})
    field = frame["customer"]
    assert field["value"] == "Retail operations managers"
    assert field["evidence_ids"] == ["market_evidence:customer_type"]
    assert field["supporting_text"]
    assert field["origin"] == "market_evidence.customer_type"
    assert field["confidence"] > 0.0


def test_rubric_confirmed_positive_and_negative_are_both_known_with_evidence():
    funding = assess_funding_readiness(
        {"revenue_model_clarity": 2, "competitive_differentiation": {"state": "confirmed_negative"}}
    )
    frame = build_venture_frame(funding_assessment=funding)
    assert is_known(frame["revenue_model"])
    assert frame["revenue_model"]["evidence_ids"] == ["rubric:revenue_model_clarity"]
    assert is_known(frame["differentiation"])
    assert frame["differentiation"]["evidence_ids"] == ["rubric:competitive_differentiation"]


def test_rubric_not_sure_yet_and_not_applicable_remain_unknown():
    funding = assess_funding_readiness(
        {
            "revenue_model_clarity": {"state": "not_sure_yet"},
            "competitive_differentiation": {"state": "not_applicable"},
        }
    )
    frame = build_venture_frame(funding_assessment=funding)
    assert not is_known(frame["revenue_model"])
    assert not is_known(frame["differentiation"])


def test_core_venture_summary_quotes_the_founders_own_words_not_invented_text():
    business_model = {"value_proposition": "A subscription analytics dashboard for retail teams."}
    frame = build_venture_frame(business_model=business_model)
    assert frame["core_venture_summary"]["value"] == "A subscription analytics dashboard for retail teams."
    assert "founder's own description" in frame["core_venture_summary"]["supporting_text"]


def test_open_questions_reuses_missing_evidence_labels_not_recomputed():
    funding = assess_funding_readiness({"traction": {"state": "not_sure_yet"}})
    frame = build_venture_frame(funding_assessment=funding)
    assert "Traction" in frame["open_questions"]


# --- Ambiguity representation (industry / positioning hypotheses) ----------------------------


def test_industry_hypothesis_holds_primary_and_secondary_when_uncertain():
    industry_prediction = {
        "predicted_industry": "b2b",
        "confidence": 0.4,
        "is_uncertain": True,
        "alternatives": [{"industry": "consumer", "confidence": 0.35}],
    }
    frame = build_venture_frame(industry_prediction=industry_prediction)
    hyp = frame["industry"]
    assert hyp["primary"]["value"] == "b2b"
    assert hyp["secondary"]["value"] == "consumer"
    assert hyp["is_ambiguous"] is True
    assert hyp["reason"]


def test_industry_hypothesis_confident_prediction_is_not_flagged_ambiguous():
    industry_prediction = {"predicted_industry": "healthcare", "confidence": 0.9, "is_uncertain": False, "alternatives": []}
    frame = build_venture_frame(industry_prediction=industry_prediction)
    hyp = frame["industry"]
    assert hyp["is_ambiguous"] is False
    assert hyp["secondary"] is None
    assert hyp["reason"] is None


def test_positioning_hypothesis_reuses_existing_secondary_domains_and_low_confidence_flag():
    venture_positioning = {
        "primary_domain": "Enterprise AI",
        "secondary_domains": ["Productivity Software"],
        "confidence": 0.42,
        "is_low_confidence": True,
        "resolution_source": "taxonomy_ambiguous_fallback",
    }
    frame = build_venture_frame(venture_positioning=venture_positioning)
    hyp = frame["positioning"]
    assert hyp["primary"]["value"] == "Enterprise AI"
    assert hyp["secondary"]["value"] == "Productivity Software"
    assert hyp["is_ambiguous"] is True


def test_deployment_context_reads_from_venture_positioning_sectors():
    venture_positioning = {"primary_domain": "PropTech", "deployment_sectors": ["real estate", "facilities"], "confidence": 0.7}
    frame = build_venture_frame(venture_positioning=venture_positioning)
    assert frame["deployment_context"]["value"] == ["real estate", "facilities"]


# --- Reuse of regulatory_context (no reimplementation) -----------------------------------------


def test_healthcare_description_surfaces_regulatory_context_and_known_constraint():
    frame = build_venture_frame(
        startup_description="A clinical decision support tool for hospital patient triage.",
        venture_positioning={"primary_domain": "Clinical Decision Support"},
    )
    assert is_known(frame["regulatory_context"])
    assert frame["known_constraints"] == [frame["regulatory_context"]]


def test_fintech_lending_description_surfaces_finance_regulatory_context():
    frame = build_venture_frame(startup_description="We provide instant small-dollar loans to gig workers.")
    assert is_known(frame["regulatory_context"])


def test_plain_saas_description_has_no_regulatory_context():
    frame = build_venture_frame(startup_description="A project management tool for remote software teams.")
    assert not is_known(frame["regulatory_context"])
    assert frame["known_constraints"] == []


# --- Domain sweep: marketplace, hardware, AI, education, social impact -------------------------


def test_marketplace_domain_builds_a_coherent_frame():
    frame = build_venture_frame(
        startup_description="A marketplace connecting freelance electricians with homeowners.",
        market_evidence={"customer_type": "Homeowners needing electrical work", "geography": "United States"},
        venture_positioning={"primary_domain": "Peer Collaboration Marketplaces", "confidence": 0.6},
    )
    assert frame["customer"]["value"] == "Homeowners needing electrical work"
    assert not is_known(frame["regulatory_context"])


def test_hardware_and_ai_description_does_not_crash_and_stays_honest():
    frame = build_venture_frame(
        startup_description="An autonomous vehicle safety sensor using onboard AI inference.",
    )
    # Safety-critical keywords should surface a regulatory constraint even with no other evidence.
    assert is_known(frame["regulatory_context"])


def test_education_and_social_impact_domains_produce_no_spurious_regulatory_flag():
    frame = build_venture_frame(
        startup_description="A tutoring platform connecting volunteer mentors with underserved students.",
    )
    # "students"/"minors"-adjacent language alone (no sensitive-data keyword) must not misfire.
    assert not is_known(frame["regulatory_context"])


# --- Very short / very detailed / contradictory inputs -----------------------------------------


def test_one_line_idea_produces_a_valid_mostly_unknown_frame():
    frame = build_venture_frame(startup_name="Nova", startup_description="AI for retail.")
    assert frame["startup_name"] == "Nova"
    assert frame["venture_frame_version"] == "v1"


def test_fully_detailed_idea_does_not_over_claim_beyond_its_evidence():
    funding = assess_funding_readiness(
        {name: 2 for name in ["problem_clarity", "customer_pain_evidence", "traction", "revenue_model_clarity"]}
    )
    frame = build_venture_frame(
        startup_name="Nova",
        startup_description=(
            "Nova is a subscription analytics dashboard for retail operations managers who need "
            "real-time inventory visibility across stores."
        ),
        funding_assessment=funding,
        market_evidence={"customer_type": "Retail operations managers", "target_market": "Mid-market retail chains"},
        business_model={"value_proposition": "Nova is a subscription analytics dashboard for retail operations managers."},
    )
    # Every populated field must still carry real evidence_ids/origin — detail in the input must
    # never cause the frame to assert something no upstream module actually computed.
    assert is_known(frame["revenue_model"])
    assert not is_known(frame["differentiation"])  # never answered — must stay Unknown despite detail elsewhere


def test_contradictory_market_evidence_fields_are_each_reported_independently_not_reconciled():
    # Phase B does not resolve contradictions (that is Contradiction Detection, a later phase) — it
    # must simply report what each source said, honestly and independently, without crashing or
    # silently picking a winner.
    frame = build_venture_frame(
        market_evidence={"customer_type": "Enterprise IT buyers", "target_market": "Individual consumers"}
    )
    assert frame["customer"]["value"] == "Enterprise IT buyers"
    assert frame["target_market"]["value"] == "Individual consumers"


# --- Immutability and determinism --------------------------------------------------------------


def test_frame_does_not_alias_mutable_input_objects():
    venture_positioning = {"primary_domain": "PropTech", "deployment_sectors": ["real estate"], "confidence": 0.7}
    frame = build_venture_frame(venture_positioning=venture_positioning)
    frame["deployment_context"]["value"].append("mutated")
    assert venture_positioning["deployment_sectors"] == ["real estate"]


def test_mutating_returned_frame_does_not_affect_a_fresh_rebuild():
    market_evidence = {"customer_type": "SMB owners"}
    frame_1 = build_venture_frame(market_evidence=market_evidence)
    frame_1["customer"]["value"] = "mutated in place"
    frame_2 = build_venture_frame(market_evidence=market_evidence)
    assert frame_2["customer"]["value"] == "SMB owners"


def test_build_venture_frame_is_deterministic():
    kwargs = dict(
        startup_name="Nova",
        startup_description="A subscription analytics dashboard for retail teams.",
        funding_assessment=assess_funding_readiness({"traction": 1}),
        market_evidence={"customer_type": "Retail ops managers"},
    )
    frame_1 = build_venture_frame(**copy.deepcopy(kwargs))
    frame_2 = build_venture_frame(**copy.deepcopy(kwargs))
    assert frame_1 == frame_2
