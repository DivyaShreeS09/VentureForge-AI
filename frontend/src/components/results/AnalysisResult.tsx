import { useEffect, useState } from "react";
import type { Analysis, ExplanationTerm, RevenueEstimate } from "../../types/api";
import emblem from "../../assets/ventureforge-emblem.webp";
import { ApiError, correctIndustry, getTaxonomy, saveRevenueAssumptions } from "../../services/api";
import { recalculateScenarios } from "../../utils/revenueRecalculation";
import { ConfidenceBar } from "../visualizations/ConfidenceBar";
import { FounderDecisionPanel } from "./studio/FounderDecisionPanel";
import { FounderMentorSection } from "./studio/FounderMentorSection";
import { InvestmentReadinessSection } from "./studio/InvestmentReadinessSection";
import { MarketExpansionSection } from "./studio/MarketExpansionSection";
import { RiskDashboardSection } from "./studio/RiskDashboardSection";
import { RoadmapSection } from "./studio/RoadmapSection";
import { StartupSnapshot } from "./studio/StartupSnapshot";
import { ValidationPlanSection } from "./studio/ValidationPlanSection";
import { WhyThisMatters } from "./studio/WhyThisMatters";
import { Section } from "./Section";
import { WorkflowTrace } from "./WorkflowTrace";

/** Fallback domain list, used only if `GET /api/v1/taxonomy` cannot be reached (offline backend,
 * network error) — the dropdown still degrades to something usable rather than empty. This is
 * NOT the source of truth (the live endpoint is; see backend/app/ml/positioning_taxonomy.py) and
 * is intentionally minimal — it exists purely so the correction control doesn't render as a
 * dead end when the fetch fails. */
const TAXONOMY_FETCH_FALLBACK_DOMAINS = ["Enterprise AI", "General Consumer App"];

/** Loads the controlled positioning taxonomy from the live backend endpoint (no more hardcoded,
 * hand-duplicated domain list) — see backend/app/api/v1/taxonomy.py. Exposes loading/error state
 * so the correction control can render distinct loading/error/fallback UI. */
function useTaxonomy() {
  const [domains, setDomains] = useState<string[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getTaxonomy()
      .then((res) => {
        if (cancelled) return;
        setDomains(res.domains.map((d) => d.id));
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Could not load the positioning taxonomy.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { domains, loading, error };
}

/** Word+char TF-IDF often surfaces several char n-gram fragments of the same root ("robot",
 * "robo", "obot", "rob") alongside the whole word — each is a real, independently-computed
 * contribution, but showing all of them reads as visual noise rather than distinct evidence. Kept
 * in descending |contribution| order (as the backend already sorts them) and drops any fragment
 * that is a substring of, or contains, a fragment already kept — so only the most informative
 * variant of each root term survives. This is presentation-only: it never changes the underlying
 * explanation data, only how many near-duplicate chips are rendered. */
function dedupeExplanationTerms(terms: ExplanationTerm[]): ExplanationTerm[] {
  const kept: ExplanationTerm[] = [];
  for (const term of terms) {
    const text = term.term.toLowerCase();
    const overlapsExisting = kept.some((k) => {
      if (k.direction !== term.direction) return false;
      const other = k.term.toLowerCase();
      return other.includes(text) || text.includes(other);
    });
    if (!overlapsExisting) kept.push(term);
  }
  return kept;
}

/** Lets a founder correct `venture_positioning.primary_domain` from the controlled taxonomy —
 * `model_category` (the raw trained-classifier output) is never editable here or anywhere else;
 * see backend/app/agents/venture_positioning.py's `user_override` rule (always wins). */
function PositioningCorrection({
  analysisId,
  currentPrimaryDomain,
  onCorrected,
}: {
  analysisId: string;
  currentPrimaryDomain: string;
  onCorrected: (updated: Analysis) => void;
}) {
  const [selected, setSelected] = useState(currentPrimaryDomain);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { domains, loading: taxonomyLoading, error: taxonomyError } = useTaxonomy();

  async function handleSubmit() {
    if (selected === currentPrimaryDomain) return;
    setSubmitting(true);
    setError(null);
    try {
      const updated = await correctIndustry(analysisId, { primary_domain: selected });
      onCorrected(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not apply this correction.");
    } finally {
      setSubmitting(false);
    }
  }

  if (taxonomyLoading) {
    return (
      <div className="mt-4 border-t border-white/5 pt-3">
        <p className="text-xs text-ink-muted">Loading available positioning domains…</p>
      </div>
    );
  }

  // On a taxonomy-fetch failure, degrade to a minimal fallback list rather than hiding the
  // control entirely — the founder can still act, and the error is surfaced honestly.
  const domainOptions = domains ?? TAXONOMY_FETCH_FALLBACK_DOMAINS;

  return (
    <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-white/5 pt-3">
      <label className="text-xs text-ink-muted" htmlFor="positioning-correction-select">
        Not the right industry?
      </label>
      <select
        id="positioning-correction-select"
        value={selected}
        onChange={(e) => setSelected(e.target.value)}
        className="rounded-lg border border-white/10 bg-white/[0.02] px-2 py-1 text-xs text-ink-primary"
      >
        {domainOptions.map((domain) => (
          <option key={domain} value={domain}>
            {domain}
          </option>
        ))}
      </select>
      <button
        type="button"
        onClick={handleSubmit}
        disabled={submitting || selected === currentPrimaryDomain}
        className="rounded-lg border border-signal-400/50 bg-signal-500/10 px-3 py-1 text-xs font-medium text-signal-200 transition hover:bg-signal-500/20 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {submitting ? "Applying…" : "Correct industry"}
      </button>
      {taxonomyError && (
        <p role="alert" className="w-full text-xs text-warning-400">
          Could not load the full taxonomy from the server ({taxonomyError}) — showing a minimal
          fallback list only.
        </p>
      )}
      {error && (
        <p role="alert" className="w-full text-xs text-danger-400">
          {error}
        </p>
      )}
    </div>
  );
}

/** Renders the always-present revenue scenario range plus per-field assumption provenance
 * (Phase A). Suggested-default fields are editable — editing recomputes all 3 scenarios locally
 * (see utils/revenueRecalculation.ts) as an instant preview; nothing is persisted by this edit
 * alone. Falls back to a read-only view for an older stored analysis that predates per-field
 * `assumptions` (only has the flat `assumptions_used` numbers, with no provenance to show). */
function RevenueEstimateBlock({
  analysisId,
  revenueEstimate,
  onSaved,
}: {
  analysisId: string;
  revenueEstimate: RevenueEstimate;
  onSaved: (updated: Analysis) => void;
}) {
  const fields = revenueEstimate.assumptions;
  const [overrides, setOverrides] = useState<Record<string, number>>({});
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const price = overrides.price_per_customer_usd ?? fields?.price_per_customer_usd.value ?? revenueEstimate.assumptions_used?.price_per_customer_usd ?? 0;
  const customers = overrides.initial_customers ?? fields?.initial_customers.value ?? revenueEstimate.assumptions_used?.initial_customers ?? 0;
  const growth = overrides.monthly_growth_rate_pct ?? fields?.monthly_growth_rate_pct.value ?? revenueEstimate.assumptions_used?.monthly_growth_rate_pct ?? 0;
  const margin = overrides.gross_margin_pct ?? fields?.gross_margin_pct.value ?? revenueEstimate.assumptions_used?.gross_margin_pct ?? 100;

  // Present but unsaved: a local edit exists that hasn't been persisted via "Save assumptions"
  // yet — the instant preview below reflects it, but a page reload would lose it (by design;
  // see handleSave, which is the only path that persists an edit).
  const hasUnsavedEdits = Object.keys(overrides).length > 0;
  const scenarios = hasUnsavedEdits ? recalculateScenarios(price, customers, growth, margin) : revenueEstimate.scenarios!;

  async function handleSave() {
    setSaving(true);
    setSaveError(null);
    try {
      const updated = await saveRevenueAssumptions(analysisId, { ...overrides });
      onSaved(updated);
      // Draft is now reflected in the persisted analysis returned above — clear local overrides
      // so the block re-renders from the (now up to date) `revenueEstimate` prop, not stale local
      // state pointing at values the server may have recomputed slightly differently.
      setOverrides({});
    } catch (err) {
      // Deliberately do NOT clear `overrides` here — a failed save must never lose the founder's
      // in-progress draft; the inputs keep showing exactly what they typed so they can retry.
      setSaveError(err instanceof ApiError ? String(err.detail ?? err.message) : "Could not save these assumptions.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="mt-6 border-t border-white/5 pt-5">
      <h3 className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-muted">Revenue Estimate</h3>
      <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
        {(["conservative", "base", "optimistic"] as const).map((key) => {
          const s = scenarios[key];
          return (
            <div key={key} className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-muted capitalize">{key}</p>
              <p className="mt-1.5 text-lg text-display text-ink-primary">${s.annual_revenue_usd.toLocaleString()}</p>
              <p className="text-xs text-ink-muted">annual revenue (12mo)</p>
              <p className="mt-1 text-xs text-ink-secondary">${s.annual_gross_profit_usd.toLocaleString()} gross profit</p>
            </div>
          );
        })}
      </div>

      {hasUnsavedEdits && (
        <p className="mt-3 rounded-lg border border-signal-400/30 bg-signal-500/10 px-3 py-1.5 text-xs text-signal-300">
          Unsaved preview — these scenarios reflect your edits locally, but nothing is saved until
          you click "Save assumptions" below.
        </p>
      )}

      {fields && (
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {(
            [
              ["price_per_customer_usd", "Price / customer", price],
              ["initial_customers", "Initial customers", customers],
              ["monthly_growth_rate_pct", "Monthly growth (%)", growth],
              ["gross_margin_pct", "Gross margin (%)", margin],
            ] as const
          ).map(([key, label, value]) => {
            const field = fields[key];
            return (
              <div key={key} className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
                <div className="flex items-center justify-between">
                  <label htmlFor={`revenue-${key}`} className="text-xs text-ink-secondary">
                    {label}
                  </label>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] uppercase tracking-[0.08em] ${
                      field.assumption_source === "user_supplied"
                        ? "bg-signal-500/10 text-signal-300"
                        : "bg-warning-500/10 text-warning-400"
                    }`}
                  >
                    {field.assumption_source === "user_supplied" ? "Founder-supplied" : "Suggested default"}
                  </span>
                </div>
                <input
                  id={`revenue-${key}`}
                  type="number"
                  value={value}
                  onChange={(e) => setOverrides((prev) => ({ ...prev, [key]: Number(e.target.value) }))}
                  className="mt-1.5 w-full rounded-lg border border-white/10 bg-white/[0.02] px-2 py-1 text-sm text-ink-primary"
                />
                <p className="mt-1 text-[11px] text-ink-muted">{field.explanation}</p>
              </div>
            );
          })}
        </div>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={handleSave}
          disabled={!hasUnsavedEdits || saving}
          className="rounded-lg border border-signal-400/50 bg-signal-500/10 px-3 py-1 text-xs font-medium text-signal-200 transition hover:bg-signal-500/20 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save assumptions"}
        </button>
        {saveError && (
          <p role="alert" className="text-xs text-danger-400">
            {saveError} Your edits are still shown above — try saving again.
          </p>
        )}
      </div>

      {revenueEstimate.missing_assumptions.length > 0 && (
        <p className="mt-3 text-xs text-warning-400">
          Suggested defaults used for: {revenueEstimate.missing_assumptions.join(", ")}
        </p>
      )}
      <p className="mt-3 text-xs italic text-ink-muted">{revenueEstimate.disclaimer}</p>
    </div>
  );
}

export function AnalysisResult({ analysis, startupName }: { analysis: Analysis; startupName?: string | null }) {
  // A founder-submitted positioning correction (see PositioningCorrection above) or a revenue
  // assumption save updates this local override rather than mutating the `analysis` prop — the
  // parent page's own fetched copy is left alone, and a page reload re-fetches the persisted,
  // corrected result anyway.
  const [correctedAnalysis, setCorrectedAnalysis] = useState<Analysis | null>(null);
  const effective = correctedAnalysis ?? analysis;
  const { industry_prediction, funding_assessment, judge_summary, mentor_interpretation } = effective;

  if (analysis.status === "FAILED") {
    return (
      <div className="space-y-6">
        <p role="alert" className="rounded-xl border border-danger-500/30 bg-danger-500/10 p-4 text-danger-400">
          Analysis failed: {analysis.error_message}
        </p>
        <Section id="workflow-trace" title="Workflow Trace">
          <WorkflowTrace trace={analysis.workflow_trace} />
        </Section>
      </div>
    );
  }

  const dedupedTerms = industry_prediction?.explanation.available
    ? dedupeExplanationTerms(industry_prediction.explanation.terms)
    : [];
  const supporting = dedupedTerms.filter((t) => t.direction === "supports");
  const competing = dedupedTerms.filter((t) => t.direction === "opposes");
  const supportingWords = supporting.filter((t) => t.kind !== "char");
  const supportingFragments = supporting.filter((t) => t.kind === "char");

  const primaryDomain = judge_summary?.venture_positioning?.primary_domain ?? null;

  return (
    <div className="relative space-y-6 overflow-hidden">
      <img
        src={emblem}
        alt=""
        aria-hidden="true"
        className="pointer-events-none absolute -right-16 -top-10 -z-10 w-72 opacity-[0.05] sm:w-96"
      />

      {/* Founder Decision Studio — a guided journey, not a set of independent report cards. Every
          section below reads from data already computed by the deterministic backend (Phase 1-3);
          nothing here recomputes a score, a classification, or a verdict — this is presentation
          only. Null-safe throughout: absent entirely for an older stored analysis or a failed run. */}
      {mentor_interpretation && (
        <>
          {/* Section 1 */}
          <StartupSnapshot
            startupName={startupName ?? null}
            primaryDomain={primaryDomain}
            mentor={mentor_interpretation}
            fundingAssessment={funding_assessment}
            successPrediction={effective.success_prediction}
          >
            {judge_summary?.venture_positioning && (
              <PositioningCorrection
                analysisId={effective.id}
                currentPrimaryDomain={judge_summary.venture_positioning.primary_domain}
                onCorrected={setCorrectedAnalysis}
              />
            )}
          </StartupSnapshot>

          {/* Section 2 */}
          <WhyThisMatters mentor={mentor_interpretation} marketIntelligence={effective.market_intelligence} />

          {/* Section 3 */}
          <FounderDecisionPanel mentor={mentor_interpretation} />

          {/* Section 4 — folds in Phase 5 (Student 3)'s top "now"-urgency ranked action, if any,
              as one additional First Week task (deduped by title — see buildRoadmapBuckets). */}
          <RoadmapSection mentor={mentor_interpretation} rankedActions={effective.student3_outputs?.ranked_actions ?? []} />

          {/* Section 5 */}
          <ValidationPlanSection validationPlan={mentor_interpretation.validation_plan} />

          {/* Section 6 — reuses Phase 2 (Idea Expansion) + Phase 3 (Strategic Opportunity
              Discovery) outputs, plus Phase 5 (Student 3)'s growth strategy; see
              MarketExpansionSection for exactly which field comes from which source, so nothing
              is duplicated. */}
          <MarketExpansionSection
            ideaExpansion={effective.idea_expansion ?? null}
            strategicOpportunity={effective.strategic_opportunity ?? null}
            growthStrategy={effective.student3_outputs?.growth_strategy ?? []}
          />

          {/* Section 7 — reuses Phase 3's strategic_risks, combined with Phase 5 (Student 3)'s
              deterministic planning-risk checklist. */}
          {effective.strategic_opportunity && (
            <RiskDashboardSection
              risks={effective.strategic_opportunity.strategic_risks}
              planningRisks={effective.student3_outputs?.risks ?? []}
            />
          )}

          {/* Section 8 */}
          {funding_assessment && (
            <InvestmentReadinessSection
              fundingAssessment={funding_assessment}
              successPrediction={effective.success_prediction}
              founderGuidanceItems={mentor_interpretation.founder_guidance_items}
              businessModelSummary={mentor_interpretation.business_model}
            >
              {effective.revenue_estimate?.scenarios && (
                <RevenueEstimateBlock
                  analysisId={effective.id}
                  revenueEstimate={effective.revenue_estimate}
                  onSaved={setCorrectedAnalysis}
                />
              )}
            </InvestmentReadinessSection>
          )}

          {/* Section 9 */}
          <FounderMentorSection mentor={mentor_interpretation} />
        </>
      )}

      {/* Advanced: How We Got This — everything technical, collapsed by default, so the founder
          journey above never has to show a model detail, algorithmic explanation, or raw agent
          output to be understood. */}
      <details className="panel p-6 sm:p-8">
        <summary className="cursor-pointer select-none text-sm font-medium text-ink-secondary">
          Advanced: How We Got This — model detail, raw agent output, and methodology
        </summary>
        <div className="mt-6 space-y-6">
          {judge_summary?.venture_positioning && (
            <div>
              <h3 className="text-sm font-medium text-ink-primary">Venture Positioning Detail</h3>
              <p className="mt-2 text-sm text-ink-secondary">
                <span className="font-medium text-ink-primary">{judge_summary.venture_positioning.primary_domain}</span>
                {judge_summary.venture_positioning.is_low_confidence && (
                  <span className="ml-2 rounded-full border border-warning-500/30 bg-warning-500/10 px-2 py-0.5 text-xs text-warning-400">
                    Low confidence
                  </span>
                )}
              </p>
              {judge_summary.venture_positioning.secondary_domains.length > 0 && (
                <p className="mt-1 text-xs text-ink-muted">
                  Also relevant: {judge_summary.venture_positioning.secondary_domains.join(", ")}
                </p>
              )}
              {judge_summary.venture_positioning.deployment_sectors.length > 0 && (
                <p className="mt-1 text-xs text-ink-muted">
                  Deployment sectors: {judge_summary.venture_positioning.deployment_sectors.join(", ")}
                </p>
              )}
              {judge_summary.positioning_correction_rationale && (
                <p className="mt-2 rounded-lg border border-white/10 bg-white/[0.02] p-3 text-xs text-ink-muted">
                  {judge_summary.positioning_correction_rationale}
                </p>
              )}
              {judge_summary.gemini_rationale && (
                <p className="mt-2 text-xs italic text-ink-muted">
                  Gemini's advisory rationale (display-only, never a decision input): {judge_summary.gemini_rationale}
                </p>
              )}
              {(effective.positioning_correction_history ?? []).length > 0 && (
                <details className="mt-3 text-xs text-ink-muted">
                  <summary className="cursor-pointer select-none">
                    Correction history ({(effective.positioning_correction_history ?? []).length})
                  </summary>
                  <ul className="mt-2 space-y-1">
                    {(effective.positioning_correction_history ?? []).map((h, i) => (
                      <li key={i}>
                        {new Date(h.corrected_at).toLocaleString()}: corrected to "{h.override.primary_domain}" (was "
                        {h.previous_positioning?.primary_domain ?? "unknown"}")
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </div>
          )}

          {industry_prediction && (
            <div>
              <h3 className="text-sm font-medium text-ink-primary">Industry Classification Detail</h3>
              <p className="mt-2 text-sm">
                <span className="font-medium capitalize text-ink-primary">{industry_prediction.predicted_industry}</span>{" "}
                <span className="text-ink-muted">
                  ({(industry_prediction.confidence * 100).toFixed(0)}% confidence, model{" "}
                  {industry_prediction.model_version})
                </span>
              </p>
              {industry_prediction.is_uncertain && (
                <p className="mt-2 rounded-lg border border-warning-500/30 bg-warning-500/10 p-3 text-sm text-warning-400">
                  Uncertain classification — treat this as a hypothesis, not a settled fact.
                  {industry_prediction.uncertainty_reasons?.map((reason) => (
                    <span key={reason} className="mt-1 block text-xs text-warning-400/80">
                      {reason}
                    </span>
                  ))}
                </p>
              )}
              {industry_prediction.alternatives.length > 0 && (
                <div className="mt-3">
                  <h4 className="text-xs font-medium text-ink-secondary">Alternative signals</h4>
                  <ul className="mt-2 space-y-2">
                    {industry_prediction.alternatives.map((alt) => (
                      <ConfidenceBar key={alt.industry} label={alt.industry} confidence={alt.confidence} />
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {funding_assessment && (
            <div>
              <h3 className="text-sm font-medium text-ink-primary">Evidence Matrix</h3>
              <div className="mt-2 space-y-3">
                {funding_assessment.breakdown.map((item) => (
                  <div key={item.dimension}>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-ink-secondary">{item.label}</span>
                      <span className="text-xs text-ink-muted">
                        {item.state === "not_applicable" ? "N/A" : `${item.raw_score}/${item.max_score}`} ·{" "}
                        {item.scale_description}
                      </span>
                    </div>
                    <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-white/5">
                      <span
                        className={`block h-full rounded-full ${
                          item.raw_score === item.max_score && item.state === "confirmed_positive"
                            ? "bg-gradient-to-r from-gold-500 to-gold-400"
                            : item.state === "confirmed_negative"
                              ? "bg-danger-500/60"
                              : "bg-gradient-to-r from-signal-500 to-current-400"
                        }`}
                        style={{ width: `${item.raw_score ? (item.raw_score / item.max_score) * 100 : 0}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {industry_prediction?.explanation.available && (
            <div>
              <h3 className="text-sm font-medium text-ink-primary">Explainability</h3>
              <p className="mt-2 text-xs text-ink-muted">Why the model chose "{industry_prediction.predicted_industry}":</p>

              {supportingWords.length > 0 && (
                <div className="mt-3">
                  <h4 className="text-xs font-semibold uppercase tracking-[0.1em] text-success-400">Supporting terms</h4>
                  <ul className="mt-2 flex flex-wrap gap-2">
                    {supportingWords.map((t, idx) => (
                      <li
                        key={`${t.term}-${idx}`}
                        className="rounded-full border border-success-500/30 bg-success-500/10 px-3 py-1 text-xs text-success-400"
                      >
                        {t.term}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {supportingFragments.length > 0 && (
                <div className="mt-3">
                  <h4 className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-muted">Letter-pattern evidence</h4>
                  <ul className="mt-2 flex flex-wrap gap-2">
                    {supportingFragments.map((t, idx) => (
                      <li
                        key={`${t.term}-${idx}`}
                        title="A letter pattern (subword fragment), not a whole word"
                        className="rounded-full border border-dashed border-success-500/30 bg-success-500/5 px-3 py-1 text-xs text-success-400/80"
                      >
                        {t.term}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {competing.length > 0 && (
                <div className="mt-3">
                  <h4 className="text-xs font-semibold uppercase tracking-[0.1em] text-danger-400">Competing-domain evidence</h4>
                  <ul className="mt-2 flex flex-wrap gap-2">
                    {competing.map((t, idx) => (
                      <li
                        key={`${t.term}-${idx}`}
                        className={`rounded-full border px-3 py-1 text-xs text-danger-400 ${
                          t.kind === "char" ? "border-dashed border-danger-500/30 bg-danger-500/5" : "border-danger-500/30 bg-danger-500/10"
                        }`}
                      >
                        {t.term}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <p className="mt-3 text-xs text-ink-muted">
                Exact linear-coefficient × TF-IDF contributions for terms present in this input — not
                SHAP, not a generic keyword list, and not causal proof. Dashed chips are letter
                patterns (character n-gram fragments), not whole words.
              </p>
            </div>
          )}

          {(industry_prediction || effective.success_prediction) && (
            <div>
              <h3 className="text-sm font-medium text-ink-primary">Model Evidence</h3>
              <div className="mt-2 grid grid-cols-1 gap-4 sm:grid-cols-2">
                {industry_prediction && (
                  <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-muted">
                      Industry classifier · {industry_prediction.model_version}
                    </p>
                    <p className="mt-2 text-sm text-ink-secondary">
                      Primary: <span className="capitalize text-ink-primary">{industry_prediction.primary_industry ?? industry_prediction.predicted_industry}</span>
                      {industry_prediction.primary_confidence != null && (
                        <span className="text-ink-muted"> ({(industry_prediction.primary_confidence * 100).toFixed(0)}%)</span>
                      )}
                    </p>
                    {industry_prediction.secondary_industry && (
                      <p className="text-sm text-ink-secondary">
                        Secondary: <span className="capitalize text-ink-primary">{industry_prediction.secondary_industry}</span>
                        {industry_prediction.secondary_confidence != null && (
                          <span className="text-ink-muted"> ({(industry_prediction.secondary_confidence * 100).toFixed(0)}%)</span>
                        )}
                      </p>
                    )}
                    {industry_prediction.is_low_confidence && (
                      <p className="mt-2 rounded-lg border border-warning-500/30 bg-warning-500/10 p-2 text-xs text-warning-400">
                        Below the abstention threshold ({((industry_prediction.abstention_threshold ?? 0) * 100).toFixed(0)}%)
                        {industry_prediction.abstention_reason ? ` — ${industry_prediction.abstention_reason}` : ""}. Treat this
                        prediction as insufficiently confident rather than a settled classification.
                      </p>
                    )}
                  </div>
                )}
                {effective.success_prediction && (
                  <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-muted">
                      Success predictor · {effective.success_prediction.model_version}
                    </p>
                    <p className="mt-2 text-sm text-ink-secondary">
                      Predicted label: <span className="text-ink-primary">{effective.success_prediction.predicted_label}</span>{" "}
                      ({(effective.success_prediction.success_probability * 100).toFixed(0)}% probability)
                    </p>
                    <p className="mt-1 text-sm text-ink-secondary">
                      Calibration: <span className="text-ink-primary">{effective.success_prediction.calibration_method ?? "unknown"}</span>
                      {" · "}Dataset: <span className="text-ink-primary">{effective.success_prediction.dataset_version}</span>
                    </p>
                    {effective.success_prediction.missing_features.length > 0 && (
                      <p className="mt-2 text-xs text-ink-muted">
                        Imputed (not supplied): {effective.success_prediction.missing_features.join(", ")}
                      </p>
                    )}
                    {effective.success_prediction.top_global_features && effective.success_prediction.top_global_features.length > 0 && (
                      <p className="mt-2 text-xs text-ink-muted">
                        Most influential features (model-wide): {effective.success_prediction.top_global_features.map((f) => f.replace(/_/g, " ")).join(", ")}
                      </p>
                    )}
                    <p className="mt-2 text-xs italic text-ink-muted">{effective.success_prediction.disclaimer}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {judge_summary?.llm_narrative && (
            <div className="rounded-xl border border-current-500/20 bg-current-500/5 p-4">
              <p className="text-xs font-medium uppercase tracking-[0.15em] text-current-400">
                AI-Generated Narrative (Gemini) — supplementary commentary only
              </p>
              <p className="mt-2 text-sm text-ink-secondary">{judge_summary.llm_narrative.executive_summary}</p>
              {judge_summary.llm_narrative.strategic_observations.length > 0 && (
                <ul className="mt-2 list-inside list-disc text-sm text-ink-muted">
                  {judge_summary.llm_narrative.strategic_observations.map((o) => (
                    <li key={o}>{o}</li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {judge_summary && (
            <div>
              <h3 className="text-sm font-medium text-ink-primary">Technical Assessment</h3>
              <p className="mt-2 text-sm text-ink-secondary">{judge_summary.overall_assessment}</p>
              {judge_summary.strengths.length > 0 && (
                <div className="mt-3">
                  <h4 className="text-xs font-medium text-success-400">All strengths (raw rubric)</h4>
                  <ul className="mt-1 list-inside list-disc text-xs text-ink-muted">
                    {judge_summary.strengths.map((s) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ul>
                </div>
              )}
              {judge_summary.weaknesses.length > 0 && (
                <div className="mt-3">
                  <h4 className="text-xs font-medium text-danger-400">All weaknesses (raw rubric, deprecated field)</h4>
                  <ul className="mt-1 list-inside list-disc text-xs text-ink-muted">
                    {judge_summary.weaknesses.map((w) => (
                      <li key={w}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {effective.customer_personas && (
            <div>
              <h3 className="text-sm font-medium text-ink-primary">Customer Personas Detail</h3>
              <div className="mt-2 space-y-2">
                {effective.customer_personas.personas.map((persona) => (
                  <div key={persona.persona_name} className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
                    <p className="text-sm font-medium text-ink-primary">{persona.persona_name}</p>
                    <p className="mt-1 text-xs text-ink-secondary">{persona.role_or_context} · {persona.goal}</p>
                    {persona.assumptions_requiring_validation.length > 0 && (
                      <p className="mt-1 text-xs text-warning-400">
                        Requires validation: {persona.assumptions_requiring_validation.join(", ")}
                      </p>
                    )}
                  </div>
                ))}
              </div>
              <p className="mt-2 text-xs italic text-ink-muted">{effective.customer_personas.disclaimer}</p>
            </div>
          )}

          {effective.competitor_analysis && (
            <div>
              <h3 className="text-sm font-medium text-ink-primary">Competitor Analysis Detail</h3>
              <p className="mt-2 text-xs italic text-ink-muted">{effective.competitor_analysis.disclaimer}</p>
            </div>
          )}

          {effective.student3_outputs && (
            <div>
              <h3 className="text-sm font-medium text-ink-primary">Growth &amp; Pitch Planning Detail (Phase 5)</h3>
              {effective.student3_outputs.innovation_opportunities.length > 0 && (
                <div className="mt-2">
                  <h4 className="text-xs font-medium text-ink-secondary">Innovation Opportunities</h4>
                  <ul className="mt-1 space-y-1.5">
                    {effective.student3_outputs.innovation_opportunities.map((item) => (
                      <li key={item.opportunity} className="text-xs text-ink-muted">
                        <span className="text-ink-primary">{item.opportunity}</span> — {item.rationale}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <div className="mt-3">
                <h4 className="text-xs font-medium text-ink-secondary">Pitch Deck Outline</h4>
                <ul className="mt-1 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                  {effective.student3_outputs.pitch_deck.map((slide) => (
                    <li key={slide.title} className="rounded-lg border border-white/10 bg-white/[0.02] p-2 text-xs">
                      <span className="text-ink-primary">{slide.title}</span>{" "}
                      <span className="text-ink-muted">({slide.evidence_status})</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          <div>
            <h3 className="text-sm font-medium text-ink-primary">Analysis Steps</h3>
            <div className="mt-2">
              <WorkflowTrace trace={effective.workflow_trace} />
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-ink-primary">Methodology and Limitations</h3>
            <ul className="mt-2 space-y-1 text-xs text-ink-muted">
              <li>
                Industry model: {effective.industry_model_version ?? "n/a"} · Funding rubric:{" "}
                {effective.funding_rubric_version ?? "n/a"}
              </li>
              <li>
                The industry classifier is trained on real Y Combinator company descriptions (see
                ml/DATASETS.md) — real, honest evaluation metrics, not a guarantee for every input.
              </li>
              <li>Funding readiness is a deterministic, hand-designed rubric — not a trained probability.</li>
              <li>
                The Historical Pattern Signal is trained only on companies that had already raised
                funding — treat it as a loose historical comparison, never a prediction of this
                idea's outcome.
              </li>
            </ul>
          </div>
        </div>
      </details>
    </div>
  );
}
