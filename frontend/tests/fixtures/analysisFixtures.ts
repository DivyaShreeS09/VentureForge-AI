import type { Analysis, MentorInterpretation } from "../../src/types/api";

export function buildMentorInterpretation(overrides: Partial<MentorInterpretation> = {}): MentorInterpretation {
  return {
    mentor_schema_version: "v1",
    source: "deterministic",
    idea_understanding: {
      summary: "WasteLess is building in the Restaurant Operations Technology space.",
      target_user: "Independent restaurant owners.",
      problem: "Food waste eats into thin margins.",
      proposed_solution: "Inventory tracking software.",
      business_context: "Positioned as Restaurant Operations Technology.",
    },
    venture_positioning: "Restaurant Operations Technology.",
    strengths: ["Problem Clarity: Specific, well-defined problem"],
    real_weaknesses: ["Traction: No users/customers"],
    suggested_possibilities: [],
    founder_guidance_items: [
      {
        dimension: "problem_clarity", category: "strength", status: "Confirmed strength",
        title: "Your problem statement is sharp.", observation: "Specific, well-defined problem",
        why_it_matters: "A specific, well-defined problem is one of the strongest early signals.",
        next_step: "Keep validating the people you describe.", example: "example text",
        priority: 1, evidence_state: "confirmed_positive", source: "deterministic",
      },
      {
        dimension: "traction", category: "validation_opportunity", status: "Validation opportunity",
        title: "Traction is your next validation opportunity.", observation: "No users/customers",
        why_it_matters: "A single, well-chosen pilot site or user group is a stronger next step than broad launch.",
        next_step: "Secure one concrete pilot commitment before building further.", example: "example text",
        priority: 2, evidence_state: "confirmed_negative", source: "deterministic",
      },
    ],
    feature_gap_analysis: {
      present_capabilities: [
        { id: "manual_inventory_logging", label: "Manual Inventory Logging", description: "d", importance: "core", prerequisites: [], validation_question: "q", reason: "Matched in the description." },
      ],
      recommended_capabilities: [],
      premature_capabilities: [],
      not_relevant_capabilities: [],
    },
    customer_and_market: "No market intelligence was generated for this run.",
    business_model: "No business-model synthesis was generated for this run.",
    competitor_landscape: "No competitors were named by the founder.",
    revenue_scenarios: "No revenue scenario is available for this run.",
    mvp_recommendation: {
      target_user: "[Suggested] One independent restaurant owner.",
      single_core_problem: "[Suggested] The narrowest version of the food-waste problem.",
      minimum_workflow: "[Suggested] Manual Inventory Logging, applied to one pilot only.",
      included_capabilities: ["manual_inventory_logging"],
      excluded_for_now: [],
      success_metric: "[Suggested] Measured reduction in weekly food waste.",
      pilot_environment: "[Suggested] One real restaurant, not a broad launch.",
      reasons: ["Scoped to one restaurant to de-risk cheaply."],
    },
    validation_plan: [
      {
        priority: 1, question_to_answer: "Is 'Traction' actually true/sufficient?",
        method: "Secure a pilot commitment", target_participants: "1 pilot site/customer",
        success_criterion: "Clear evidence.", source_gap: "traction",
        build_dependency: "Must be resolved before scaling.",
      },
    ],
    roadmap_30_60_90: [
      { period: "days_1_30", focus: "Discovery, evidence-gathering, buyer/user validation", activities: ["Secure a pilot commitment"], rationale: "Validation must come before build effort." },
      { period: "days_31_60", focus: "Minimal prototype / pilot preparation", activities: ["Build the minimum workflow."], rationale: "Building begins after validation." },
      { period: "days_61_90", focus: "Pilot execution, measurement, and iteration", activities: ["Run the pilot."], rationale: "Execution closes the loop." },
    ],
    top_next_actions: [
      "Secure one concrete pilot commitment before building further.",
      "Price the offering to 3 prospective customers.",
      "Compare against the 2 closest alternatives.",
    ],
    mentor_verdict: {
      readiness_level: "developing",
      concise_verdict: "Developing — real progress alongside real gaps.",
      strongest_signal: "Your problem statement is sharp. A specific, well-defined problem is one of the strongest early signals.",
      biggest_risk: "Traction is your next validation opportunity. A single, well-chosen pilot site or user group is a stronger next step than broad launch.",
      immediate_priority: "Secure one concrete pilot commitment before building further.",
    },
    evidence_and_uncertainty: {
      model_category_caveat: "model_category is the raw trained classifier's technical output.",
      historical_pattern_signal_caveat: "Historical Pattern Signal: treat as a loose pattern match.",
      low_confidence_flags: [],
      user_supplied_vs_suggested_summary: "All revenue figures are suggested defaults.",
      unresolved_questions: [],
    },
    source_attribution: {},
    ...overrides,
  };
}

export function buildAnalysis(overrides: Partial<Analysis> = {}): Analysis {
  return {
    id: "analysis-1",
    startup_id: "startup-1",
    status: "COMPLETED",
    industry_model_version: "v1",
    industry_prediction: {
      predicted_industry: "fintech",
      confidence: 0.72,
      alternatives: [],
      model_version: "v1",
      explanation: { method: "linear_coefficient_x_tfidf", available: false, terms: [] },
    },
    funding_rubric_version: "v1",
    funding_assessment: {
      rubric_version: "v1",
      overall_score: 45,
      level: "developing",
      breakdown: [
        { dimension: "traction", label: "Traction", state: "confirmed_negative", raw_score: 0, max_score: 2, weight: 0.14, weighted_contribution: 0, scale_description: "No users/customers" },
      ],
      missing_evidence: [],
      disclaimer: "This is a deterministic readiness assessment, not investment advice.",
    },
    success_model_version: "v1",
    success_prediction: {
      pattern_signal_label: "insufficient_input_reliability",
      pattern_signal_display: "Insufficient input reliability",
      pattern_signal_sentence: "Not enough information was supplied to compare this idea to historical patterns reliably.",
      predicted_label: "success",
      success_probability: 0.5,
      model_version: "v1",
      model_pipeline: "hist_gradient_boosting",
      dataset_version: "v1-crunchbase-2013",
      missing_features: ["total_funding_usd"],
      is_uncertain: true,
      uncertainty_reasons: ["Key inputs were imputed."],
      disclaimer: "Historical pattern estimate — not a guarantee.",
    },
    revenue_engine_version: "v1-deterministic",
    revenue_estimate: null,
    market_intelligence: null,
    competitor_analysis: null,
    customer_personas: null,
    business_model: null,
    judge_summary: {
      overall_assessment: "This startup was classified as 'fintech' and rated 'developing'.",
      strengths: ["Problem Clarity: Specific, well-defined problem"],
      weaknesses: [],
      missing_evidence: [],
      next_actions: [],
      confidence_level: "medium",
      source_attribution: {},
      suggested_possibilities: [],
      model_category: { label: "fintech", confidence: 0.72, top_3: [], local_explanation: null, is_uncertain: false },
      venture_positioning: {
        primary_domain: "Restaurant Operations Technology",
        secondary_domains: ["Food-Cost Management"],
        deployment_sectors: ["Restaurants"],
        confidence: 0.6,
        is_low_confidence: false,
        resolution_source: "taxonomy_dominant",
      },
      taxonomy_candidates: [],
      positioning_correction_rationale: null,
      gemini_rationale: null,
    },
    mentor_interpretation: buildMentorInterpretation(),
    idea_expansion: {
      idea_expansion_version: "v1",
      source: "deterministic",
      customer_segments: [
        { title: "Hotels", reason: "Shares similar inventory-waste needs.", confidence_tier: "confirmed_from_evidence", source: "deterministic" },
      ],
      adjacent_industries: [],
      feature_ideas: [
        { title: "Offline mode", reason: "Kitchens often have unreliable wifi.", confidence_tier: "reasonable_hypothesis", source: "deterministic" },
      ],
      pricing_models: [
        { title: "Subscription", reason: "Predictable recurring revenue.", confidence_tier: "reasonable_hypothesis", source: "deterministic" },
      ],
      mvp_simplification: {
        current_vision: "Full inventory + waste + reorder suite.",
        simplest_mvp: "Manual inventory logging for one restaurant.",
        version_2: "Add POS integration.",
        version_3: "Add automated reorder suggestions.",
        confidence_tier: "confirmed_from_evidence",
      },
      pivot_opportunities: [
        { title: "Food-Cost Management", reason: "If restaurant adoption is slow, this adjacent space may also fit.", confidence_tier: "reasonable_hypothesis", source: "deterministic" },
      ],
      partnerships: [
        { title: "Point-of-sale (POS) vendors", reason: "A natural integration partner.", confidence_tier: "reasonable_hypothesis", source: "deterministic" },
      ],
      go_to_market: [
        { title: "Secure one pilot restaurant.", reason: "A standard early go-to-market step.", confidence_tier: "reasonable_hypothesis", source: "deterministic" },
      ],
    },
    strategic_opportunity: {
      strategic_opportunity_version: "v1",
      source: "deterministic",
      primary_opportunity: {
        opportunity: "Restaurant Operations Technology",
        reason: "This is the strongest current positioning because evidence already concentrates here.",
        evidence: "Demand: some. Buyer: restaurant owners.",
        confidence_tier: "reasonable_hypothesis",
        recommended_next_step: "Secure one concrete pilot commitment before building further.",
        potential_revenue: "Not yet quantified.",
        difficulty: "medium",
        time_to_market: "3-6 months",
        validation_effort: "Ongoing measurement across existing pilots",
        suitable_stage: "pilot",
        source: "deterministic",
        demand: "Targets independent restaurants.",
        buyer: "Independent restaurant owners.",
        urgency: "Not yet confirmed.",
        willingness_to_pay: "Not yet confirmed.",
        competition: "No verified named competitor yet.",
        implementation_difficulty: "medium",
      },
      adjacent_opportunities: [
        { opportunity: "Hotels", reason: "Hotel kitchens face the same food-cost and inventory-waste problem restaurants do, just at larger scale.", evidence: "Derived from taxonomy.", confidence_tier: "reasonable_hypothesis", recommended_next_step: "Interview one hotel kitchen manager.", potential_revenue: "Not yet quantified.", difficulty: "medium", time_to_market: "3-6 months", validation_effort: "1-2 discovery interviews", suitable_stage: "pilot", source: "deterministic" },
      ],
      future_expansion: [
        { opportunity: "Analytics Platform", reason: "The operational data this product already collects is a natural foundation for a standalone analytics product.", evidence: "Grounded in existing capability.", confidence_tier: "speculative_future_opportunity", recommended_next_step: "Revisit once multiple pilots exist.", potential_revenue: "Not yet quantified.", difficulty: "medium", time_to_market: "3-6 months", validation_effort: "1-2 discovery interviews", suitable_stage: "growth", source: "deterministic" },
      ],
      strategic_risks: [
        { risk: "Market may be narrower than assumed", category: "market", why: "If adoption stays niche, the market may be smaller than assumed.", likelihood: "medium", impact: "medium", mitigation: "Validate demand in a second sub-segment.", confidence_tier: "reasonable_hypothesis", source: "deterministic" },
      ],
    },
    student3_outputs: {
      customer_segment: {
        segment_id: "unavailable", segment_name: "Customer segmentation unavailable", fit_score: null,
        characteristics: [], pain_points: [], recommended_channels: [],
        evidence_basis: ["No trained customer-segment assignment was produced."],
        limitations: ["customer RFM input was not supplied"], model_version: "unavailable", method: "unavailable",
      },
      ranked_actions: [
        { title: "Interview prospective customers", priority_score: 90, impact: "high", effort: "low", urgency: "now", evidence_basis: ["Funding rubric: Traction is 0/2."], dependency: "Recruit relevant interview participants.", readiness_dimension: "customer_pain_evidence", ranking_version: "next-action-rules-v1" },
      ],
      innovation_opportunities: [
        { category: "feature", opportunity: "Define a narrow, measurable user outcome.", rationale: "Testable differentiation.", validation_requirement: "Observe target users completing the intended workflow.", assumptions: [] },
      ],
      risks: [
        { title: "Unvalidated customer problem", category: "market", probability_band: "high", impact_band: "high", severity: "high", evidence_basis: ["Funding readiness input for customer_pain_evidence: missing."], mitigation: "Interview target users before committing scope.", early_warning_indicator: "Interviews do not describe a repeated costly problem.", assumptions: [] },
      ],
      growth_strategy: [
        { area: "validation", recommendation: "Interview prospective customers", rationale: "Highest-ranked action from the readiness gaps.", dependency: "A defined interview or pilot cohort.", assumptions: [] },
      ],
      pitch_deck: [
        { title: "Traction and evidence", content: ["Unknown: no revenue, customers, or partnerships were supplied."], evidence_status: "unknown" },
      ],
      executive_summary: ["This startup was classified as 'fintech' and rated 'developing'."],
    },
    workflow_trace: [],
    error_message: null,
    positioning_correction_history: [],
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}
