"""Founder Report composer (Product Intelligence Sprint, Phase 7; rebuilt for the Founder
Consulting Experience Sprint).

Deterministic, purely additive assembly — invents nothing new. Every value here is already computed
elsewhere (judge_summary, the deterministic mentor sections, pricing/GTM/feature/competitor
intelligence); this module's only job is composing them into ONE consulting engagement, not a
stitched-together stack of independent analyses.

Founder Consulting Experience Sprint — information architecture rebuild. The previous version of
this module rendered ~26 flat, independently-computed sections in sequence; a founder reading start
to finish hit the same underlying facts (a gap dimension, a moat check, a knowledge-pack pattern)
restated three or four times in different voices (a blind spot, then an investor question, then a
challenge-mode objection, then an opportunity-assessment bullet). This rebuild does not add new
reasoning — every fact still traces to the exact same upstream module it always did (see
`_tag`/`source_attribution` in app.agents.mentor_synthesis) — it changes WHICH facts lead the
narrative and how many times each one is allowed to appear there:

  1. executive_verdict      — one screen, no scrolling: the whole engagement in seven lines.
  2. what_we_learned         — "This tells us..." implications, never a restated founder input.
  3. three_biggest_problems  — exactly 3, ranked, from the single founder_guidance_items ordering.
  4. three_biggest_advantages — exactly 3, same ordering, strength/improvement end.
  5. investor_view           — investor_questions + founder_challenge_mode + the relevant
                                critical_blind_spots merged per-dimension into ONE line of
                                reasoning; a dimension already named in #3 is cross-referenced by
                                rank, never restated.
  6. founder_strategy        — the single validation_plan ranking (already merged with roadmap/
                                pilot-roadmap reasoning in app.agents.mentor_synthesis), not three
                                separate roadmap presentations of the same 90 days.
  7. moat_and_competitive_position — what's copyable today / what isn't / what changes at 10, 100,
                                and 1,000 customers, instead of eight near-identical "not yet
                                established" paragraphs.
  8. market_insight          — the curated, already-personalized (venture_signals-driven) sentences
                                from pricing/GTM/competitor/feature intelligence; the full
                                category-level detail moves to the appendix.
  9. success_path            — day-30/90, month-6/12, built ONLY from roadmap_30_60_90 +
                                pilot_roadmap + funding_stage_ladder, never a new projection.
  10. appendix               — everything else: the full previous section set, kept intact for
                                anyone who wants the underlying depth, deliberately never part of
                                the main narrative above.

Every leaf value is still a `{content, category}` tagged claim (or a list of them) exactly as
before, so app.agents.consistency_audit's generic tree-walker needs no changes; only
app.agents.knowledge_audit's fixed section-path map was extended for the new top-level paths (old
paths kept too, since they're still real path names inside `appendix`).
"""

from __future__ import annotations

FOUNDER_REPORT_VERSION = "v2"

_CATEGORIES = ("evidence", "inference", "ai_recommendation", "market_assumption", "experiment_suggestion")

_PROBLEM_CATEGORIES = ("confirmed_risk", "validation_opportunity", "discovery_question")
_ADVANTAGE_CATEGORIES = ("strength", "improvement_opportunity")

_IF_IGNORED_BY_CATEGORY = {
    "confirmed_risk": "This stays an active red flag in every future investor or partner conversation until it's resolved — it doesn't fade with time.",
    "validation_opportunity": "This remains an assumption indefinitely, and every downstream decision — pricing, hiring, roadmap — keeps building on an unconfirmed foundation.",
    "discovery_question": "You'll keep making decisions blind on this until you deliberately go find the answer — it won't resolve itself as the venture grows.",
}


def _tag(content, category: str) -> dict:
    assert category in _CATEGORIES, f"invalid founder-report category: {category!r}"
    return {"content": content, "category": category}


def _format_period_label(period: str) -> str:
    """"days_1_30" -> "Days 1–30". A blind `.replace('_', '–').replace('days', 'Days ')` (the
    previous implementation) turned the underscore between "days" and "1" into a dash too,
    rendering every report as "Days –1–30" — found during the pre-submission audit, reproducible
    in all 10 test reports since every analysis produces this same roadmap field."""
    _, start, end = period.split("_")
    return f"Days {start}–{end}"


def _build_executive_verdict(
    startup_name: str,
    idea_understanding: dict,
    mentor_verdict: dict,
    funding_assessment: dict,
    funding_stage_ladder: dict,
) -> dict:
    stage_line = funding_stage_ladder.get("current_stage") or "unresolved"
    if funding_stage_ladder.get("next_stage"):
        stage_line = f"{stage_line} → {funding_stage_ladder['next_stage']}"
    return {
        "overall_verdict": _tag(mentor_verdict.get("concise_verdict", ""), "inference"),
        "one_sentence_summary": _tag(idea_understanding.get("summary", f"{startup_name}."), "evidence"),
        "biggest_opportunity": _tag(mentor_verdict.get("strongest_signal", ""), "inference"),
        "biggest_risk": _tag(mentor_verdict.get("biggest_risk", ""), "inference"),
        "investor_readiness": _tag(
            f"{funding_assessment.get('level', 'unknown')} ({funding_assessment.get('overall_score', 0):.0f}/100 on the readiness rubric)",
            "evidence",
        ),
        "current_stage": _tag(stage_line, "evidence"),
        "highest_priority_action": _tag(mentor_verdict.get("immediate_priority", ""), "ai_recommendation"),
    }


def _build_what_we_learned(guidance_items: list[dict], excluded_dimensions: set[str]) -> list[dict]:
    """Deliberately NOT the founder's own inputs restated — every bullet is the item's own
    `why_it_matters` (already phrased as an implication, never a fact echo), and deliberately skips
    whatever dimensions already lead #3/#4 below so the same gap never opens two sections in a row."""
    remaining = [item for item in guidance_items if item["dimension"] not in excluded_dimensions]
    learned: list[dict] = []
    seen_reasons: set[str] = set()
    for item in remaining:
        if item["why_it_matters"] in seen_reasons:
            continue
        seen_reasons.add(item["why_it_matters"])
        learned.append(_tag(f"This tells us: {item['why_it_matters']}", "inference"))
        if len(learned) == 5:
            break
    return learned


def _build_three(items: list[dict], role_key: str, action_key: str) -> list[dict]:
    """Shared shape for `three_biggest_problems` (role_key='problem') and
    `three_biggest_advantages` (role_key='advantage') — same six-field structure the sprint asked
    for both to share, populated from the one existing founder_guidance_items ranking."""
    result = []
    for rank, item in enumerate(items[:3], start=1):
        entry = {
            "rank": rank,
            "dimension": item["dimension"],
            role_key: _tag(item["title"], "inference"),
            "evidence": _tag(item["observation"], "evidence"),
            "why_it_matters": _tag(item["why_it_matters"], "inference"),
            action_key: _tag(item["next_step"], "ai_recommendation"),
        }
        result.append(entry)
    return result


def _build_three_biggest_problems(guidance_items: list[dict], blind_spot_reasons: dict[str, str]) -> list[dict]:
    problem_items = [i for i in guidance_items if i["category"] in _PROBLEM_CATEGORIES]
    entries = _build_three(problem_items, "problem", "recommended_fix")
    for entry, item in zip(entries, problem_items[:3]):
        entry["business_consequence"] = _tag(
            blind_spot_reasons.get(
                item["dimension"],
                f"An unresolved '{item['title'].rstrip('.')}' is exactly the kind of gap a serious evaluator "
                "probes for first — it shapes how every other claim in the pitch gets read.",
            ),
            "inference",
        )
        entry["if_ignored"] = _tag(_IF_IGNORED_BY_CATEGORY.get(item["category"], _IF_IGNORED_BY_CATEGORY["validation_opportunity"]), "inference")
    return entries


def _build_three_biggest_advantages(guidance_items: list[dict]) -> list[dict]:
    strengths = [i for i in guidance_items if i["category"] == "strength"]
    # `improvement_opportunity` is shared by two very different underlying states: a genuine partial
    # positive (confirmed_positive, severity 1 — "you have a start here") and a softened-language
    # negative (confirmed_negative on a dimension like team_completeness, coached gently but still a
    # gap, not an advantage). Only the former belongs here as a fallback "advantage" when fewer than
    # 3 real strengths exist — a founder should never see "your team gap" presented as a strength.
    fallback = [i for i in guidance_items if i["category"] == "improvement_opportunity" and i["evidence_state"] == "confirmed_positive"]
    advantage_items = (strengths + fallback)[:3]
    entries = _build_three(advantage_items, "advantage", "how_to_leverage")
    for entry, item in zip(entries, advantage_items):
        entry["business_value"] = _tag(item["why_it_matters"], "inference")
        entry["risk_if_unused"] = _tag(
            "An advantage you don't actively build on tends to erode as competitors catch up — "
            "leveraging it now is what turns a current edge into a lasting one.",
            "inference",
        )
    return entries


def _build_investor_view(
    investor_questions: list[dict],
    founder_challenge_mode: list[dict],
    blind_spots: list[dict],
    problem_rank_by_dimension: dict[str, int],
) -> list[dict]:
    """Merges three previously-separate sections (Investor Questions, Founder Challenge Mode,
    Critical Blind Spots) into ONE per-dimension line of reasoning — each real gap dimension now
    appears here exactly once, joined across all three sources by the `dimension` field each of
    app.agents.founder_intelligence's builders already carries. A dimension already covered in
    `three_biggest_problems` is cross-referenced by rank instead of restating its evidence text."""
    by_question = {q["dimension"]: q for q in investor_questions if q.get("dimension")}
    by_challenge = {c["dimension"]: c for c in founder_challenge_mode if c.get("dimension")}
    by_blind_spot = {b["dimension"]: b for b in blind_spots}

    ordered_dims: list[str] = []
    for source in (investor_questions, founder_challenge_mode):
        for entry in source:
            dim = entry.get("dimension")
            if dim and dim not in ordered_dims:
                ordered_dims.append(dim)

    rows = []
    for dim in ordered_dims:
        q = by_question.get(dim)
        c = by_challenge.get(dim)
        b = by_blind_spot.get(dim)
        grounded_in = (q or c or {}).get("grounded_in", "")
        rank = problem_rank_by_dimension.get(dim)
        evidence_content = f"(Same evidence as Problem #{rank} above.)" if rank else grounded_in
        rows.append(
            {
                "dimension": dim,
                "evidence": _tag(evidence_content, "evidence"),
                "investor_concern": _tag(
                    (b or {}).get("why_investors_care", "This is one of the first things a serious evaluator checks."),
                    "inference",
                ),
                "likely_objection": _tag(c["objection"], "inference") if c else None,
                "how_to_answer": _tag(c["how_to_overcome"], "ai_recommendation") if c else None,
                "investor_question": _tag(f"{q['persona']}: {q['question']}", "inference") if q else None,
            }
        )
    if not rows:
        fallback_q = investor_questions[0] if investor_questions else None
        fallback_c = founder_challenge_mode[0] if founder_challenge_mode else None
        rows.append(
            {
                "dimension": None,
                "evidence": _tag((fallback_q or fallback_c or {}).get("grounded_in", "No open gaps remain."), "evidence"),
                "investor_concern": _tag("Every dimension already has a real answer — execution is the remaining question.", "inference"),
                "likely_objection": _tag(fallback_c["objection"], "inference") if fallback_c else None,
                "how_to_answer": _tag(fallback_c["how_to_overcome"], "ai_recommendation") if fallback_c else None,
                "investor_question": _tag(f"{fallback_q['persona']}: {fallback_q['question']}", "inference") if fallback_q else None,
            }
        )
    return rows


def _build_founder_strategy(validation_plan: list[dict]) -> list[dict]:
    """Replaces three previously-separate presentations of the same execution work (Product
    Roadmap's 3 phases, the 90-Day Action Plan's weekly breakdown, and the Validation Plan) with
    ONE ranked list — every field here already exists on app.agents.mentor_synthesis's enriched
    validation_plan entries (reason/impact/difficulty/estimated_duration/first_step), added
    specifically to support this merge rather than computing a new ranking."""
    return [
        {
            "priority": item["priority"],
            "action": _tag(item["question_to_answer"], "ai_recommendation"),
            "reason": _tag(item["reason"], "inference"),
            "impact": item["impact"],
            "difficulty": item["difficulty"],
            "estimated_duration": item["estimated_duration"],
            "success_metric": _tag(item["success_criterion"], "experiment_suggestion"),
            "first_step": _tag(item["first_step"], "ai_recommendation"),
            "definition_of_done": _tag(item["definition_of_done"], "ai_recommendation"),
        }
        for item in validation_plan
    ]


def _build_moat_and_competitive_position(moat_intelligence: dict) -> dict:
    moats = moat_intelligence.get("moats", [])
    signal_found = [m for m in moats if m["tier"] == "signal_found"]
    regulation = next((m for m in moats if m["moat_type"] == "regulation" and m["tier"] == "signal_found"), None)
    not_established = [m for m in moats if m["tier"] == "not_yet_established"]

    if not_established:
        names = ", ".join(m["moat_type"].replace("_", " ").title() for m in not_established)
        copyable_today = _tag(
            f"Concretely, everything: {names} show no real signal yet in your own description, which "
            "means a competitor with your same feature list could match you line for line. That's "
            "expected this early — the point isn't to panic about it, it's to know exactly which of "
            "these to start earning first.",
            "inference",
        )
    else:
        copyable_today = _tag(
            "Nothing about your current setup reads as trivially copyable — every checked moat "
            "dimension already has some real signal behind it.",
            "inference",
        )

    earners = signal_found + ([regulation] if regulation and regulation not in signal_found else [])
    if earners:
        detail = "; ".join(f"{m['moat_type'].replace('_', ' ').title()} — {m['basis']}" for m in earners)
        cannot_copy = _tag(detail, "evidence")
    else:
        cannot_copy = _tag(
            "Nothing yet — no moat has real signal in your own description today. That's normal this "
            "early; a moat is earned through traction and technical depth, not claimed in advance.",
            "inference",
        )

    return {
        "what_competitors_can_copy_today": copyable_today,
        "what_they_cannot_copy": cannot_copy,
        # General startup-mechanics reasoning about how THESE SAME checked moat types typically
        # compound with scale — never a per-venture prediction, never a fabricated number, and
        # never a moat type this venture wasn't already checked against above.
        "defensible_after_10_customers": _tag(
            "Enough for a first real case study and, if you have any real integration or embedded-workflow "
            "lock-in, the earliest switching-cost signal — not yet enough volume for a data moat or network "
            "effects to compound.",
            "market_assumption",
        ),
        "defensible_after_100_customers": _tag(
            "Enough usage for a genuine data moat to start compounding if you're accumulating proprietary "
            "data, and for early word-of-mouth/brand signal to build — network effects still need real "
            "multi-sided density, not just customer count, to become real.",
            "market_assumption",
        ),
        "defensible_after_1000_customers": _tag(
            "At this scale, any real data or switching-cost moat becomes genuinely hard to replicate "
            "quickly, and distribution/brand advantages compound — network effects only become realistic "
            "here if the underlying model is genuinely multi-sided, not simply high-volume.",
            "market_assumption",
        ),
    }


def _build_market_insight(pricing: dict, gtm: dict, competitors: dict, features: dict, benchmark: dict | None) -> list[dict]:
    """Curated, already-personalized (venture_signals-driven) sentences from four previously
    separate sections — the full category-level detail these draw from stays available in
    `appendix`; this list keeps only the parts that answer 'why THIS startup', not 'why this
    category in general'."""
    pricing_content = (
        f"Recommended price: {pricing['recommended_price_per_customer']} {pricing['currency']}"
        if pricing.get("recommended_price_per_customer") is not None
        else f"Recommended range: {pricing['recommended_price_range']['low']}–{pricing['recommended_price_range']['high']} {pricing['currency']}"
    )
    pricing_category = "ai_recommendation" if pricing.get("confidence") == "high" else "market_assumption"
    items = [
        _tag(pricing_content, pricing_category),
        _tag(gtm["who_to_approach_first"], "ai_recommendation"),
        _tag(gtm["early_adopter_profile"], "ai_recommendation"),
        _tag(competitors["how_to_win"], "ai_recommendation"),
    ]
    top_feature = features.get("ai_feature") or {}
    if top_feature:
        items.append(_tag(f"{top_feature.get('idea', '')} — {top_feature.get('why', '')}", "ai_recommendation"))
    growth_path = (benchmark or {}).get("growth_path") or {}
    if growth_path.get("pattern"):
        items.append(_tag(growth_path["pattern"], "market_assumption" if growth_path.get("source") != "retrieved_evidence" else "evidence"))
    return items


def _build_success_path(roadmap: list[dict], pilot_roadmap: dict, funding_stage_ladder: dict, funding_assessment: dict) -> dict:
    """Built ONLY from already-computed roadmap_30_60_90 + pilot_roadmap + funding_stage_ladder —
    no new projection, no invented milestone. Framed conditionally ('if you execute the plan
    above') rather than as a prediction."""
    periods = {p["period"]: p for p in roadmap}
    day_30 = periods.get("days_1_30", {})
    day_90 = periods.get("days_61_90", {})
    weeks = pilot_roadmap.get("weeks") or []
    week_4 = next((w for w in weeks if w["week"] == 4), None)

    day_30_content = day_30.get("focus", "")
    if weeks:
        day_30_content += f" — week by week: {'; '.join(w['focus'] for w in weeks)}."

    day_90_content = day_90.get("focus", "")
    if week_4:
        day_90_content += f" Decision point: {week_4['activities'][-1] if week_4['activities'] else pilot_roadmap.get('go_no_go_decision', '')}"

    next_stage = funding_stage_ladder.get("next_stage")
    month_6_content = (
        f"If the 90-day plan above goes well, the next real milestone worth aiming for is moving from "
        f"'{funding_stage_ladder.get('current_stage')}' to '{next_stage}' — {funding_stage_ladder.get('what_moves_you_to_next_stage', '')}"
        if next_stage
        else "If the 90-day plan above goes well, the next real milestone is sharpening what already works, not chasing a new stage label."
    )

    is_ready = funding_assessment.get("level") == "ready"
    month_12_content = (
        "Twelve months out, if this pattern holds, the goal shifts from proving readiness to compounding "
        "on it — the specific next move depends on which of the advantages above you've actually built on."
        if is_ready
        else "Twelve months out, if this pattern holds, the concrete bar worth aiming for is reaching a "
        "'ready' funding-readiness level on this same rubric — not a new stage label, since that's the "
        "one this pipeline already measures you against."
    )

    return {
        "day_30": _tag(day_30_content, "ai_recommendation"),
        "day_90": _tag(day_90_content, "ai_recommendation"),
        "month_6": _tag(month_6_content, "ai_recommendation"),
        "month_12": _tag(month_12_content, "ai_recommendation"),
    }


def _build_appendix(
    startup_name: str,
    judge_summary: dict,
    mentor: dict,
    funding_assessment: dict,
    revenue_estimate: dict | None,
    success_prediction: dict | None,
    idea_understanding: dict,
    pricing: dict,
    gtm: dict,
    features: dict,
    competitors: dict,
    mentor_verdict: dict,
    founder_guidance_items: list[dict],
) -> dict:
    """Everything NOT part of the main consulting narrative above — the full previous section set,
    kept intact for anyone who wants the underlying depth (a technical reviewer, a judge checking
    rigor, a founder who wants the raw detail). Deliberately never referenced from sections 1-9
    above except by explicit cross-reference (e.g. 'see Problem #2 above')."""
    is_low_confidence = bool((judge_summary.get("venture_positioning") or {}).get("is_low_confidence", True))

    strengths_evidence = [_tag(s, "evidence") for s in mentor.get("strengths", [])]
    risks = [
        _tag(item.get("title") or item.get("observation", ""), "evidence")
        for item in founder_guidance_items
        if item.get("category") == "confirmed_risk"
    ] or [_tag("No confirmed risks in the evidence submitted — that's a fact about what was submitted, not a claim the venture is risk-free.", "evidence")]
    opportunities = [
        _tag(item.get("title") or item.get("observation", ""), "inference")
        for item in founder_guidance_items
        if item.get("category") in ("validation_opportunity", "future_enhancement", "improvement_opportunity")
    ]

    if success_prediction is not None:
        historical_pattern = _tag(
            "A historical-pattern comparison is available below — informational only, never used as "
            "a risk signal or readiness score anywhere in this report.",
            "evidence",
        )
    else:
        historical_pattern = _tag("No historical-pattern comparison was available for this run.", "evidence")

    venture_retrieval = mentor.get("venture_retrieval") or {}
    venture_space = venture_retrieval.get("venture_space_analytics") if venture_retrieval.get("available") else None
    venture_space_analysis = []
    if venture_space:
        novelty = venture_space["novelty_score"]
        venture_space_analysis.append(_tag(f"Novelty score {novelty['value']:.2f} — {novelty['note']}", "evidence"))
        density = venture_space["competition_density"]
        venture_space_analysis.append(
            _tag(
                f"Competition density: {density['count']} of the reference corpus "
                f"({density['fraction_of_corpus']:.1%}) score at or above {density['threshold']} similarity to this venture.",
                "evidence",
            )
        )
        if venture_space.get("innovation_distance"):
            innov = venture_space["innovation_distance"]
            venture_space_analysis.append(_tag(f"Innovation distance {innov['value']:.2f} from the '{innov['reference_industry']}' category prototype.", "evidence"))
        if venture_space.get("market_crowdedness"):
            mc = venture_space["market_crowdedness"]
            venture_space_analysis.append(_tag(f"Market crowdedness: the '{mc['industry']}' category represents {mc['value']:.1%} of the reference corpus ({mc['corpus_size']} companies).", "evidence"))
        oi = venture_space["opportunity_isolation"]
        venture_space_analysis.append(_tag(f"Opportunity isolation: {'flagged' if oi['is_isolated'] else 'not flagged'} — {oi['definition']}", "inference"))
        venture_space_analysis.append(_tag(f"Venture cluster metric: {venture_space['venture_cluster']['reason']}", "evidence"))
    similar_historical_ventures = (
        [
            _tag(f"{v['name']} ({v['industry']}, similarity {v['similarity']:.2f}): {v['why_similar']}", "evidence")
            for v in venture_retrieval.get("neighbors", [])
        ]
        if venture_retrieval.get("available")
        else []
    )
    comparative = venture_retrieval.get("comparative_intelligence") or {}
    comparative_pattern_summary = []
    if comparative.get("available"):
        industry_c = comparative.get("common_industry_positioning") or {}
        if industry_c.get("available"):
            comparative_pattern_summary.append(_tag(f"{industry_c['support']} (citing: {', '.join(industry_c['citations'][:3])})", "evidence"))
        terminology_c = comparative.get("common_terminology") or {}
        if terminology_c.get("available"):
            top_terms = ", ".join(t["term"] for t in terminology_c["terms"][:5])
            comparative_pattern_summary.append(_tag(f"Common terms across similar ventures' own descriptions: {top_terms}", "evidence"))
        for dim in ("common_geography", "common_funding_stage_pattern"):
            field = comparative.get(dim) or {}
            if field.get("available"):
                comparative_pattern_summary.append(_tag(f"{field['support']} ({field['coverage']}; citing: {', '.join(field['citations'][:3])})", "evidence"))
        for dim in ("common_pricing_model", "common_deployment_strategy", "common_go_to_market_motion"):
            note = (comparative.get(dim) or {}).get("note")
            if note:
                comparative_pattern_summary.append(_tag(f"{dim.replace('_', ' ').title()}: {note}", "evidence"))

    action_plan = [
        _tag(f"{_format_period_label(period['period'])}: {period['focus']}", "ai_recommendation")
        for period in mentor.get("roadmap_30_60_90", [])
    ]

    blind_spots = [
        {
            "title": _tag(bs["title"], "evidence" if bs["blind_spot_type"] != "missing_gtm_evidence" else "inference"),
            "detail": _tag(bs["detail"], "evidence"),
            "why_investors_care": _tag(bs["why_investors_care"], "inference"),
        }
        for bs in mentor.get("critical_blind_spots", [])
    ]
    investor_questions = [
        {"persona": q["persona"], "question": _tag(q["question"], "inference"), "grounded_in": _tag(q["grounded_in"], "evidence")}
        for q in mentor.get("investor_questions", [])
    ]
    challenge_mode = [
        {
            "objection_category": c["objection_category"],
            "objection": _tag(c["objection"], "inference"),
            "grounded_in": _tag(c["grounded_in"], "evidence"),
            "how_to_overcome": _tag(c["how_to_overcome"], "ai_recommendation"),
        }
        for c in mentor.get("founder_challenge_mode", [])
    ]
    moat = mentor.get("moat_intelligence") or {}
    _moats = moat.get("moats", [])
    _established = [m for m in _moats if m["tier"] == "signal_found" or m["moat_type"] == "regulation"]
    _not_established = [m for m in _moats if m not in _established]
    moat_intelligence = [
        _tag(f"{m['moat_type'].replace('_', ' ').title()} ({m['tier'].replace('_', ' ')}): {m['basis']}", "evidence" if m["tier"] == "signal_found" else "inference")
        for m in _established
    ]
    if _not_established:
        names = ", ".join(m["moat_type"].replace("_", " ").title() for m in _not_established)
        moat_intelligence.append(
            _tag(
                f"Not yet established: {names}. None of these showed up as a real signal in your own "
                "description — that's expected this early, and any one of them could become a real "
                "moat once you have the traction or technical depth to back it up.",
                "inference",
            )
        )
    feature_gap_market = mentor.get("feature_gap_vs_market") or {}
    feature_gap_vs_market = (
        [_tag(f"{g['capability']}: {g['evidence']}", "evidence") for g in feature_gap_market.get("gaps", [])]
        if feature_gap_market.get("available")
        else [_tag(feature_gap_market.get("reason", "Not available for this run."), "evidence")]
    )
    stage_ladder = mentor.get("funding_stage_ladder") or {}
    funding_stage_ladder = {
        "current_stage": stage_ladder.get("current_stage"),
        "next_stage": stage_ladder.get("next_stage"),
        "what_moves_you_forward": _tag(stage_ladder.get("what_moves_you_to_next_stage", ""), "ai_recommendation"),
        "basis": _tag(stage_ladder.get("basis", ""), "evidence"),
    }
    iq_report = mentor.get("founder_iq_report") or {}
    founder_iq_report = {
        "category_scores": {
            category: {"understanding_level": scores["understanding_level"], "basis": _tag(scores["basis"], "evidence")}
            for category, scores in (iq_report.get("category_scores") or {}).items()
        },
        "knowledge_gaps": iq_report.get("knowledge_gaps", []),
        "dominant_thinking_pattern": (
            _tag(iq_report["dominant_thinking_pattern"], "inference") if iq_report.get("dominant_thinking_pattern") else None
        ),
    }
    pilot_roadmap_raw = mentor.get("pilot_roadmap") or {}
    pilot_roadmap = {
        "weeks": pilot_roadmap_raw.get("weeks", []),
        "pilot_customers": _tag(pilot_roadmap_raw.get("pilot_customers", ""), "ai_recommendation"),
        "validation_metrics": _tag(pilot_roadmap_raw.get("validation_metrics", ""), "ai_recommendation"),
        "success_criteria": _tag(pilot_roadmap_raw.get("success_criteria", ""), "experiment_suggestion"),
        "pivot_conditions": _tag(pilot_roadmap_raw.get("pivot_conditions", ""), "inference"),
        "go_no_go_decision": _tag(pilot_roadmap_raw.get("go_no_go_decision", ""), "ai_recommendation"),
    }

    benchmark = mentor.get("startup_benchmark") or {}

    def _benchmark_field(field: dict | None) -> dict:
        if not field:
            return _tag("Not available for this run.", "market_assumption")
        category = "evidence" if field.get("source") == "retrieved_evidence" else "market_assumption"
        pattern = field["pattern"]
        content = "; ".join(pattern) if isinstance(pattern, list) else pattern
        return _tag(content, category)

    startup_benchmark = {
        "industry_positioning": (
            _tag(benchmark["industry_positioning_pattern"]["pattern"], "evidence")
            if benchmark.get("industry_positioning_pattern")
            else _tag("No retrieval-backed industry positioning pattern available for this run.", "market_assumption")
        ),
        "pricing_approach": _benchmark_field(benchmark.get("pricing_approach")),
        "customer_acquisition_pattern": _benchmark_field(benchmark.get("customer_acquisition_pattern")),
        "typical_pilot_strategy": _benchmark_field(benchmark.get("typical_pilot_strategy")),
        "common_mistakes": _benchmark_field(benchmark.get("common_mistakes")),
        "typical_first_customer": _benchmark_field(benchmark.get("typical_first_customer")),
        "growth_path": _benchmark_field(benchmark.get("growth_path")),
        "retrieved_ventures_used": benchmark.get("retrieved_ventures_used", []),
    }

    investor_intel = mentor.get("investor_intelligence") or {}
    investor_intelligence = {
        "why_similar_ventures_succeed": [_tag(p, "market_assumption") for p in investor_intel.get("why_similar_ventures_succeed", {}).get("patterns", [])],
        "why_similar_ventures_fail": [_tag(p, "market_assumption") for p in investor_intel.get("why_similar_ventures_fail", {}).get("patterns", [])],
        "likely_investor_objections": [_tag(o["objection"], "inference") for o in investor_intel.get("likely_investor_objections", [])],
        "most_important_milestones": [_tag(f"{m['milestone']}: {m['current_state']}", "evidence") for m in investor_intel.get("most_important_milestones", [])],
        "most_important_traction_metrics": [_tag(m["metric"], "ai_recommendation") for m in investor_intel.get("most_important_traction_metrics", [])],
    }

    pack = mentor.get("industry_knowledge_pack") or {}
    industry_context = {
        "typical_customer": _tag(pack.get("typical_customer", ""), "market_assumption"),
        "buying_process": _tag(pack.get("buying_process", ""), "market_assumption"),
        "customer_journey": [_tag(step, "market_assumption") for step in pack.get("customer_journey", [])],
        "common_integrations": [_tag(i, "market_assumption") for i in pack.get("common_integrations", [])],
        "expected_kpis": [_tag(k, "market_assumption") for k in pack.get("expected_kpis", [])],
        "procurement_difficulty": _tag(pack.get("procurement_difficulty", ""), "market_assumption"),
        "sales_cycle": _tag(pack.get("sales_cycle", ""), "market_assumption"),
        "enterprise_objections": [_tag(o, "market_assumption") for o in pack.get("enterprise_objections", [])],
        "smb_objections": [_tag(o, "market_assumption") for o in pack.get("smb_objections", [])],
        "customer_acquisition_channels": [_tag(c, "market_assumption") for c in pack.get("customer_acquisition_channels", [])],
        "retention_strategy": _tag(pack.get("retention_strategy", ""), "market_assumption"),
        "expansion_triggers": [_tag(t, "market_assumption") for t in pack.get("expansion_triggers", [])],
        "enterprise_readiness_checklist": [_tag(c, "market_assumption") for c in pack.get("enterprise_readiness_checklist", [])],
        "regulatory_considerations": _tag(pack.get("regulatory_considerations", ""), "market_assumption"),
        "technical_stack_expectations": _tag(pack.get("technical_stack_expectations", ""), "market_assumption"),
        "typical_differentiation": _tag(pack.get("typical_differentiation", ""), "market_assumption"),
        "common_feature_roadmap": [_tag(f, "market_assumption") for f in pack.get("common_feature_roadmap", [])],
    }

    return {
        "executive_summary": _tag(judge_summary.get("overall_assessment", ""), "inference"),
        "startup_snapshot": {
            "name": startup_name,
            "positioning": _tag(mentor.get("venture_positioning", ""), "inference" if is_low_confidence else "evidence"),
            "funding_readiness_level": _tag(funding_assessment.get("level", "unknown"), "evidence"),
        },
        "problem_analysis": _tag(idea_understanding.get("problem", ""), "evidence"),
        "customer_analysis": _tag(mentor.get("customer_and_market", ""), "inference"),
        "business_model": _tag(mentor.get("business_model", ""), "inference"),
        "market_position": _tag(mentor.get("venture_positioning", ""), "inference" if is_low_confidence else "evidence"),
        "pricing_strategy": {
            "recommendation": _tag(
                (
                    f"Recommended price: {pricing['recommended_price_per_customer']} {pricing['currency']}"
                    if pricing.get("recommended_price_per_customer") is not None
                    else f"Recommended range: {pricing['recommended_price_range']['low']}–{pricing['recommended_price_range']['high']} {pricing['currency']}"
                ),
                "ai_recommendation" if pricing.get("confidence") == "high" else "market_assumption",
            ),
            "rationale": [_tag(r, "market_assumption") for r in pricing["rationale"]],
        },
        "go_to_market_strategy": {
            "who_to_approach_first": _tag(gtm["who_to_approach_first"], "ai_recommendation"),
            "first_customers": _tag(gtm["first_twenty_customers_source"], "ai_recommendation"),
            "early_adopter_profile": _tag(gtm["early_adopter_profile"], "ai_recommendation"),
            "distribution_channels": [_tag(c, "ai_recommendation") for c in gtm["distribution_channels"]],
            "sales_motion": _tag(gtm["sales_motion"], "ai_recommendation"),
            "validation_roadmap": [_tag(v, "experiment_suggestion") for v in gtm["validation_roadmap"]],
            "expansion_roadmap": [_tag(e, "ai_recommendation") for e in gtm["expansion_roadmap"]],
        },
        "competitive_landscape": {
            "summary": _tag(mentor.get("competitor_landscape", ""), "evidence"),
            "likely_alternatives": [_tag(a, "market_assumption") for a in competitors["likely_customer_alternatives"]],
            "switching_behavior": _tag(competitors["switching_behavior"], "market_assumption"),
            "switching_friction": _tag(competitors["switching_friction"], "market_assumption"),
            "how_to_win": _tag(competitors["how_to_win"], "ai_recommendation"),
            "similar_historical_ventures": similar_historical_ventures,
            "comparative_pattern_summary": comparative_pattern_summary,
            "venture_space_analysis": venture_space_analysis,
        },
        "product_roadmap": action_plan,
        "critical_blind_spots": blind_spots,
        "investor_questions": investor_questions,
        "founder_challenge_mode": challenge_mode,
        "moat_intelligence": moat_intelligence,
        "feature_gap_vs_market": feature_gap_vs_market,
        "funding_stage_ladder": funding_stage_ladder,
        "founder_iq_report": founder_iq_report,
        "pilot_roadmap": pilot_roadmap,
        "startup_benchmark": startup_benchmark,
        "investor_intelligence": investor_intelligence,
        "industry_context": industry_context,
        "ai_feature_suggestions": [
            _tag(f"{label.replace('_', ' ').title()}: {features[label]['idea']} — {features[label]['why']}", "ai_recommendation")
            for label in ("ai_feature", "automation", "analytics", "integrations", "premium_tier", "enterprise_feature")
        ],
        "risk_assessment": risks,
        "opportunity_assessment": opportunities,
        "funding_readiness": _tag(
            f"{funding_assessment.get('level', 'unknown')} ({funding_assessment.get('overall_score', 0):.0f}/100 on the readiness rubric)",
            "evidence",
        ),
        "historical_pattern_signal": historical_pattern,
        "ninety_day_action_plan": [
            _tag(f"Week {w['week']} ({w['focus']}): {'; '.join(w['activities'])}", "ai_recommendation")
            for w in pilot_roadmap_raw.get("weeks", [])
        ] or action_plan,
        "final_mentor_verdict": _tag(mentor_verdict.get("concise_verdict", ""), "inference"),
        "evidence_supporting_strengths": strengths_evidence,
        "knowledge_transparency_note": (
            "The full evidence/inference/ai_recommendation/market_assumption/experiment_suggestion tag "
            "on every claim above, plus this pipeline's own knowledge-source and consistency audits, are "
            "reported alongside this report as mentor.knowledge_audit and mentor.consistency_audit — not "
            "duplicated inside the report body itself."
        ),
    }


def build_founder_report(
    startup_name: str,
    judge_summary: dict,
    mentor: dict,
    funding_assessment: dict,
    revenue_estimate: dict | None,
    success_prediction: dict | None,
) -> dict:
    """Build the complete consulting-engagement founder report. `mentor` is the in-progress
    deterministic mentor dict from app.agents.mentor_synthesis.build_deterministic_mentor — called
    at the end of that function once every section it composes from already exists."""
    idea_understanding = mentor["idea_understanding"]
    pricing = mentor["pricing_intelligence"]
    gtm = mentor["go_to_market_intelligence"]
    features = mentor["feature_intelligence"]
    competitors = mentor["competitor_intelligence"]
    mentor_verdict = mentor["mentor_verdict"]
    founder_guidance_items = mentor.get("founder_guidance_items", [])
    funding_stage_ladder = mentor.get("funding_stage_ladder") or {}
    blind_spots_raw = mentor.get("critical_blind_spots", [])
    blind_spot_reasons = {b["dimension"]: b["why_investors_care"] for b in blind_spots_raw}

    three_problems = _build_three_biggest_problems(founder_guidance_items, blind_spot_reasons)
    three_advantages = _build_three_biggest_advantages(founder_guidance_items)
    excluded_dims = {p["dimension"] for p in three_problems} | {a["dimension"] for a in three_advantages}
    problem_rank_by_dimension = {p["dimension"]: p["rank"] for p in three_problems}

    return {
        "founder_report_version": FOUNDER_REPORT_VERSION,
        "executive_verdict": _build_executive_verdict(startup_name, idea_understanding, mentor_verdict, funding_assessment, funding_stage_ladder),
        "what_we_learned": _build_what_we_learned(founder_guidance_items, excluded_dims),
        "three_biggest_problems": three_problems,
        "three_biggest_advantages": three_advantages,
        "investor_view": _build_investor_view(
            mentor.get("investor_questions", []), mentor.get("founder_challenge_mode", []), blind_spots_raw, problem_rank_by_dimension
        ),
        "founder_strategy": _build_founder_strategy(mentor.get("validation_plan", [])),
        "moat_and_competitive_position": _build_moat_and_competitive_position(mentor.get("moat_intelligence") or {}),
        "market_insight": _build_market_insight(pricing, gtm, competitors, features, mentor.get("startup_benchmark")),
        "success_path": _build_success_path(
            mentor.get("roadmap_30_60_90", []), mentor.get("pilot_roadmap") or {}, funding_stage_ladder, funding_assessment
        ),
        "appendix": _build_appendix(
            startup_name, judge_summary, mentor, funding_assessment, revenue_estimate, success_prediction,
            idea_understanding, pricing, gtm, features, competitors, mentor_verdict, founder_guidance_items,
        ),
        "disclaimer": (
            "Every claim above is explicitly tagged: 'evidence' (established fact from what was "
            "submitted), 'inference' (a reasoned conclusion from that evidence), 'ai_recommendation' "
            "(a suggestion, not a fact about this venture), 'market_assumption' (a general pattern "
            "assumed to apply, not a cited statistic), or 'experiment_suggestion' (a concrete test to "
            "run). Nothing here is fabricated market research, a verified competitor database, or a "
            "live pricing feed. The full technical detail behind every section above — including every "
            "previous section this report used to show inline — lives in the appendix."
        ),
    }
