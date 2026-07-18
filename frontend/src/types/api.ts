export interface FundingAnswers {
  problem_clarity?: number | null;
  customer_pain_evidence?: number | null;
  market_size_evidence?: number | null;
  product_maturity?: number | null;
  traction?: number | null;
  revenue_model_clarity?: number | null;
  team_completeness?: number | null;
  competitive_differentiation?: number | null;
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

export interface Startup {
  id: string;
  name: string;
  description: string;
  funding_answers: FundingAnswers;
  company_metrics: CompanyMetrics;
  revenue_assumptions: RevenueAssumptions;
  market_evidence: MarketEvidence;
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

export interface FundingBreakdownItem {
  dimension: string;
  label: string;
  raw_score: number;
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

export interface JudgeSummary {
  overall_assessment: string;
  strengths: string[];
  weaknesses: string[];
  missing_evidence: string[];
  next_actions: string[];
  confidence_level: "low" | "medium" | "high";
  source_attribution: Record<string, string>;
  /** Optional supplementary narrative from Gemini — present only when GEMINI_API_KEY is
   * configured server-side and the call succeeded. Never affects industry/confidence/score. */
  llm_narrative?: LlmNarrative | null;
}

export interface WorkflowTraceStep {
  node: string;
  status: string;
  detail: string | null;
}

export interface SuccessPrediction {
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

export interface RevenueEstimate {
  engine_version: string;
  available: boolean;
  missing_assumptions: string[];
  scenarios: { conservative: RevenueScenario; base: RevenueScenario; optimistic: RevenueScenario } | null;
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

export interface CompetitorAnalysis {
  agent_version: string;
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

export interface Analysis {
  id: string;
  startup_id: string;
  status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
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
  created_at: string;
  updated_at: string;
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
