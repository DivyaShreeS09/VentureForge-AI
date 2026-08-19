"""Golden-case regression tests (Phase 0.75, brought forward as part of Phase 0.5 per the
approved architecture plan). Runs the real HTTP API -> real orchestrator pipeline -> real trained
industry classifier -> real deterministic taxonomy/Judge resolution for 5 fixed cases and checks
structural/semantic invariants — never exact generated prose, since Gemini's phrasing (when
configured) legitimately varies run to run and no live API key is required or used here (Gemini is
never invoked in CI; see app.agents.positioning_reviewer, which returns None whenever
GEMINI_API_KEY is unset — exactly the deterministic-fallback path these assertions exercise).

These fixtures graduated unchanged from the Phase -1 prototype
(ml/prototypes/mentor_prototype/cases/*.json) — same inputs, now exercised through real
production code instead of the isolated prototype module tree.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.agents.competitor_agent import generate_competitor_analysis  # noqa: E402
from app.ai.schemas import GeminiCompetitorPossibilities, _looks_like_named_company  # noqa: E402
from app.ml import predictor  # noqa: E402
from conftest import wait_for_terminal_analysis  # noqa: E402

_CASES_DIR = Path(__file__).resolve().parent / "golden_cases"


@pytest.fixture(autouse=True)
def _skip_if_untrained():
    if not predictor.is_loaded():
        pytest.skip("industry_classifier artifact not trained — run ml/src/training first")


def _run_case(client, case_name: str) -> dict:
    fixture = json.loads((_CASES_DIR / f"{case_name}.json").read_text())
    create_response = client.post(
        "/api/v1/startups",
        json={
            "name": fixture["name"],
            "description": fixture["description"],
            "funding_answers": fixture["funding_answers"],
        },
    )
    assert create_response.status_code == 201
    startup = create_response.json()

    analyze_response = client.post(f"/api/v1/startups/{startup['id']}/analyze")
    assert analyze_response.status_code == 201
    # `/analyze` returns immediately with RUNNING (Act IV, The Forging) — wait for the real
    # background orchestrator run to reach a terminal status before asserting on its output.
    analysis = wait_for_terminal_analysis(client, analyze_response.json()["id"])
    assert analysis["status"] == "COMPLETED"
    return analysis


def _no_not_sure_yet_dimension_is_a_weakness(analysis: dict) -> bool:
    """Structural check that holds regardless of exact wording: every weakness label must trace
    back to a `confirmed_negative` breakdown item, never a `not_sure_yet` one."""
    breakdown = analysis["funding_assessment"]["breakdown"]
    not_sure_yet_labels = {b["label"] for b in breakdown if b["state"] == "not_sure_yet"}
    weaknesses = analysis["judge_summary"]["weaknesses"]
    return not any(any(label in w for label in not_sure_yet_labels) for w in weaknesses)


def test_campus_resolves_to_smart_facilities_technology(client):
    analysis = _run_case(client, "campus")
    judge = analysis["judge_summary"]

    # model_category remains the real trained classifier output — never asserted to a specific
    # hardcoded label, since the artifact trained in this environment may differ from production.
    assert judge["model_category"] is not None
    assert judge["model_category"]["label"] == analysis["industry_prediction"]["predicted_industry"]

    vp = judge["venture_positioning"]
    assert vp["primary_domain"] == "Smart Facilities Technology"
    assert {"Campuses", "Hotels"}.issubset(set(vp["deployment_sectors"]))
    assert _no_not_sure_yet_dimension_is_a_weakness(analysis)

    # Phase A: revenue scenario always available, every field carrying real provenance.
    revenue_estimate = analysis["revenue_estimate"]
    assert revenue_estimate["available"] is True
    assert revenue_estimate["scenarios"] is not None
    for field in revenue_estimate["assumptions"].values():
        assert field["assumption_source"] in ("user_supplied", "suggested_default")

    # Phase B: all five competitor buckets present and serializable.
    competitor_analysis = analysis["competitor_analysis"]
    for bucket in (
        "verified_competitors", "unverified_possibilities", "indirect_alternatives",
        "manual_process_alternative", "do_nothing_alternative",
    ):
        assert bucket in competitor_analysis

    # Full Mentor Orchestration phase: identifies facilities managers, prioritizes pilot-access
    # validation, recommends only relevant capabilities, MVP begins with one property/building and
    # limited utilities, roadmap validates before expansion.
    mentor = analysis["mentor_interpretation"]
    assert mentor is not None
    assert "facilities manager" in mentor["idea_understanding"]["target_user"].lower()
    mvp = mentor["mvp_recommendation"]
    assert "building" in mvp["minimum_workflow"].lower() or "site" in mvp["minimum_workflow"].lower()
    # No prerequisite-blocked capability is ever recommended or included in the MVP.
    premature_ids = {c["id"] for c in mentor["feature_gap_analysis"]["premature_capabilities"]}
    assert premature_ids.isdisjoint(set(mvp["included_capabilities"]))
    assert mentor["roadmap_30_60_90"][0]["focus"].lower().startswith("discovery")


def test_diabetic_foot_prefers_a_specific_health_domain_over_enterprise_ai(client):
    analysis = _run_case(client, "diabetic_foot")
    judge = analysis["judge_summary"]

    # The raw model_category may legitimately remain a coarse/uncertain label (e.g. b2b) — that's
    # exactly the gap venture_positioning exists to close, not a bug to assert away.
    vp = judge["venture_positioning"]
    health_domains = {"HealthTech Diagnostics", "Clinical Decision Support"}
    assert vp["primary_domain"] in health_domains, "must prefer a specific health domain over Enterprise AI"
    assert vp["primary_domain"] != "Enterprise AI"
    all_positioning_domains = {vp["primary_domain"], *vp["secondary_domains"]}
    assert health_domains & all_positioning_domains == health_domains or len(health_domains & all_positioning_domains) >= 1
    # Low confidence must remain visible, not hidden, given how thin the taxonomy signal is here.
    assert vp["is_low_confidence"] is True

    # No invented named competitor — nothing was founder-supplied for this fixture, so
    # verified_competitors must be empty and unverified_possibilities (if populated by Gemini,
    # which is never invoked in CI without an API key) must never contain a proper-noun brand.
    competitor_analysis = analysis["competitor_analysis"]
    assert competitor_analysis["verified_competitors"] == []
    assert competitor_analysis["unverified_possibilities"] == []

    # Full Mentor Orchestration phase: prioritizes regulatory/clinical validation, never claims
    # diagnosis approval or invents clinical evidence, and recommends a narrow, clinician-reviewed
    # MVP rather than an autonomous-diagnosis one.
    mentor = analysis["mentor_interpretation"]
    assert mentor is not None
    validation_gaps = {a["source_gap"] for a in mentor["validation_plan"]}
    assert "regulatory_documentation" in validation_gaps or "autonomous_diagnosis" in validation_gaps
    mvp = mentor["mvp_recommendation"]
    assert "autonomous_diagnosis" not in mvp["included_capabilities"]
    assert "autonomous_diagnosis" in mentor["feature_gap_analysis"]["premature_capabilities"][0]["id"] or any(
        c["id"] == "autonomous_diagnosis" for c in mentor["feature_gap_analysis"]["premature_capabilities"]
    )
    for text in (mvp["single_core_problem"], mvp["minimum_workflow"], mentor["venture_positioning"]):
        assert "approved" not in text.lower() and "fda" not in text.lower()


def test_restaurant_resolves_to_a_restaurant_operations_domain(client):
    analysis = _run_case(client, "restaurant")
    judge = analysis["judge_summary"]

    vp = judge["venture_positioning"]
    assert vp["primary_domain"] in {"Restaurant Operations Technology", "Food-Cost Management"}
    assert "Restaurants" in vp["deployment_sectors"]

    # No false competitor facts: every competitor entry must be either user-supplied (none were,
    # for this fixture) or explicitly flagged as unverified — never asserted as a real, verified
    # company the founder never named.
    competitor_analysis = analysis["competitor_analysis"]
    assert competitor_analysis["verified_competitors"] == []
    for entry in competitor_analysis["entries"]:
        assert entry["evidence_source"] != "verified" or entry["competitor_or_alternative"] == ""
    # Manual process alternative present, deterministic regardless of Gemini availability.
    assert competitor_analysis["manual_process_alternative"]["description"]

    # Phase A: revenue scenario always available, using suggested defaults since this fixture
    # supplies no revenue_assumptions at all.
    revenue_estimate = analysis["revenue_estimate"]
    assert revenue_estimate["available"] is True
    assert set(revenue_estimate["missing_assumptions"]) == {
        "price_per_customer_usd", "initial_customers", "monthly_growth_rate_pct", "gross_margin_pct",
    }
    for field in revenue_estimate["assumptions"].values():
        assert field["assumption_source"] == "suggested_default"

    # Full Mentor Orchestration phase: prioritizes one manual-entry pilot before POS integration,
    # revenue assumptions remain suggested, spreadsheets/manual counting identified as alternatives.
    mentor = analysis["mentor_interpretation"]
    assert mentor is not None
    present_ids = {c["id"] for c in mentor["feature_gap_analysis"]["present_capabilities"]}
    assert {"manual_inventory_logging", "waste_tracking"}.issubset(present_ids)
    # pos_integration (POS integration) must never be scoped into the MVP ahead of the
    # already-present manual-entry/waste-tracking capabilities.
    assert "pos_integration" not in mentor["mvp_recommendation"]["included_capabilities"]
    assert "spreadsheet" in mentor["competitor_landscape"].lower() or "manual" in mentor["competitor_landscape"].lower()
    assert mentor["evidence_and_uncertainty"]["user_supplied_vs_suggested_summary"]


def test_marketplace_positioning_supported_by_evidence(client):
    analysis = _run_case(client, "marketplace")
    judge = analysis["judge_summary"]

    vp = judge["venture_positioning"]
    assert vp["primary_domain"] in {"Peer Collaboration Marketplaces", "Campus & Student Services", "EdTech"}

    # Disagreement between signals (raw model_category vs. the resolved taxonomy positioning, or
    # taxonomy vs. Gemini) must be visible, never silently discarded, whenever the taxonomy signal
    # itself was ambiguous enough to be flagged low-confidence.
    if vp["is_low_confidence"]:
        assert judge["positioning_correction_rationale"]

    # A free/freemium or organizer-tier revenue scenario appears only as a suggested default, not
    # a fact — this fixture supplies no revenue_assumptions, so every field must be labeled as
    # such (never silently presented as a researched number).
    revenue_estimate = analysis["revenue_estimate"]
    assert revenue_estimate["available"] is True
    for field in revenue_estimate["assumptions"].values():
        assert field["assumption_source"] == "suggested_default"
        assert field["editable"] is True

    # Full Mentor Orchestration phase: prioritizes a one-campus/one-event liquidity test, never
    # recommends payments before matching value is validated.
    mentor = analysis["mentor_interpretation"]
    assert mentor is not None
    mvp = mentor["mvp_recommendation"]
    assert "payments_and_monetization" not in mvp["included_capabilities"]
    premature_ids = {c["id"] for c in mentor["feature_gap_analysis"]["premature_capabilities"]}
    recommended_ids = {c["id"] for c in mentor["feature_gap_analysis"]["recommended_capabilities"]}
    assert "payments_and_monetization" not in recommended_ids or "payments_and_monetization" in premature_ids


def test_vague_case_stays_honest_about_low_confidence(client):
    analysis = _run_case(client, "vague")
    judge = analysis["judge_summary"]

    vp = judge["venture_positioning"]
    assert vp["is_low_confidence"] is True
    # No fabricated strengths: nothing in this fixture was confirmed_positive with severity 2.
    assert judge["strengths"] == []
    # No fabricated *funding-evidence* weakness: nothing in this fixture was confirmed_negative,
    # so none of the 8 rubric dimensions may appear as a weakness. (A separate, honestly-sourced
    # weakness from the success predictor being genuinely uncertain on this thin an input is
    # expected and is not what this assertion is checking — see
    # _no_not_sure_yet_dimension_is_a_weakness for the funding-specific check.)
    assert _no_not_sure_yet_dimension_is_a_weakness(analysis)
    funding_labels = {b["label"] for b in analysis["funding_assessment"]["breakdown"]}
    assert not any(any(label in w for label in funding_labels) for w in judge["weaknesses"])
    # Every dimension was left "not_sure_yet" -> every one must produce a structured hypothesis,
    # never a bare gap message.
    assert len(judge["suggested_possibilities"]) == 8
    for hypothesis in judge["suggested_possibilities"]:
        assert hypothesis["starting_hypothesis"]
        assert hypothesis["validation_task"]

    # Generic/discovery-stage revenue scenario, clearly labeled — no domain or model-category
    # default applies to this deliberately vague description.
    revenue_estimate = analysis["revenue_estimate"]
    assert revenue_estimate["available"] is True
    assert revenue_estimate["default_basis"] in (
        "generic_discovery_stage_default", "model_category_default", "domain_default",
    )
    if revenue_estimate["default_basis"] == "generic_discovery_stage_default":
        assert "discovery-stage" in revenue_estimate["assumptions"]["price_per_customer_usd"]["explanation"]

    # No invented competitor names for this fixture either.
    competitor_analysis = analysis["competitor_analysis"]
    assert competitor_analysis["verified_competitors"] == []

    # Full Mentor Orchestration phase: no fabricated strengths, no confirmed weaknesses unless
    # supplied, no premature MVP, roadmap begins with discovery, feature recommendations minimal.
    mentor = analysis["mentor_interpretation"]
    assert mentor is not None
    assert mentor["strengths"] == []
    # No *funding-rubric-derived* weakness (every dimension here was left not_sure_yet, never
    # confirmed_negative) — a genuinely-observed model-uncertainty note (unrelated to the rubric)
    # may still legitimately appear, exactly as it does in judge_summary.weaknesses upstream.
    funding_labels = {b["label"] for b in analysis["funding_assessment"]["breakdown"]}
    assert not any(any(label in w for label in funding_labels) for w in mentor["real_weaknesses"])
    assert mentor["mvp_recommendation"]["included_capabilities"] == []
    assert mentor["roadmap_30_60_90"][0]["focus"].lower().startswith("discovery")
    assert len(mentor["feature_gap_analysis"]["recommended_capabilities"]) <= 1


# --- Production-hardening phase: cross-cutting regression checks --------------------------------

_ALL_GOLDEN_CASE_NAMES = ["campus", "diabetic_foot", "restaurant", "marketplace", "vague"]


def test_taxonomy_endpoint_exposes_every_domain_the_golden_cases_actually_resolve_to(client):
    """Confirms GET /api/v1/taxonomy is a genuinely live source of truth: every
    `venture_positioning.primary_domain` any golden case resolves to in this real pipeline run must
    be present in the taxonomy endpoint's domain list — proving the endpoint isn't a stale or
    partial copy of the taxonomy actually used for resolution."""
    resolved_domains = set()
    for case_name in _ALL_GOLDEN_CASE_NAMES:
        analysis = _run_case(client, case_name)
        resolved_domains.add(analysis["judge_summary"]["venture_positioning"]["primary_domain"])

    taxonomy_response = client.get("/api/v1/taxonomy")
    assert taxonomy_response.status_code == 200
    taxonomy_domain_ids = {d["id"] for d in taxonomy_response.json()["domains"]}

    assert resolved_domains.issubset(taxonomy_domain_ids)


def test_persisted_revenue_edit_survives_reload_and_never_touches_model_category(client):
    """Applies a real revenue-assumption edit (PATCH) and a real positioning correction (POST) to
    the same analysis, then re-fetches it fresh — proving both edits persist across a reload and
    that `model_category` (the raw trained-classifier output) is never altered by either edit,
    exactly as app.services.analysis_service's two update functions guarantee."""
    analysis = _run_case(client, "restaurant")
    original_model_category = analysis["judge_summary"]["model_category"]

    patch_response = client.patch(
        f"/api/v1/analyses/{analysis['id']}/revenue-assumptions",
        json={"price_per_customer_usd": 149.0, "initial_customers": 8},
    )
    assert patch_response.status_code == 200

    correction_response = client.post(
        f"/api/v1/analyses/{analysis['id']}/industry-correction",
        json={"primary_domain": "Food-Cost Management"},
    )
    assert correction_response.status_code == 200

    refetched = client.get(f"/api/v1/analyses/{analysis['id']}").json()
    assumptions = refetched["revenue_estimate"]["assumptions"]
    assert assumptions["price_per_customer_usd"]["value"] == 149.0
    assert assumptions["price_per_customer_usd"]["assumption_source"] == "user_supplied"
    assert assumptions["initial_customers"]["value"] == 8

    assert refetched["judge_summary"]["venture_positioning"]["primary_domain"] == "Food-Cost Management"
    assert refetched["judge_summary"]["model_category"] == original_model_category


def test_invalid_gemini_competitor_items_never_appear_in_any_golden_case(client):
    """Gemini is never invoked in CI (no GEMINI_API_KEY configured — see module docstring), so
    every golden case's `unverified_possibilities` bucket is empty by construction. This directly
    exercises the same hardened schema the live pipeline would use if Gemini *were* configured,
    proving an adversarial mixed valid/invalid response could never leak an invalid item into this
    bucket regardless of whether Gemini happens to be configured in a given environment."""
    for case_name in _ALL_GOLDEN_CASE_NAMES:
        analysis = _run_case(client, case_name)
        assert analysis["competitor_analysis"]["unverified_possibilities"] == []

    adversarial_payload = {
        "possibilities": [
            {"category": "Toast POS", "solution_type": "software_platform", "reason": "x", "source": "ai_suggested_category"},
            {"category": "visit www.example.com", "solution_type": "software_platform", "reason": "x", "source": "ai_suggested_category"},
            {"category": "Acme Inc", "solution_type": "software_platform", "reason": "x", "source": "ai_suggested_category"},
            {"category": "general point-of-sale software", "solution_type": "software_platform", "reason": "A generic adjacent category.", "source": "ai_suggested_category"},
        ]
    }
    validated = GeminiCompetitorPossibilities.model_validate(adversarial_payload)
    surviving_categories = [p.category for p in validated.possibilities]
    assert surviving_categories == ["general point-of-sale software"]
    assert not any(_looks_like_named_company(c) for c in surviving_categories)


def test_valid_category_level_possibility_remains_usable_in_the_competitor_bucket_contract(client):
    """A valid, schema-passing category-level possibility (as Gemini would produce if configured)
    must still flow all the way through generate_competitor_analysis into a real, usable
    `unverified_possibilities` entry — proving the hardened schema doesn't accidentally make every
    Gemini suggestion unusable, only unsafe ones."""
    valid_possibility = {
        "category": "spreadsheet-based inventory tools",
        "solution_type": "manual_process_tool",
        "reason": "Common low-cost alternative for very small restaurants.",
        "source": "ai_suggested_category",
    }
    result = generate_competitor_analysis(
        known_competitors=[],
        industry_prediction={"predicted_industry": "b2b"},
        unverified_possibilities=[valid_possibility],
    )
    assert result["unverified_possibilities"] == [
        {
            "category": "spreadsheet-based inventory tools",
            "solution_type": "manual_process_tool",
            "reason": "Common low-cost alternative for very small restaurants.",
            "evidence_source": "gemini-suggested category (advisory, never a named company)",
            "confidence": "low",
        }
    ]
