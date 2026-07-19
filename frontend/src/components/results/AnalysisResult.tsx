import type { Analysis, ExplanationTerm, JudgeSummary } from "../../types/api";
import emblem from "../../assets/ventureforge-emblem.webp";
import { ConfidenceBar } from "../visualizations/ConfidenceBar";
import { ReadinessReactor } from "../visualizations/ReadinessReactor";
import { Section } from "./Section";
import { WorkflowTrace } from "./WorkflowTrace";
import { Student3Results } from "./Student3Results";

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

const CONFIDENCE_STYLES: Record<string, string> = {
  high: "border-success-500/40 bg-success-500/10 text-success-400",
  medium: "border-signal-500/40 bg-signal-500/10 text-signal-400",
  low: "border-danger-500/40 bg-danger-500/10 text-danger-400",
};

/** Plain-language verdict headline, derived only from real fields already computed by the
 * backend (funding level + judge confidence) — a presentation template, not a new data source. */
function verdictHeadline(fundingLevel: string, confidenceLevel: string): string {
  if (fundingLevel === "ready" && confidenceLevel !== "low") {
    return "Strong candidate — investor-ready signals present.";
  }
  if (fundingLevel === "early_stage") {
    return "Early-stage idea — significant validation still needed.";
  }
  return "Promising concept, but not yet investor-ready.";
}

function decisionFields(judge: JudgeSummary) {
  const opportunity = judge.strengths[0] ?? "Not yet demonstrated — no strengths identified from the current inputs.";
  const risk =
    judge.weaknesses[0] ??
    (judge.missing_evidence[0] ? `Insufficient evidence: ${judge.missing_evidence[0]}.` : "No major risk flagged from the current inputs.");
  const move = judge.next_actions[0] ?? "Answer more of the funding-readiness questions to unlock a specific recommendation.";
  return { opportunity, risk, move };
}

export function AnalysisResult({ analysis }: { analysis: Analysis }) {
  const { industry_prediction, funding_assessment, judge_summary, student3_outputs } = analysis;

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

  return (
    <div className="relative space-y-6 overflow-hidden">
      <img
        src={emblem}
        alt=""
        aria-hidden="true"
        className="pointer-events-none absolute -right-16 -top-10 -z-10 w-72 opacity-[0.05] sm:w-96"
      />

      {/* Executive Dashboard */}
      <section className="panel panel-glow p-6 sm:p-8">
        <p className="text-xs font-medium uppercase tracking-[0.15em] text-ink-muted">Executive Dashboard</p>
        <div className="mt-4 flex flex-wrap items-baseline gap-x-10 gap-y-4">
          {industry_prediction && (
            <div>
              <p className="text-xs text-ink-muted">Industry</p>
              <p className="text-display text-2xl capitalize">Primary: {industry_prediction.predicted_industry}</p>
            </div>
          )}
          {funding_assessment && (
            <div>
              <p className="text-xs text-ink-muted">Readiness</p>
              <p className="text-display text-2xl">
                <span>{funding_assessment.overall_score}/100</span>{" "}
                <span className="text-base font-normal capitalize text-ink-secondary">
                  ({funding_assessment.level.replace("_", " ")})
                </span>
              </p>
            </div>
          )}
          {judge_summary && (
            <div>
              <p className="text-xs text-ink-muted">Judge confidence</p>
              <span
                className={`mt-1 inline-block rounded-full border px-3 py-0.5 text-sm capitalize ${CONFIDENCE_STYLES[judge_summary.confidence_level]}`}
              >
                {judge_summary.confidence_level}
              </span>
            </div>
          )}
        </div>
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Industry Intelligence */}
        {industry_prediction && (
          <Section id="industry" title="Industry Intelligence" source="model">
            <p>
              <span className="font-medium capitalize text-ink-primary">{industry_prediction.predicted_industry}</span>{" "}
              <span className="text-ink-muted">
                ({(industry_prediction.confidence * 100).toFixed(0)}% confidence, model{" "}
                {industry_prediction.model_version})
              </span>
            </p>

            {industry_prediction.is_uncertain && (
              <p className="mt-3 rounded-lg border border-warning-500/30 bg-warning-500/10 p-3 text-sm text-warning-400">
                Uncertain classification — treat this as a hypothesis, not a settled fact.
                {industry_prediction.uncertainty_reasons?.map((reason) => (
                  <span key={reason} className="mt-1 block text-xs text-warning-400/80">
                    {reason}
                  </span>
                ))}
              </p>
            )}

            {industry_prediction.alternatives.length > 0 && (
              <div className="mt-4">
                <h3 className="text-sm font-medium text-ink-secondary">Alternative signals</h3>
                <ul className="mt-2 space-y-2">
                  {industry_prediction.alternatives.map((alt) => (
                    <ConfidenceBar key={alt.industry} label={alt.industry} confidence={alt.confidence} />
                  ))}
                </ul>
              </div>
            )}
          </Section>
        )}

        {/* Funding Readiness Reactor */}
        {funding_assessment && (
          <Section id="funding" title="Funding Readiness Reactor" source="deterministic">
            <ReadinessReactor score={funding_assessment.overall_score} level={funding_assessment.level} />
            <p className="mt-4 text-xs italic text-ink-muted">{funding_assessment.disclaimer}</p>
          </Section>
        )}
      </div>

      {/* Evidence Matrix */}
      {funding_assessment && (
        <Section id="evidence" title="Evidence Matrix" source="deterministic">
          <div className="space-y-3">
            {funding_assessment.breakdown.map((item) => (
              <div key={item.dimension}>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-ink-secondary">{item.label}</span>
                  <span className="text-xs text-ink-muted">
                    {item.raw_score}/{item.max_score} · {item.scale_description}
                  </span>
                </div>
                <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-white/5">
                  <span
                    className={`block h-full rounded-full ${
                      item.raw_score === item.max_score
                        ? "bg-gradient-to-r from-gold-500 to-gold-400"
                        : "bg-gradient-to-r from-signal-500 to-current-400"
                    }`}
                    style={{ width: `${(item.raw_score / item.max_score) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
          {funding_assessment.missing_evidence.length > 0 ? (
            <p className="mt-4 text-sm text-warning-400">
              Missing evidence: {funding_assessment.missing_evidence.join(", ")}
            </p>
          ) : (
            <p className="mt-4 text-sm text-success-400">Every readiness dimension was answered.</p>
          )}
          <p className="mt-1 text-xs text-ink-muted">
            Unanswered dimensions score 0 — no favorable assumption is made for missing data.
          </p>
        </Section>
      )}

      {/* Startup Success Prediction */}
      <Section id="success-prediction" title="Startup Success Prediction" source="model">
        {analysis.success_prediction ? (
          <div>
            <p className="text-lg font-medium capitalize text-ink-primary">
              {analysis.success_prediction.predicted_label}{" "}
              <span className="text-sm font-normal text-ink-muted">
                ({(analysis.success_prediction.success_probability * 100).toFixed(0)}% probability, model{" "}
                {analysis.success_prediction.model_version})
              </span>
            </p>
            {analysis.success_prediction.is_uncertain && (
              <p className="mt-3 rounded-lg border border-warning-500/30 bg-warning-500/10 p-3 text-sm text-warning-400">
                Uncertain estimate — treat as a hypothesis, not a settled fact.
                {analysis.success_prediction.uncertainty_reasons.map((reason) => (
                  <span key={reason} className="mt-1 block text-xs text-warning-400/80">
                    {reason}
                  </span>
                ))}
              </p>
            )}
            {analysis.success_prediction.missing_features.length > 0 && (
              <p className="mt-2 text-xs text-ink-muted">
                Imputed (not supplied): {analysis.success_prediction.missing_features.join(", ")}
              </p>
            )}
            {analysis.success_prediction.top_global_features && analysis.success_prediction.top_global_features.length > 0 && (
              <div className="mt-3">
                <h3 className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-muted">
                  Most influential features (model-wide)
                </h3>
                <ul className="mt-1 flex flex-wrap gap-2">
                  {analysis.success_prediction.top_global_features.map((f) => (
                    <li key={f} className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-xs text-ink-secondary">
                      {f.replace(/_/g, " ")}
                    </li>
                  ))}
                </ul>
                {analysis.success_prediction.explanation_note && (
                  <p className="mt-1.5 text-[11px] text-ink-muted">{analysis.success_prediction.explanation_note}</p>
                )}
              </div>
            )}
            <p className="mt-3 text-xs italic text-ink-muted">{analysis.success_prediction.disclaimer}</p>
          </div>
        ) : (
          <p className="text-sm text-ink-muted">
            Success prediction model unavailable for this run — no artifact was loaded on the server.
          </p>
        )}
      </Section>

      {/* Revenue Estimate */}
      <Section id="revenue-estimate" title="Revenue Estimate" source="deterministic">
        {analysis.revenue_estimate?.available && analysis.revenue_estimate.scenarios ? (
          <div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              {(["conservative", "base", "optimistic"] as const).map((key) => {
                const s = analysis.revenue_estimate!.scenarios![key];
                return (
                  <div key={key} className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-muted capitalize">{key}</p>
                    <p className="mt-1.5 text-lg text-display text-ink-primary">
                      ${s.annual_revenue_usd.toLocaleString()}
                    </p>
                    <p className="text-xs text-ink-muted">annual revenue (12mo)</p>
                    <p className="mt-1 text-xs text-ink-secondary">
                      ${s.annual_gross_profit_usd.toLocaleString()} gross profit
                    </p>
                  </div>
                );
              })}
            </div>
            {analysis.revenue_estimate.missing_assumptions.length > 0 && (
              <p className="mt-3 text-xs text-warning-400">
                Defaulted assumptions: {analysis.revenue_estimate.missing_assumptions.join(", ")}
              </p>
            )}
            <p className="mt-3 text-xs italic text-ink-muted">{analysis.revenue_estimate.disclaimer}</p>
          </div>
        ) : (
          <p className="text-sm text-ink-muted">
            No revenue range shown — {analysis.revenue_estimate?.disclaimer ??
              "revenue assumptions were not submitted."}
          </p>
        )}
      </Section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Market Intelligence */}
        {analysis.market_intelligence && (
          <Section id="market-intelligence" title="Market Intelligence" source="deterministic">
            <p className="text-sm text-ink-secondary">{analysis.market_intelligence.market_summary}</p>
            {analysis.market_intelligence.opportunity_drivers.length > 0 && (
              <div className="mt-3">
                <h3 className="text-xs font-semibold uppercase tracking-[0.1em] text-success-400">Opportunity drivers</h3>
                <ul className="mt-1 list-inside list-disc text-sm text-ink-secondary">
                  {analysis.market_intelligence.opportunity_drivers.map((d) => (
                    <li key={d}>{d}</li>
                  ))}
                </ul>
              </div>
            )}
            {analysis.market_intelligence.constraints.length > 0 && (
              <div className="mt-3">
                <h3 className="text-xs font-semibold uppercase tracking-[0.1em] text-danger-400">Constraints</h3>
                <ul className="mt-1 list-inside list-disc text-sm text-ink-secondary">
                  {analysis.market_intelligence.constraints.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              </div>
            )}
            {analysis.market_intelligence.evidence_gaps.length > 0 && (
              <p className="mt-3 text-xs text-warning-400">
                Evidence gaps: {analysis.market_intelligence.evidence_gaps.join(", ")}
              </p>
            )}
            <p className="mt-3 text-xs italic text-ink-muted">{analysis.market_intelligence.disclaimer}</p>
          </Section>
        )}

        {/* Competitor Analysis */}
        {analysis.competitor_analysis && (
          <Section id="competitor-analysis" title="Competitor Analysis" source="deterministic">
            <ul className="space-y-2">
              {analysis.competitor_analysis.entries.map((entry) => (
                <li key={entry.competitor_or_alternative} className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
                  <p className="text-sm font-medium text-ink-primary">{entry.competitor_or_alternative}</p>
                  <p className="text-xs text-ink-muted">{entry.category}</p>
                </li>
              ))}
            </ul>
            <p className="mt-3 text-xs italic text-ink-muted">{analysis.competitor_analysis.disclaimer}</p>
          </Section>
        )}
      </div>

      {/* Customer Personas */}
      {analysis.customer_personas && (
        <Section id="customer-personas" title="Customer Personas" source="deterministic">
          {analysis.customer_personas.personas.map((persona) => (
            <div key={persona.persona_name} className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
              <p className="text-sm font-medium text-ink-primary">{persona.persona_name}</p>
              <dl className="mt-2 grid grid-cols-1 gap-2 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-xs text-ink-muted">Role/context</dt>
                  <dd className="text-ink-secondary">{persona.role_or_context}</dd>
                </div>
                <div>
                  <dt className="text-xs text-ink-muted">Goal</dt>
                  <dd className="text-ink-secondary">{persona.goal}</dd>
                </div>
              </dl>
              {persona.assumptions_requiring_validation.length > 0 && (
                <p className="mt-2 text-xs text-warning-400">
                  Requires validation: {persona.assumptions_requiring_validation.join(", ")}
                </p>
              )}
            </div>
          ))}
          <p className="mt-3 text-xs italic text-ink-muted">{analysis.customer_personas.disclaimer}</p>
        </Section>
      )}

      {/* Business Model */}
      {analysis.business_model && (
        <Section id="business-model" title="Business Model" source="deterministic">
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {(
              [
                ["Value proposition", analysis.business_model.value_proposition],
                ["Customer segments", analysis.business_model.customer_segments],
                ["Revenue streams", analysis.business_model.revenue_streams],
                ["Unit economics readiness", analysis.business_model.unit_economics_readiness],
              ] as const
            ).map(([label, val]) => (
              <div key={label}>
                <dt className="text-xs uppercase tracking-[0.1em] text-ink-muted">{label}</dt>
                <dd className="mt-1 text-sm text-ink-secondary">{val}</dd>
              </div>
            ))}
          </dl>
          {analysis.business_model.recommended_experiments.length > 0 && (
            <div className="mt-4">
              <h3 className="text-xs font-semibold uppercase tracking-[0.1em] text-signal-400">Recommended experiments</h3>
              <ul className="mt-1 list-inside list-disc text-sm text-ink-secondary">
                {analysis.business_model.recommended_experiments.map((e) => (
                  <li key={e}>{e}</li>
                ))}
              </ul>
            </div>
          )}
          <p className="mt-3 text-xs italic text-ink-muted">{analysis.business_model.disclaimer}</p>
        </Section>
      )}

      {/* Explainability */}
      {industry_prediction?.explanation.available && (
        <Section id="explainability" title="Explainability" source="model">
          <p className="text-xs text-ink-muted">Why the model chose "{industry_prediction.predicted_industry}":</p>

          {supportingWords.length > 0 && (
            <div className="mt-3">
              <h3 className="text-xs font-semibold uppercase tracking-[0.1em] text-success-400">Supporting terms</h3>
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
              <h3 className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-muted">
                Letter-pattern evidence
              </h3>
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
              <h3 className="text-xs font-semibold uppercase tracking-[0.1em] text-danger-400">
                Competing-domain evidence
              </h3>
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

          <details className="mt-4 rounded-lg border border-white/5 bg-white/[0.02] p-3 text-xs text-ink-muted">
            <summary className="cursor-pointer select-none font-medium text-ink-secondary">Methodology</summary>
            <p className="mt-2">
              Exact linear-coefficient × TF-IDF contributions for terms present in this input — not
              SHAP, not a generic keyword list, and not causal proof. Dashed chips are letter
              patterns (character n-gram fragments), not whole words.
            </p>
          </details>
        </Section>
      )}

      {/* Model Evidence — compact, honest summary of what each model knows, doesn't know, and how confident it is */}
      {(industry_prediction || analysis.success_prediction) && (
        <Section id="model-evidence" title="Model Evidence" source="model">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
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
            {analysis.success_prediction && (
              <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
                <p className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-muted">
                  Success predictor · {analysis.success_prediction.model_version}
                </p>
                <p className="mt-2 text-sm text-ink-secondary">
                  Calibration: <span className="text-ink-primary">{analysis.success_prediction.calibration_method ?? "unknown"}</span>
                  {" · "}Dataset: <span className="text-ink-primary">{analysis.success_prediction.dataset_version}</span>
                </p>
                {analysis.success_prediction.recommended_threshold_info && (
                  <p className="mt-2 text-xs text-ink-muted">
                    Operating threshold {analysis.success_prediction.recommended_threshold_info.threshold}:{" "}
                    {analysis.success_prediction.recommended_threshold_info.justification}
                  </p>
                )}
              </div>
            )}
          </div>
          <p className="mt-3 text-xs italic text-ink-muted">
            Evidence is reported to show what each model actually knows and how it was validated — not to imply certainty
            beyond what the underlying data supports.
          </p>
        </Section>
      )}

      {/* Judge Verdict */}
      {judge_summary && funding_assessment && (
        <Section id="judge" title="Judge Verdict" source="judge">
          {(() => {
            const { opportunity, risk, move } = decisionFields(judge_summary);
            return (
              <div className="space-y-4">
                <p className="text-lg font-medium text-ink-primary">
                  {verdictHeadline(funding_assessment.level, judge_summary.confidence_level)}
                </p>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div className="rounded-xl border border-success-500/20 bg-success-500/5 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.1em] text-success-400">Opportunity</p>
                    <p className="mt-1.5 text-sm text-ink-secondary">{opportunity}</p>
                  </div>
                  <div className="rounded-xl border border-danger-500/20 bg-danger-500/5 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.1em] text-danger-400">Primary risk</p>
                    <p className="mt-1.5 text-sm text-ink-secondary">{risk}</p>
                  </div>
                  <div className="rounded-xl border border-signal-500/20 bg-signal-500/5 p-4">
                    <p className="text-xs font-semibold uppercase tracking-[0.1em] text-signal-400">Immediate move</p>
                    <p className="mt-1.5 text-sm text-ink-secondary">{move}</p>
                  </div>
                </div>
              </div>
            );
          })()}

          {judge_summary.llm_narrative && (
            <div className="mt-6 rounded-xl border border-current-500/20 bg-current-500/5 p-4">
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
              <p className="mt-2 text-xs text-ink-muted">
                Generated commentary only — the industry prediction, confidence, and funding score
                above are always computed deterministically and are never influenced by this text.
              </p>
            </div>
          )}

          <details className="mt-6 rounded-lg border border-white/5 bg-white/[0.02] p-3 text-xs text-ink-muted">
            <summary className="cursor-pointer select-none font-medium text-ink-secondary">
              Technical assessment
            </summary>
            <p className="mt-2 text-ink-secondary">{judge_summary.overall_assessment}</p>
            {judge_summary.strengths.length > 0 && (
              <div className="mt-3">
                <h3 className="text-xs font-medium text-success-400">All strengths</h3>
                <ul className="mt-1 list-inside list-disc">
                  {judge_summary.strengths.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </div>
            )}
            {judge_summary.weaknesses.length > 0 && (
              <div className="mt-3">
                <h3 className="text-xs font-medium text-danger-400">All weaknesses</h3>
                <ul className="mt-1 list-inside list-disc">
                  {judge_summary.weaknesses.map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              </div>
            )}
          </details>
        </Section>
      )}

      {/* Strategic Next Moves */}
      {judge_summary && judge_summary.next_actions.length > 0 && (
        <Section id="next-moves" title="Strategic Next Moves" source="judge">
          <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {judge_summary.next_actions.map((a) => (
              <li key={a} className="rounded-xl border border-white/10 bg-white/[0.02] p-4 text-sm text-ink-secondary">
                {a}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {student3_outputs && <Student3Results outputs={student3_outputs} />}

      {/* Workflow Timeline */}
      <Section id="workflow-trace" title="Workflow Timeline" source="deterministic">
        <WorkflowTrace trace={analysis.workflow_trace} />
      </Section>

      {/* Methodology and Limitations */}
      <Section id="methodology" title="Methodology and Limitations">
        <ul className="space-y-1 text-xs text-ink-muted">
          <li>
            Industry model: {analysis.industry_model_version ?? "n/a"} · Funding rubric:{" "}
            {analysis.funding_rubric_version ?? "n/a"}
          </li>
          <li>
            The industry classifier is trained on real Y Combinator company descriptions (see
            ml/DATASETS.md) — real, honest evaluation metrics, not a guarantee for every input.
          </li>
          <li>Funding readiness is a deterministic, hand-designed rubric — not a trained probability.</li>
        </ul>
      </Section>
    </div>
  );
}
