export type EvidenceState = "confirmed_positive" | "confirmed_negative" | "not_sure_yet" | "not_applicable";

export interface DimensionEvidence {
  state: EvidenceState;
  /** Only meaningful when state === "confirmed_positive"; 1 (some evidence) or 2 (strong evidence). */
  severity?: number | null;
}

export interface FundingAnswers {
  problem_clarity?: DimensionEvidence;
  customer_pain_evidence?: DimensionEvidence;
  market_size_evidence?: DimensionEvidence;
  product_maturity?: DimensionEvidence;
  traction?: DimensionEvidence;
  revenue_model_clarity?: DimensionEvidence;
  team_completeness?: DimensionEvidence;
  competitive_differentiation?: DimensionEvidence;
}

export interface CompanyMetrics {
  total_funding_usd?: number | null;
  funding_rounds?: number | null;
  founded_year?: number | null;
  country_code?: string | null;
}

export interface RevenueAssumptions {
  price_per_customer_usd?: number | null;
  initial_customers?: number | null;
  monthly_growth_rate_pct?: number | null;
  gross_margin_pct?: number | null;
}

export interface MarketEvidence {
  target_market?: string | null;
  customer_type?: string | null;
  geography?: string | null;
  startup_stage?: string | null;
  known_competitors?: string[];
}

export interface CustomerRFMInput {
  recency_days: number;
  frequency: number;
  monetary: number;
}

export interface Startup {
  id: string;
  name: string;
  description: string;
  funding_answers: FundingAnswers;
  company_metrics: CompanyMetrics;
  revenue_assumptions: RevenueAssumptions;
  market_evidence: MarketEvidence;
  customer_rfm: CustomerRFMInput | null;
  created_at: string;
  updated_at: string;
}

export interface IndustryAlternative {
  industry: string;
  confidence: number;
}

export interface ExplanationTerm {
  term: string;
  kind?: "word" | "char";
  contribution: number;
  direction: "supports" | "opposes";
}

export interface Explanation {
  method: string;
  available: boolean;
  terms: ExplanationTerm[];
  note?: string;
}

export interface IndustryPrediction {
  predicted_industry: string;
  confidence: number;
  alternatives: IndustryAlternative[];
  model_version: string;
  model_pipeline?: string;
  explanation: Explanation;
  is_uncertain?: boolean;
  uncertainty_reasons?: string[];
  // v2 additive fields (Industry Classifier V2 upgrade) — never replace fields above.
  primary_industry?: string;
  primary_confidence?: number;
  secondary_industry?: string | null;
  secondary_confidence?: number | null;
  is_low_confidence?: boolean;
  abstention_threshold?: number;
  abstention_reason?: string | null;
}

/** One deployment-sector match from the backend's `extract_deployment_sectors` — e.g. a
 * description mentioning "hotel" surfaces {sector: "Hotels", matched_text: ["hotel"]}.
 * Deterministic keyword extraction, not a model prediction. */
export interface CustomerHint {
  sector: string;
  matched_text: string[];
}

/** Response of `POST /predict/industry` — the thin, read-only Discovery-only preview. Every
 * field mirrors `IndustryPrediction` above exactly (same classifier, same confidence
 * calculation); `available: false` is the honest "can't answer yet" state (untrained
 * classifier, or too little text) and is not an error. */
export interface IndustryPreview {
  available: boolean;
  predicted_industry: string | null;
  confidence: number | null;
  is_uncertain: boolean | null;
  uncertainty_reasons: string[];
  secondary_industry: string | null;
  secondary_confidence: number | null;
  model_version: string | null;
  customer_hints: CustomerHint[];
  detected_keywords: string[];
}

export interface FundingBreakdownItem {
  dimension: string;
  label: string;
  state: EvidenceState;
  /** null only when state === "not_applicable" (excluded from scoring entirely). */
  raw_score: number | null;
  max_score: number;
  weight: number;
  weighted_contribution: number;
  scale_description: string;
}

export interface FundingAssessment {
  rubric_version: string;
  overall_score: number;
  level: "ready" | "developing" | "early_stage";
  breakdown: FundingBreakdownItem[];
  missing_evidence: string[];
  disclaimer: string;
}

export interface LlmNarrative {
  executive_summary: string;
  strategic_observations: string[];
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
}

export interface ModelCategory {
  label: string;
  confidence: number;
  top_3: { industry: string; confidence: number }[];
  local_explanation: Explanation | null;
  is_uncertain: boolean;
}

export interface VenturePositioning {
  primary_domain: string;
  secondary_domains: string[];
  deployment_sectors: string[];
  confidence: number;
  is_low_confidence: boolean;
  resolution_source:
    | "taxonomy_dominant"
    | "taxonomy_ambiguous_fallback"
    | "taxonomy_gemini_confirmed"
    | "gemini_agreement_within_ambiguity_margin"
    | "user_override"
    | "model_category_fallback"
    // Legacy value from an older stored analysis, predating the corrected Judge rule set.
    | "taxonomy";
}

export interface GeminiStructuredRecommendation {
  recommended_primary_domain: string;
  recommended_secondary_domains: string[];
  confidence: number;
  rationale: string;
}

export interface SuggestedPossibility {
  source_dimension: string;
  suggestion_label: string;
  starting_hypothesis: string;
  assumptions: string[];
  alternatives: string[];
  validation_task: string;
}

export interface JudgeSummary {
  overall_assessment: string;
  strengths: string[];
  weaknesses: string[];
  missing_evidence: string[];
  next_actions: string[];
  confidence_level: "low" | "medium" | "high";
  source_attribution: Record<string, string>;
  /** Structured hypothesis per `not_sure_yet` dimension — see backend/app/agents/hypothesis_engine.py.
   * Never a bare gap message: every entry proposes a starting hypothesis, its assumptions, real
   * alternatives, and a concrete validation task, all explicitly labeled as a suggestion. */
  suggested_possibilities: SuggestedPossibility[];
  /** Two distinct category outputs (Phase 0.5) — see backend/app/agents/venture_positioning.py.
   * `model_category` is the untouched trained-classifier output, relabeled as technical evidence.
   * `venture_positioning` is the founder-facing identity the Judge Agent's deterministic rule set
   * resolves from the controlled taxonomy — present this first, `model_category` second. */
  model_category: ModelCategory | null;
  venture_positioning: VenturePositioning | null;
  taxonomy_candidates: { domain: string; weighted_score: number; matched_concepts: string[] }[];
  /** Gemini's structured recommendation, if invoked — advisory only, never a decision input.
   * `rationale` (inside gemini_structured_recommendation) is display-only text; the Judge's
   * decision rules never parse or score it. */
  gemini_structured_recommendation?: GeminiStructuredRecommendation | null;
  gemini_rationale?: string | null;
  positioning_correction_rationale?: string | null;
  /** Optional supplementary narrative from Gemini — present only when GEMINI_API_KEY is
   * configured server-side and the call succeeded. Never affects industry/confidence/score. */
  llm_narrative?: LlmNarrative | null;
  evidence_categories?: Record<string, string[]>;
}

export interface WorkflowTraceStep {
  node: string;
  status: string;
  detail: string | null;
}

export type PatternSignalLabel =
  | "insufficient_input_reliability"
  | "stronger_comparison"
  | "mixed_comparison"
  | "limited_comparison";

export interface SuccessPrediction {
  // Phase 1 correction: the founder-facing default view must render `pattern_signal_display`/
  // `pattern_signal_sentence` only — never `predicted_label` ("success"/"failure"), which stays
  // below purely for backward compatibility and the Advanced/technical view.
  pattern_signal_label: PatternSignalLabel;
  pattern_signal_display: string;
  pattern_signal_sentence: string;
  predicted_label: "success" | "failure";
  success_probability: number;
  model_version: string;
  model_pipeline: string;
  calibration_method?: string;
  dataset_version: string;
  missing_features: string[];
  is_uncertain: boolean;
  uncertainty_reasons: string[];
  top_global_features?: string[];
  explanation_note?: string;
  // v2 additive fields (Success Predictor V2 upgrade) — never replace fields above.
  operating_threshold?: number;
  recommended_threshold_info?: {
    threshold: number;
    justification: string;
  };
  subgroup_metrics_summary?: Record<string, unknown> | null;
  disclaimer: string;
}

export interface RevenueScenario {
  annual_revenue_usd: number;
  annual_gross_profit_usd: number;
  month_12_customers: number;
  month_12_monthly_revenue_usd: number;
}

export type AssumptionSource = "user_supplied" | "suggested_default";

export interface RevenueAssumptionField {
  value: number;
  unit: string;
  assumption_source: AssumptionSource;
  explanation: string;
  editable: true;
}

export interface RevenueEstimate {
  engine_version: string;
  revenue_defaults_version?: string;
  /** Phase A: always true — a scenario is always produced, every field either user-supplied or a
   * clearly labeled suggested default. See `assumptions` for per-field provenance. */
  available: boolean;
  /** Which of the 4 fields fell back to a suggested default (never user-supplied). */
  missing_assumptions: string[];
  /** "domain_default" | "model_category_default" | "generic_discovery_stage_default". */
  default_basis?: string;
  /** Per-field provenance — the source of truth for whether a number is a fact or a suggestion. */
  assumptions?: {
    price_per_customer_usd: RevenueAssumptionField;
    initial_customers: RevenueAssumptionField;
    monthly_growth_rate_pct: RevenueAssumptionField;
    gross_margin_pct: RevenueAssumptionField;
  };
  scenarios: { conservative: RevenueScenario; base: RevenueScenario; optimistic: RevenueScenario } | null;
  /** Deprecated flat-number alias, kept for older stored analyses/consumers — prefer `assumptions`. */
  assumptions_used?: Required<RevenueAssumptions>;
  disclaimer: string;
}

export interface MarketIntelligence {
  agent_version: string;
  market_summary: string;
  opportunity_drivers: string[];
  constraints: string[];
  evidence_gaps: string[];
  market_maturity: string;
  confidence: "low" | "medium";
  source_attribution: Record<string, string>;
  recommended_validation_actions: string[];
  disclaimer: string;
}

export interface CompetitorEntry {
  competitor_or_alternative: string;
  category: string;
  comparable_capability: string;
  likely_strength: string;
  likely_weakness: string;
  differentiation_gap: string;
  evidence_source: string;
  confidence: string;
  unknown_fields: string[];
}

export interface VerifiedCompetitor {
  name: string;
  verification_status: "unverified_by_system";
  category: string;
  comparable_capability: string;
  likely_strength: string;
  likely_weakness: string;
  differentiation_gap: string;
  evidence_source: string;
  confidence: string;
  unknown_fields: string[];
}

export type CompetitorSolutionType =
  | "software_platform"
  | "marketplace"
  | "manual_process_tool"
  | "service_provider"
  | "other_category";

export interface UnverifiedPossibility {
  category: string;
  /** Present only for possibilities produced by the hardened typed schema (production-hardening
   * phase) — absent for an older stored analysis predating it. */
  solution_type?: CompetitorSolutionType;
  reason?: string;
  evidence_source: string;
  confidence: string;
}

export interface AlternativeCategory {
  category: string;
  evidence_source: string;
  confidence: string;
}

export interface GenericAlternative {
  description: string;
  evidence_source: string;
  confidence: string;
}

export interface CompetitorAnalysis {
  agent_version: string;
  /** Five explicit buckets (Phase B) — see backend/app/agents/competitor_agent.py. Optional
   * because an older, pre-Phase-B stored analysis's JSON blob won't have these keys at all —
   * always guard with `?.` when rendering. */
  verified_competitors?: VerifiedCompetitor[];
  unverified_possibilities?: UnverifiedPossibility[];
  indirect_alternatives?: AlternativeCategory[];
  manual_process_alternative?: GenericAlternative;
  do_nothing_alternative?: GenericAlternative;
  /** Deprecated flat-list alias, kept for older stored analyses/consumers — prefer the 5 buckets. */
  entries: CompetitorEntry[];
  recommended_validation_actions: string[];
  disclaimer: string;
}

export interface CustomerPersona {
  persona_name: string;
  customer_type: string;
  role_or_context: string;
  goal: string;
  pain_point: string;
  current_alternative: string;
  decision_criteria: string;
  adoption_barrier: string;
  likely_channel: string;
  evidence_source: string;
  confidence: string;
  field_provenance: Record<string, string>;
  assumptions_requiring_validation: string[];
}

export interface CustomerPersonas {
  agent_version: string;
  personas: CustomerPersona[];
  disclaimer: string;
}

export interface BusinessModel {
  agent_version: string;
  value_proposition: string;
  customer_segments: string;
  channels: string;
  customer_relationships: string;
  revenue_streams: string;
  key_resources: string;
  key_activities: string;
  key_partners: string;
  cost_structure: string;
  unit_economics_readiness: string;
  scalability: string;
  evidence_gaps: string[];
  recommended_experiments: string[];
  source_attribution: Record<string, string>;
  disclaimer: string;
}

export interface MentorIdeaUnderstanding {
  summary: string;
  target_user: string;
  problem: string;
  proposed_solution: string;
  business_context: string;
}

export interface MentorCapability {
  id: string;
  label: string;
  description: string;
  importance: "core" | "useful" | "advanced";
  prerequisites: string[];
  validation_question: string;
  reason: string;
}

export interface MentorFeatureGapAnalysis {
  present_capabilities: MentorCapability[];
  recommended_capabilities: MentorCapability[];
  premature_capabilities: MentorCapability[];
  not_relevant_capabilities: MentorCapability[];
}

export interface MentorMvpRecommendation {
  target_user: string;
  single_core_problem: string;
  minimum_workflow: string;
  included_capabilities: string[];
  excluded_for_now: string[];
  success_metric: string;
  pilot_environment: string;
  reasons: string[];
}

export interface MentorValidationAction {
  priority: number;
  question_to_answer: string;
  method: string;
  target_participants: string;
  success_criterion: string;
  source_gap: string;
  build_dependency: string;
}

export interface MentorRoadmapPeriod {
  period: "days_1_30" | "days_31_60" | "days_61_90";
  focus: string;
  activities: string[];
  rationale: string;
}

export interface MentorVerdict {
  readiness_level: string;
  concise_verdict: string;
  strongest_signal: string;
  biggest_risk: string;
  immediate_priority: string;
}

export interface MentorEvidenceAndUncertainty {
  model_category_caveat: string;
  historical_pattern_signal_caveat: string;
  low_confidence_flags: string[];
  user_supplied_vs_suggested_summary: string;
  unresolved_questions: string[];
}

export type FounderGuidanceCategory =
  | "strength"
  | "improvement_opportunity"
  | "discovery_question"
  | "validation_opportunity"
  | "confirmed_risk"
  | "future_enhancement";

/** The single structured, coached replacement for the old raw "weakness" strings (Phase 1
 * correction) — see backend/app/agents/founder_guidance.py. Every unknown/gap is one of these six
 * categories, never a bare risk label; `strengths`/`real_weaknesses`/`suggested_possibilities`
 * above are deprecated, backward-compatibility-only fields — render from this list instead. */
export interface FounderGuidanceItem {
  dimension: string;
  category: FounderGuidanceCategory;
  status: string;
  title: string;
  observation: string;
  why_it_matters: string;
  next_step: string;
  example: string;
  priority: number;
  evidence_state: string;
  source: "deterministic";
}

/** Product Intelligence Sprint: every recommendation-bearing sentence in the Founder Report is
 * tagged with exactly one of these five categories server-side (backend/app/agents/founder_report.py)
 * — never rendered without its tag, so a founder always knows what kind of claim they're reading. */
export type FounderReportCategory =
  | "evidence"
  | "inference"
  | "ai_recommendation"
  | "market_assumption"
  | "experiment_suggestion";

export interface TaggedText {
  content: string;
  category: FounderReportCategory;
}

export interface PricingTiers {
  pilot: number;
  launch: number;
  premium: number;
  recommended_starting_tier: "pilot" | "launch" | "premium";
  starting_tier_reason: string;
}

export interface PricingIntelligence {
  pricing_intelligence_version: string;
  currency: string;
  target_market: "india" | "international" | "unclear";
  target_market_is_assumption: boolean;
  confidence: "high" | "low";
  rationale: string[];
  pricing_tiers: PricingTiers;
  personalization: string[];
  recommended_price_per_customer: number | null;
  recommended_price_range: { low: number; high: number } | null;
  source: string;
}

export interface GoToMarketIntelligence {
  gtm_intelligence_version: string;
  who_to_approach_first: string;
  first_twenty_customers_source: string;
  early_adopter_profile: string;
  outreach_strategy: string;
  distribution_channels: string[];
  sales_motion: string;
  validation_roadmap: string[];
  expansion_roadmap: string[];
  personalization: string[];
  source: string;
}

export interface FeatureIdea {
  idea: string;
  why: string;
}

export interface NextBuildRecommendation {
  idea: string | null;
  why: string;
  how_to_validate: string;
  builds_on: string;
}

export interface FeatureIntelligence {
  feature_intelligence_version: string;
  differentiation_is_weak: boolean;
  next_build_recommendation: NextBuildRecommendation;
  framing_note: string;
  ai_feature: FeatureIdea;
  automation: FeatureIdea;
  analytics: FeatureIdea;
  integrations: FeatureIdea;
  premium_tier: FeatureIdea;
  enterprise_feature: FeatureIdea;
  future_roadmap: FeatureIdea;
  monetization_opportunity: FeatureIdea;
  source: string;
}

export interface CompetitorIntelligence {
  competitor_intelligence_version: string;
  framing_note: string;
  named_competitor_context: string;
  likely_customer_alternatives: string[];
  switching_behavior: string;
  switching_friction: string;
  how_to_win: string;
  source: string;
}

/** Every previous flat section, kept intact one level deeper for depth-seekers — see
 * backend/app/agents/founder_report.py's `_build_appendix`. Never part of the main consulting
 * narrative (`FounderReport`'s top-level fields); collapsed by default in the UI. */
export interface FounderReportAppendix {
  executive_summary: TaggedText;
  startup_snapshot: {
    name: string;
    positioning: TaggedText;
    funding_readiness_level: TaggedText;
  };
  problem_analysis: TaggedText;
  customer_analysis: TaggedText;
  business_model: TaggedText;
  market_position: TaggedText;
  pricing_strategy: {
    recommendation: TaggedText;
    rationale: TaggedText[];
  };
  go_to_market_strategy: {
    who_to_approach_first: TaggedText;
    first_customers: TaggedText;
    early_adopter_profile: TaggedText;
    distribution_channels: TaggedText[];
    sales_motion: TaggedText;
    validation_roadmap: TaggedText[];
    expansion_roadmap: TaggedText[];
  };
  competitive_landscape: {
    summary: TaggedText;
    likely_alternatives: TaggedText[];
    switching_behavior: TaggedText;
    switching_friction: TaggedText;
    how_to_win: TaggedText;
    similar_historical_ventures: TaggedText[];
    comparative_pattern_summary: TaggedText[];
    venture_space_analysis: TaggedText[];
  };
  product_roadmap: TaggedText[];
  ai_feature_suggestions: TaggedText[];
  risk_assessment: TaggedText[];
  opportunity_assessment: TaggedText[];
  funding_readiness: TaggedText;
  historical_pattern_signal: TaggedText;
  ninety_day_action_plan: TaggedText[];
  final_mentor_verdict: TaggedText;
  evidence_supporting_strengths: TaggedText[];
  critical_blind_spots: {
    title: TaggedText;
    detail: TaggedText;
    why_investors_care: TaggedText;
  }[];
  investor_questions: {
    persona: string;
    question: TaggedText;
    grounded_in: TaggedText;
  }[];
  founder_challenge_mode: {
    objection_category: string;
    objection: TaggedText;
    grounded_in: TaggedText;
    how_to_overcome: TaggedText;
  }[];
  moat_intelligence: TaggedText[];
  feature_gap_vs_market: TaggedText[];
  funding_stage_ladder: {
    current_stage: string | null;
    next_stage: string | null;
    what_moves_you_forward: TaggedText;
    basis: TaggedText;
  };
  founder_iq_report: {
    category_scores: Record<string, { understanding_level: string; basis: TaggedText }>;
    knowledge_gaps: string[];
    dominant_thinking_pattern: TaggedText | null;
  };
  pilot_roadmap: {
    weeks: { week: number; focus: string; activities: string[] }[];
    pilot_customers: TaggedText;
    validation_metrics: TaggedText;
    success_criteria: TaggedText;
    pivot_conditions: TaggedText;
    go_no_go_decision: TaggedText;
  };
  startup_benchmark: {
    industry_positioning: TaggedText;
    pricing_approach: TaggedText;
    customer_acquisition_pattern: TaggedText;
    typical_pilot_strategy: TaggedText;
    common_mistakes: TaggedText;
    typical_first_customer: TaggedText;
    growth_path: TaggedText;
    retrieved_ventures_used: { name: string; industry: string; similarity: number }[];
  };
  investor_intelligence: {
    why_similar_ventures_succeed: TaggedText[];
    why_similar_ventures_fail: TaggedText[];
    likely_investor_objections: TaggedText[];
    most_important_milestones: TaggedText[];
    most_important_traction_metrics: TaggedText[];
  };
  industry_context: {
    typical_customer: TaggedText;
    buying_process: TaggedText;
    customer_journey: TaggedText[];
    common_integrations: TaggedText[];
    expected_kpis: TaggedText[];
    procurement_difficulty: TaggedText;
    sales_cycle: TaggedText;
    enterprise_objections: TaggedText[];
    smb_objections: TaggedText[];
    customer_acquisition_channels: TaggedText[];
    retention_strategy: TaggedText;
    expansion_triggers: TaggedText[];
    enterprise_readiness_checklist: TaggedText[];
    regulatory_considerations: TaggedText;
    technical_stack_expectations: TaggedText;
    typical_differentiation: TaggedText;
    common_feature_roadmap: TaggedText[];
  };
  knowledge_transparency_note: string;
}

/** The Founder Report — rebuilt as one consulting engagement (Founder Consulting Experience
 * Sprint) rather than a stack of independently-computed analyses. See
 * backend/app/agents/founder_report.py's module docstring for the full information-architecture
 * rationale. Every leaf is a `TaggedText` (or a list of them) so the category is always visible
 * next to the claim; every previous section still exists, verbatim, inside `appendix`. */
export interface FounderReport {
  founder_report_version: string;
  executive_verdict: {
    overall_verdict: TaggedText;
    one_sentence_summary: TaggedText;
    biggest_opportunity: TaggedText;
    biggest_risk: TaggedText;
    investor_readiness: TaggedText;
    current_stage: TaggedText;
    highest_priority_action: TaggedText;
  };
  what_we_learned: TaggedText[];
  three_biggest_problems: {
    rank: number;
    dimension: string;
    problem: TaggedText;
    evidence: TaggedText;
    why_it_matters: TaggedText;
    business_consequence: TaggedText;
    if_ignored: TaggedText;
    recommended_fix: TaggedText;
  }[];
  three_biggest_advantages: {
    rank: number;
    dimension: string;
    advantage: TaggedText;
    evidence: TaggedText;
    why_it_matters: TaggedText;
    business_value: TaggedText;
    risk_if_unused: TaggedText;
    how_to_leverage: TaggedText;
  }[];
  investor_view: {
    dimension: string | null;
    evidence: TaggedText;
    investor_concern: TaggedText;
    likely_objection: TaggedText | null;
    how_to_answer: TaggedText | null;
    investor_question: TaggedText | null;
  }[];
  founder_strategy: {
    priority: number;
    action: TaggedText;
    reason: TaggedText;
    impact: "High" | "Medium" | "Low";
    difficulty: "Easy" | "Medium" | "Hard";
    estimated_duration: string;
    success_metric: TaggedText;
    first_step: TaggedText;
    definition_of_done: TaggedText;
  }[];
  moat_and_competitive_position: {
    what_competitors_can_copy_today: TaggedText;
    what_they_cannot_copy: TaggedText;
    defensible_after_10_customers: TaggedText;
    defensible_after_100_customers: TaggedText;
    defensible_after_1000_customers: TaggedText;
  };
  market_insight: TaggedText[];
  success_path: {
    day_30: TaggedText;
    day_90: TaggedText;
    month_6: TaggedText;
    month_12: TaggedText;
  };
  appendix: FounderReportAppendix;
  disclaimer: string;
}

/** The single coherent, founder-facing mentor result (Full Mentor Orchestration phase) — see
 * backend/app/agents/mentor_schemas.py. `null` only for a run whose judge node itself failed, or
 * an older stored analysis persisted before this phase existed — always guard with `?.`/null
 * checks when rendering. Renders identically whether `source` is "deterministic" or "gemini". */
export interface MentorInterpretation {
  mentor_schema_version: string;
  source: "deterministic" | "gemini";
  idea_understanding: MentorIdeaUnderstanding;
  venture_positioning: string;
  // Deprecated, backward-compatibility only — do not render these; use founder_guidance_items.
  strengths: string[];
  real_weaknesses: string[];
  suggested_possibilities: SuggestedPossibility[];
  founder_guidance_items: FounderGuidanceItem[];
  feature_gap_analysis: MentorFeatureGapAnalysis;
  customer_and_market: string;
  business_model: string;
  competitor_landscape: string;
  revenue_scenarios: string;
  mvp_recommendation: MentorMvpRecommendation;
  validation_plan: MentorValidationAction[];
  roadmap_30_60_90: MentorRoadmapPeriod[];
  top_next_actions: string[];
  mentor_verdict: MentorVerdict;
  evidence_and_uncertainty: MentorEvidenceAndUncertainty;
  source_attribution: Record<string, string>;
  mentor_advice_items?: { domain: string; category: string; text: string }[];
  pricing_intelligence?: PricingIntelligence;
  go_to_market_intelligence?: GoToMarketIntelligence;
  feature_intelligence?: FeatureIntelligence;
  competitor_intelligence?: CompetitorIntelligence;
  founder_report?: FounderReport;
}

export type IdeaConfidenceTier = "confirmed_from_evidence" | "reasonable_hypothesis" | "speculative_future_opportunity";

/** One additive Idea Expansion possibility (Phase 2) — see backend/app/agents/idea_expansion.py.
 * `confidence_tier` must always be shown; "confirmed_from_evidence" is reserved for items derived
 * directly from this venture's own already-computed data (source: "deterministic") — a
 * Gemini-authored item (source: "gemini") can never carry that tier (enforced server-side by the
 * Gemini response schema itself, not just by convention). */
export interface IdeaExpansionItem {
  title: string;
  reason: string;
  confidence_tier: IdeaConfidenceTier;
  source: "deterministic" | "gemini";
}

export interface MvpSimplification {
  current_vision: string;
  simplest_mvp: string;
  version_2: string;
  version_3: string;
  confidence_tier: IdeaConfidenceTier;
}

/** Idea Expansion (Phase 2) — additive, never-authoritative brainstorming on top of the
 * deterministic mentor result. Every suggestion is tagged with a confidence tier and rendered with
 * that tier visible; nothing here ever overrides venture_positioning, funding_assessment, or
 * mentor_verdict. `null` only for a run whose mentor synthesis itself did not run, or an older
 * stored analysis persisted before this phase existed. */
export interface IdeaExpansion {
  idea_expansion_version: string;
  source: "deterministic" | "gemini_enhanced";
  customer_segments: IdeaExpansionItem[];
  adjacent_industries: IdeaExpansionItem[];
  feature_ideas: IdeaExpansionItem[];
  pricing_models: IdeaExpansionItem[];
  mvp_simplification: MvpSimplification;
  pivot_opportunities: IdeaExpansionItem[];
  partnerships: IdeaExpansionItem[];
  go_to_market: IdeaExpansionItem[];
}

export type StrategicRiskCategory = "market" | "timing" | "regulatory" | "technology" | "competition" | "adoption";
export type StrategicRiskLevel = "low" | "medium" | "high";
export type StrategicStage = "idea" | "prototype" | "pilot" | "growth" | "enterprise";

/** One strategic opportunity item (Phase 3) — see backend/app/agents/strategic_opportunity.py.
 * Shared shape for `primary_opportunity`, `adjacent_opportunities`, and `future_expansion`. */
export interface StrategicOpportunityItem {
  opportunity: string;
  reason: string;
  evidence: string;
  confidence_tier: IdeaConfidenceTier;
  recommended_next_step: string;
  potential_revenue: string;
  difficulty: string;
  time_to_market: string;
  validation_effort: string;
  suitable_stage: string;
  source: "deterministic" | "gemini";
}

/** `primary_opportunity` extends the shared item shape with the six required reasoning
 * dimensions (demand/buyer/urgency/willingness-to-pay/competition/implementation-difficulty) —
 * always fully deterministic; Gemini never contributes to this field (see
 * backend/app/agents/strategic_opportunity_reviewer.py). */
export interface PrimaryOpportunity extends StrategicOpportunityItem {
  demand: string;
  buyer: string;
  urgency: string;
  willingness_to_pay: string;
  competition: string;
  implementation_difficulty: string;
}

export interface StrategicRisk {
  risk: string;
  category: StrategicRiskCategory;
  why: string;
  likelihood: StrategicRiskLevel;
  impact: StrategicRiskLevel;
  mitigation: string;
  confidence_tier: IdeaConfidenceTier;
  source: "deterministic" | "gemini";
}

/** Strategic Opportunity Discovery (Phase 3) — "where else could this startup realistically
 * succeed, and why?" Additive strategic reasoning layered on top of Idea Expansion; never
 * overrides venture_positioning, funding_assessment, mentor_verdict, historical pattern signal,
 * customer_personas, judge output, or idea_expansion — those remain authoritative. `null` only
 * for a run whose mentor synthesis itself did not run, or an older stored analysis persisted
 * before this phase existed. */
export interface StrategicOpportunity {
  strategic_opportunity_version: string;
  source: "deterministic" | "gemini_enhanced";
  primary_opportunity: PrimaryOpportunity;
  adjacent_opportunities: StrategicOpportunityItem[];
  future_expansion: StrategicOpportunityItem[];
  strategic_risks: StrategicRisk[];
}

/** Phase 5 (Student 3): deterministic growth/strategy planning output — see
 * backend/app/agents/student3.py. Additive; never overrides mentor_verdict, funding_assessment,
 * idea_expansion, or strategic_opportunity — those remain authoritative. `null` only for a run
 * whose funding_readiness node itself failed upstream, or an older stored analysis persisted
 * before this phase existed. */
export interface Student3CustomerSegment {
  segment_id: string;
  segment_name: string;
  fit_score: number | null;
  characteristics: string[];
  pain_points: string[];
  recommended_channels: string[];
  evidence_basis: string[];
  limitations: string[];
  model_version: string;
  method: "clustering_model" | "unavailable";
}

export interface Student3RankedAction {
  title: string;
  priority_score: number;
  impact: "low" | "medium" | "high";
  effort: "low" | "medium" | "high";
  urgency: "now" | "next" | "later";
  evidence_basis: string[];
  dependency: string;
  readiness_dimension: string;
  ranking_version: string;
}

export interface Student3InnovationOpportunity {
  category: "feature" | "technical" | "operational" | "defensibility" | "ip_direction";
  opportunity: string;
  rationale: string;
  validation_requirement: string;
  assumptions: string[];
}

export type Student3RiskCategory =
  | "market" | "adoption" | "competition" | "technical" | "operations" | "financial"
  | "regulatory_legal" | "privacy_security" | "execution_team";

export interface Student3Risk {
  title: string;
  category: Student3RiskCategory;
  probability_band: "low" | "medium" | "high";
  impact_band: "low" | "medium" | "high";
  severity: "low" | "medium" | "high";
  evidence_basis: string[];
  mitigation: string;
  early_warning_indicator: string;
  assumptions: string[];
}

export interface Student3GrowthItem {
  area: "validation" | "acquisition" | "partnership" | "retention" | "expansion" | "experiment" | "kpi";
  recommendation: string;
  rationale: string;
  dependency: string;
  assumptions: string[];
}

export interface Student3PitchSlide {
  title: string;
  content: string[];
  evidence_status: "verified evidence" | "model inference" | "deterministic assessment" | "assumption" | "evidence required" | "unknown";
}

export interface Student3Outputs {
  customer_segment: Student3CustomerSegment;
  ranked_actions: Student3RankedAction[];
  innovation_opportunities: Student3InnovationOpportunity[];
  risks: Student3Risk[];
  growth_strategy: Student3GrowthItem[];
  pitch_deck: Student3PitchSlide[];
  executive_summary: string[];
}

export interface Analysis {
  id: string;
  startup_id: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
  /** Act IV (The Forging) live-progress fields — see backend/app/agents/stage_labels.py. Both
   * null until the first real orchestrator node of this run has completed; once set, never
   * cleared back to null (even after COMPLETED/FAILED — a late load still shows where it finished). */
  current_node: string | null;
  current_stage: string | null;
  industry_model_version: string | null;
  industry_prediction: IndustryPrediction | null;
  funding_rubric_version: string | null;
  funding_assessment: FundingAssessment | null;
  success_model_version: string | null;
  success_prediction: SuccessPrediction | null;
  revenue_engine_version: string | null;
  revenue_estimate: RevenueEstimate | null;
  market_intelligence: MarketIntelligence | null;
  competitor_analysis: CompetitorAnalysis | null;
  customer_personas: CustomerPersonas | null;
  business_model: BusinessModel | null;
  judge_summary: JudgeSummary | null;
  workflow_trace: WorkflowTraceStep[] | null;
  error_message: string | null;
  /** Full Mentor Orchestration phase — null for a failed run or an older stored analysis. */
  mentor_interpretation?: MentorInterpretation | null;
  /** Phase 2: Idea Expansion — null for a failed run or an older stored analysis. */
  idea_expansion?: IdeaExpansion | null;
  /** Phase 3: Strategic Opportunity Discovery — null for a failed run or an older stored analysis. */
  strategic_opportunity?: StrategicOpportunity | null;
  /** Phase 5 (Student 3): growth/strategy intelligence — null for a failed run or an older stored analysis. */
  student3_outputs?: Student3Outputs | null;
  /** Phase C: auditable history of founder-initiated venture-positioning corrections, oldest
   * first. Always an array (never missing) — empty for any analysis never corrected. */
  positioning_correction_history: PositioningCorrectionHistoryEntry[];
  created_at: string;
  updated_at: string;
}

export interface PositioningCorrectionHistoryEntry {
  previous_positioning: VenturePositioning | null;
  override: { primary_domain: string; secondary_domains: string[] };
  taxonomy_version: string;
  corrected_at: string;
}

export interface TaxonomyDomain {
  id: string;
  label: string;
  description: string;
  deployment_sectors: string[];
}

/** GET /api/v1/taxonomy response — the live source of truth for the controlled
 * venture-positioning taxonomy. See services/api.ts's getTaxonomy and the
 * PositioningCorrection component, which loads this instead of a hardcoded domain list. */
export interface TaxonomyResponse {
  taxonomy_version: string;
  domains: TaxonomyDomain[];
  allowed_secondary_domains: string[];
}

export interface ModelStatus {
  industry_classifier_loaded: boolean;
  industry_classifier_version: string | null;
  industry_classifier_trained_at: string | null;
  funding_rubric_version: string;
  success_predictor_loaded: boolean;
  success_predictor_version: string | null;
  success_predictor_trained_at: string | null;
  revenue_engine_version: string;
}

/** Development-only aggregate health check (backend/app/api/v1/system_status.py). Not available
 * in production (404) — the frontend must fall back to a plain connectivity error in that case. */
export interface SystemStatus {
  api: { ok: boolean };
  database: { ok: boolean; detail: string | null };
  migrations: { up_to_date: boolean | null; detail: string | null };
  industry_model: { ok: boolean; version: string | null; detail: string | null };
  llm: { configured: boolean; detail: string | null };
}
