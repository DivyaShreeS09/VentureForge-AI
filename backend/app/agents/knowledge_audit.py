"""Knowledge Audit (Startup Domain Intelligence Sprint, Phase 1).

Answers "where did this knowledge come from?" for every founder-facing recommendation — reuses
app.agents.consistency_audit's tree-walker (`_collect_tagged_items`) rather than re-implementing a
second traversal, and classifies each tagged item's TOP-LEVEL section by this pipeline's own known,
fixed architecture (which module built it and what it draws on) — not a per-run guess. Five source
categories, distinct from the five evidentiary tags (evidence/inference/ai_recommendation/
market_assumption/experiment_suggestion) already on every item — this audits WHERE knowledge came
from, not what epistemic status it claims:

- retrieved_evidence: real, retrieved similar ventures (app.ml.venture_retrieval) or their
  comparative intelligence — the only category backed by real historical company data.
- deterministic_reasoning: computed from this venture's own submitted evidence
  (funding-readiness rubric, venture_signals, capability_library) — real, but about THIS venture's
  inputs, not other companies.
- ai_reasoning: Gemini-authored narrative (app.agents.mentor_reviewer) — NOT part of
  founder_report today (see finding below), reported honestly as 0% rather than assumed present.
- startup_knowledge: general, category-level startup-domain knowledge
  (app.agents.industry_knowledge_packs and the category-template scaffolds in
  pricing_intelligence/go_to_market_intelligence/feature_intelligence) — real domain knowledge, but
  general to the category, not specific to this venture or backed by retrieved data.
- unsupported_generic_advice: anything that doesn't trace to one of the above — the target is 0%,
  and this audit exists specifically to catch anything that ever isn't.
"""

from __future__ import annotations

from app.agents.consistency_audit import _collect_tagged_items
from app.agents.industry_knowledge_packs import supported_categories
from app.agents.venture_vocabulary import all_resolvable_categories

KNOWLEDGE_AUDIT_VERSION = "v2"

# Fixed map of this pipeline's own architecture: which top-level founder_report section each path
# starts with, and which of the 5 source categories it belongs to. Built from this codebase's own
# module docstrings/source_attribution — not inferred at audit time.
#
# Founder Consulting Experience Sprint: app.agents.founder_report was rebuilt around a 10-section
# consulting narrative (executive_verdict ... success_path) with almost all of the PREVIOUS section
# set preserved verbatim one level deeper, under `appendix`. Both the new top-level section names
# and the `appendix.*` paths are mapped below; the old un-prefixed names (`founder_report.
# problem_analysis`, etc.) are kept too — real report paths no longer produce them (they're all
# under `appendix` now), but a handful of this module's own unit tests still construct small,
# synthetic old-shaped dicts directly to test the classifier in isolation, and there's no reason to
# make those less readable for a real behavior change that doesn't need it.
_SECTION_SOURCE: dict[str, str] = {
    "founder_report.executive_verdict": "deterministic_reasoning",
    "founder_report.what_we_learned": "deterministic_reasoning",
    "founder_report.three_biggest_problems": "deterministic_reasoning",
    "founder_report.three_biggest_advantages": "deterministic_reasoning",
    "founder_report.investor_view": "deterministic_reasoning",
    "founder_report.founder_strategy": "deterministic_reasoning",
    "founder_report.moat_and_competitive_position": "deterministic_reasoning",
    "founder_report.market_insight": "startup_knowledge",
    "founder_report.success_path": "deterministic_reasoning",
    "founder_report.executive_summary": "deterministic_reasoning",
    "founder_report.startup_snapshot": "deterministic_reasoning",
    "founder_report.problem_analysis": "deterministic_reasoning",
    "founder_report.customer_analysis": "deterministic_reasoning",
    "founder_report.business_model": "deterministic_reasoning",
    "founder_report.market_position": "deterministic_reasoning",
    "founder_report.pricing_strategy": "deterministic_reasoning",
    "founder_report.go_to_market_strategy": "deterministic_reasoning",
    "founder_report.competitive_landscape.summary": "deterministic_reasoning",
    "founder_report.competitive_landscape.likely_alternatives": "startup_knowledge",
    "founder_report.competitive_landscape.switching_behavior": "startup_knowledge",
    "founder_report.competitive_landscape.switching_friction": "startup_knowledge",
    "founder_report.competitive_landscape.how_to_win": "deterministic_reasoning",
    "founder_report.competitive_landscape.similar_historical_ventures": "retrieved_evidence",
    "founder_report.competitive_landscape.comparative_pattern_summary": "retrieved_evidence",
    "founder_report.competitive_landscape.venture_space_analysis": "retrieved_evidence",
    "founder_report.product_roadmap": "deterministic_reasoning",
    "founder_report.critical_blind_spots": "deterministic_reasoning",
    "founder_report.investor_questions": "deterministic_reasoning",
    "founder_report.founder_challenge_mode": "deterministic_reasoning",
    "founder_report.moat_intelligence": "deterministic_reasoning",
    "founder_report.feature_gap_vs_market": "retrieved_evidence",
    "founder_report.ai_feature_suggestions": "startup_knowledge",
    "founder_report.risk_assessment": "deterministic_reasoning",
    "founder_report.opportunity_assessment": "deterministic_reasoning",
    "founder_report.funding_readiness": "deterministic_reasoning",
    "founder_report.historical_pattern_signal": "deterministic_reasoning",
    "founder_report.funding_stage_ladder": "deterministic_reasoning",
    "founder_report.founder_iq_report": "deterministic_reasoning",
    "founder_report.pilot_roadmap": "deterministic_reasoning",
    "founder_report.startup_benchmark": "startup_knowledge",
    "founder_report.investor_intelligence": "startup_knowledge",
    "founder_report.industry_context": "startup_knowledge",
    "founder_report.ninety_day_action_plan": "deterministic_reasoning",
    "founder_report.evidence_supporting_strengths": "deterministic_reasoning",
    "founder_report.final_mentor_verdict": "deterministic_reasoning",
}

# Same section map, nested one level under `appendix` — every real founder_report run has its
# detailed sections here now, not at the top level.
_SECTION_SOURCE.update({f"founder_report.appendix.{key.removeprefix('founder_report.')}": value for key, value in list(_SECTION_SOURCE.items())})


def _classify_path(path: str, item: dict) -> str:
    # `founder_report.startup_benchmark.industry_positioning` is the one path whose actual source
    # varies per-run (real retrieved evidence when retrieval is enabled and found neighbors,
    # general knowledge otherwise) — app.agents.founder_report already tags it "evidence" only in
    # the retrieved case, so that real per-run tag is authoritative here rather than a static guess.
    if path in ("founder_report.startup_benchmark.industry_positioning", "founder_report.appendix.startup_benchmark.industry_positioning"):
        return "retrieved_evidence" if item.get("category") == "evidence" else "startup_knowledge"
    # Longest-prefix match against the fixed section map above.
    best_match = None
    for prefix in _SECTION_SOURCE:
        if path == prefix or path.startswith(prefix + ".") or path.startswith(prefix + "["):
            if best_match is None or len(prefix) > len(best_match):
                best_match = prefix
    return _SECTION_SOURCE.get(best_match, "unsupported_generic_advice") if best_match else "unsupported_generic_advice"


def audit_category_coverage() -> dict:
    """Master Startup Knowledge Base Sprint, Phase 7 ('category coverage'). Reports how many of the
    categories app.agents.venture_vocabulary.resolve_category can actually produce have a dedicated
    (non-generic) app.agents.industry_knowledge_packs pack, vs. falling back to the generic pack —
    a real, computed number, not an estimate."""
    all_categories = all_resolvable_categories()
    covered = supported_categories()
    missing = sorted(c for c in all_categories if c not in covered and c != "generic")
    denominator = len(all_categories) - 1 or 1  # "generic" itself is a fallback, not a coverage target
    return {
        "categories_resolvable_by_taxonomy": len(all_categories),
        "categories_with_dedicated_knowledge_pack": len(covered),
        "coverage_percentage": round(len(covered) / denominator * 100, 1),
        "categories_missing_a_dedicated_pack": missing,
    }


def audit_knowledge_sources(founder_report: dict, consistency_audit_result: dict | None = None) -> dict:
    """Walks the assembled founder_report and classifies every tagged item's knowledge source.
    Returns real counts/percentages — never a guessed or rounded-for-effect number.

    `consistency_audit_result` is optional and, when passed, reuses
    app.agents.consistency_audit.audit_founder_report's ALREADY-COMPUTED generic-boilerplate hits
    (rather than re-scanning the report a second time) to report a genuine
    generic_advice_percentage for Phase 7's knowledge-quality measures, alongside the
    knowledge-source counts this function already computed. Backward compatible: omitting it just
    means that one figure is reported as unavailable rather than silently guessed."""
    tagged_items: list[tuple[str, dict]] = []
    _collect_tagged_items(founder_report, "founder_report", tagged_items)

    counts: dict[str, int] = {
        "retrieved_evidence": 0,
        "deterministic_reasoning": 0,
        "ai_reasoning": 0,
        "startup_knowledge": 0,
        "unsupported_generic_advice": 0,
    }
    unclassified_paths: list[str] = []
    for path, item in tagged_items:
        source = _classify_path(path, item)
        counts[source] += 1
        if source == "unsupported_generic_advice":
            unclassified_paths.append(path)

    total = len(tagged_items) or 1
    percentages = {k: round(v / total * 100, 1) for k, v in counts.items()}

    if consistency_audit_result is not None:
        generic_hits = len(consistency_audit_result.get("generic_boilerplate_hits", []))
        generic_advice_percentage = round(generic_hits / total * 100, 1)
    else:
        generic_advice_percentage = None

    return {
        "knowledge_audit_version": KNOWLEDGE_AUDIT_VERSION,
        "n_items_audited": len(tagged_items),
        "counts": counts,
        "percentages": percentages,
        "unclassified_paths": unclassified_paths,
        "category_coverage": audit_category_coverage(),
        # Phase 7's "knowledge quality" measures, reusing the counts/percentages already computed
        # above rather than a second, separate computation — the terms Phase 7 asks for map
        # directly onto this audit's existing 5-way source classification:
        "knowledge_backed_advice_percentage": percentages["startup_knowledge"],
        "retrieved_evidence_coverage_percentage": percentages["retrieved_evidence"],
        "unsupported_advice_percentage": percentages["unsupported_generic_advice"],
        "generic_advice_percentage": generic_advice_percentage,
        # Phase 1's "category-level vs venture-level" audit, reframed from the same counts:
        # deterministic_reasoning is computed from THIS venture's own submitted evidence
        # (venture-level); startup_knowledge is category-level reference data; retrieved_evidence
        # is venture-comparative (real other ventures, more specific than a category but not this
        # venture itself).
        "venture_level_percentage": percentages["deterministic_reasoning"],
        "category_level_percentage": percentages["startup_knowledge"],
        "venture_comparative_percentage": percentages["retrieved_evidence"],
        "finding_ai_reasoning_is_zero_percent": (
            "founder_report is composed entirely from the deterministic mentor backbone (see "
            "app.agents.founder_report's own docstring: 'adds no new facts, only presentation') — "
            "app.agents.mentor_reviewer's optional Gemini narrative layer sits alongside "
            "mentor_result, not inside founder_report, so 0% of the founder report's own tagged "
            "content is AI-authored today. Reported honestly rather than assumed otherwise."
        ),
        "method": (
            "Every tagged item's dict-path is matched against a fixed map of this pipeline's own "
            "known architecture (which module built each top-level section and what it draws on) — "
            "not a per-run guess or keyword heuristic. Any path not matching a known section is "
            "counted as unsupported_generic_advice and listed in unclassified_paths for review. "
            "Category coverage counts how many resolvable categories have a dedicated knowledge "
            "pack vs. the generic fallback. generic_advice_percentage reuses "
            "app.agents.consistency_audit's own generic-boilerplate-phrase count when supplied, "
            "rather than re-implementing phrase detection here."
        ),
    }
