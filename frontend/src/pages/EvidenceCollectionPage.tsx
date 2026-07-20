import { motion } from "framer-motion";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useNewAnalysis } from "../context/NewAnalysisContext";
import { MagneticButton } from "../components/motion/MagneticButton";
import { createStartup } from "../services/api";
import type { FundingAnswers } from "../types/api";

/** Mirrors the 8 real dimensions in backend/app/ml/funding_readiness.py exactly — labels, help
 * text, and evidence-quality option text are the same rubric the backend scores, just presented
 * as an expandable category per dimension instead of a bare select (see the reference layout).
 * Each dimension now exposes all four explicit evidence states (see EvidenceState in
 * backend/app/ml/funding_readiness.py): the three `evidenceOptions` below all resolve to either
 * `confirmed_negative` (no evidence) or `confirmed_positive` (some/strong evidence, severity 1/2)
 * — "Not sure yet" and "Not applicable" are separate, always-available choices, never inferred
 * from silence. */
const DIMENSIONS: { key: keyof FundingAnswers; label: string; tip: string; options: string[] }[] = [
  {
    key: "market_size_evidence",
    label: "Market Opportunity",
    tip: "A sourced TAM/SAM/SOM estimate scores highest — a guessed billion-dollar figure does not.",
    options: ["No sizing provided", "Rough estimate", "Sourced TAM/SAM/SOM"],
  },
  {
    key: "customer_pain_evidence",
    label: "Target Customers",
    tip: "Interviews, surveys, or support tickets documenting the pain — not just a hunch.",
    options: ["No evidence provided", "Anecdotal evidence", "Documented evidence (interviews/data)"],
  },
  {
    key: "product_maturity",
    label: "Solution & Product",
    tip: "What a real user could try today.",
    options: ["Idea only", "Prototype/MVP", "Live product with users"],
  },
  {
    key: "traction",
    label: "Traction & Validation",
    tip: "Real usage or paying customers, not projected ones.",
    options: ["No users/customers", "Early pilot users", "Paying customers / recurring usage"],
  },
  {
    key: "revenue_model_clarity",
    label: "Pricing & Revenue",
    tip: "Pricing and unit economics, not just \"we'll figure it out.\"",
    options: ["Not defined", "Roughly defined", "Clear pricing and unit economics"],
  },
  {
    key: "problem_clarity",
    label: "Problem Clarity",
    tip: "Can you state who has this problem and what it costs them in one sentence?",
    options: ["Problem not clearly stated", "Problem stated but broad", "Specific, well-defined problem"],
  },
  {
    key: "team_completeness",
    label: "Team & Execution",
    tip: "Does the founding team cover the core skills this venture needs?",
    options: ["Solo, no key skills covered", "Partial team", "Founding team covers core skills"],
  },
  {
    key: "competitive_differentiation",
    label: "What Makes You Different",
    tip: "How this differs from the 2-3 closest alternatives — the clearest lens on competitive risk.",
    options: ["No differentiation stated", "Some differentiation", "Clear, defensible differentiation"],
  },
];

const MAX_PER_DIMENSION = 2;
const RADIUS = 46;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

function StrengthRing({ percent }: { percent: number }) {
  const offset = CIRCUMFERENCE * (1 - percent / 100);
  const color = percent >= 70 ? "#ffd166" : percent >= 40 ? "#168bff" : "#7c2cff";
  const label = percent >= 70 ? "Excellent" : percent >= 40 ? "Good" : "Needs Detail";

  return (
    <div className="relative flex h-32 w-32 items-center justify-center">
      <svg width="128" height="128" viewBox="0 0 128 128">
        <circle cx="64" cy="64" r={RADIUS} fill="none" stroke="rgba(245,247,255,0.08)" strokeWidth="8" />
        <circle
          cx="64"
          cy="64"
          r={RADIUS}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={offset}
          transform="rotate(-90 64 64)"
          className="transition-[stroke-dashoffset,stroke] duration-500 ease-out"
          style={{ filter: `drop-shadow(0 0 10px ${color}80)` }}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-display text-2xl text-ink-primary">{percent}%</span>
        <span className="text-[10px] uppercase tracking-[0.1em] text-ink-muted">{label}</span>
      </div>
    </div>
  );
}

export function EvidenceCollectionPage() {
  const navigate = useNavigate();
  const {
    idea,
    fundingAnswers,
    updateFunding,
    companyMetrics,
    revenueAssumptions,
    marketEvidence,
    updateCompanyMetrics,
    updateRevenueAssumptions,
    updateMarketEvidence,
    buildDescription,
    reset,
  } = useNewAnalysis();
  const [expanded, setExpanded] = useState<string | null>(DIMENSIONS[0].key);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [competitorsInput, setCompetitorsInput] = useState(
    (marketEvidence.known_competitors ?? []).join(", "),
  );

  // Mirrors backend/app/ml/funding_readiness.py's weight-renormalization: a dimension marked
  // "not_applicable" is excluded from both the numerator and the denominator, so opting it out
  // never lowers the achievable strength percentage.
  const strengthPercent = useMemo(() => {
    const applicable = DIMENSIONS.filter((d) => fundingAnswers[d.key]?.state !== "not_applicable");
    if (applicable.length === 0) return 0;
    const total = applicable.reduce((sum, d) => {
      const entry = fundingAnswers[d.key];
      return sum + (entry?.state === "confirmed_positive" ? (entry.severity ?? 1) : 0);
    }, 0);
    return Math.round((total / (applicable.length * MAX_PER_DIMENSION)) * 100);
  }, [fundingAnswers]);

  const answeredKeys = DIMENSIONS.filter((d) => {
    const state = fundingAnswers[d.key]?.state;
    return state === "confirmed_positive" || state === "confirmed_negative" || state === "not_applicable";
  });

  async function handleSubmit() {
    if (!idea.name.trim() || buildDescription().length < 10) {
      setError("Your idea details look incomplete — go back to Idea Submission first.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const startup = await createStartup({
        name: idea.name,
        description: buildDescription(),
        funding_answers: fundingAnswers,
        company_metrics: companyMetrics,
        revenue_assumptions: revenueAssumptions,
        market_evidence: marketEvidence,
      });
      reset();
      navigate(`/startups/${startup.id}/status`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not submit this venture for analysis.");
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-14 sm:px-10">
      <p className="text-xs font-medium uppercase tracking-[0.25em] text-signal-400">Evidence Collection</p>
      <h1 className="mt-2 text-display text-3xl">Strengthen your analysis with evidence</h1>
      <p className="mt-2 max-w-xl text-ink-secondary">
        Help our AI agents analyze your venture more accurately. "Not sure yet" is never treated
        as a weakness — it becomes a starting hypothesis and a concrete validation task instead.
        Only an explicit "no evidence yet" answer is scored as a real weakness.
      </p>

      <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-[1fr_18rem]">
        <div className="space-y-3">
          {DIMENSIONS.map((d) => {
            const entry = fundingAnswers[d.key];
            const state = entry?.state ?? "not_sure_yet";
            const severity = entry?.severity ?? 0;
            const isOpen = expanded === d.key;
            const barWidth = state === "confirmed_positive" ? (severity / MAX_PER_DIMENSION) * 100 : 0;
            const statusLabel =
              state === "confirmed_positive"
                ? `${severity}/${MAX_PER_DIMENSION}`
                : state === "confirmed_negative"
                  ? "None yet"
                  : state === "not_applicable"
                    ? "N/A"
                    : "Not sure yet";
            return (
              <div key={d.key} className="panel hover-lift overflow-hidden">
                <button
                  type="button"
                  onClick={() => setExpanded(isOpen ? null : d.key)}
                  className="flex w-full items-center justify-between px-5 py-4 text-left"
                  aria-expanded={isOpen}
                >
                  <span className="text-sm font-medium text-ink-primary">{d.label}</span>
                  <div className="flex items-center gap-3">
                    <div className="h-1.5 w-24 overflow-hidden rounded-full bg-white/5">
                      <div
                        className={`h-full rounded-full transition-[width] duration-500 ${
                          state === "confirmed_positive" && severity === 2
                            ? "bg-gold-400"
                            : state === "confirmed_positive"
                              ? "bg-signal-500"
                              : state === "confirmed_negative"
                                ? "bg-danger-500/60"
                                : "bg-white/10"
                        }`}
                        style={{ width: `${barWidth}%` }}
                      />
                    </div>
                    <span className="w-20 text-right text-xs text-ink-muted">{statusLabel}</span>
                  </div>
                </button>
                {isOpen && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    transition={{ duration: 0.25 }}
                    className="border-t border-white/5 px-5 py-4"
                  >
                    <p className="text-xs text-ink-muted">{d.tip}</p>
                    <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3">
                      {d.options.map((opt, idx) => {
                        const optionIsActive = state === "confirmed_positive" ? severity === idx : state === "confirmed_negative" && idx === 0;
                        return (
                          <button
                            key={opt}
                            type="button"
                            onClick={() =>
                              updateFunding(
                                d.key,
                                idx === 0
                                  ? { state: "confirmed_negative", severity: null }
                                  : { state: "confirmed_positive", severity: idx as 1 | 2 },
                              )
                            }
                            className={`rounded-lg border px-3 py-2 text-left text-xs transition ${
                              optionIsActive
                                ? idx === 2
                                  ? "border-gold-400/60 bg-gold-500/10 text-gold-300"
                                  : "border-signal-400/60 bg-signal-500/10 text-signal-200"
                                : "border-white/10 bg-white/[0.02] text-ink-secondary hover:border-white/25"
                            }`}
                          >
                            {opt}
                          </button>
                        );
                      })}
                    </div>
                    <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                      <button
                        type="button"
                        onClick={() => updateFunding(d.key, { state: "not_sure_yet", severity: null })}
                        className={`rounded-lg border px-3 py-2 text-left text-xs transition ${
                          state === "not_sure_yet"
                            ? "border-current-400/60 bg-current-500/10 text-current-200"
                            : "border-white/10 bg-white/[0.02] text-ink-secondary hover:border-white/25"
                        }`}
                      >
                        Not sure yet — treat as an open question, not a weakness
                      </button>
                      <button
                        type="button"
                        onClick={() => updateFunding(d.key, { state: "not_applicable", severity: null })}
                        className={`rounded-lg border px-3 py-2 text-left text-xs transition ${
                          state === "not_applicable"
                            ? "border-white/40 bg-white/10 text-ink-primary"
                            : "border-white/10 bg-white/[0.02] text-ink-secondary hover:border-white/25"
                        }`}
                      >
                        Not applicable to this venture
                      </button>
                    </div>
                  </motion.div>
                )}
              </div>
            );
          })}
        </div>

        <div className="space-y-4">
          <div className="panel flex flex-col items-center p-6 text-center">
            <p className="text-xs font-medium uppercase tracking-[0.15em] text-ink-muted">Evidence Strength</p>
            <div className="mt-4">
              <StrengthRing percent={strengthPercent} />
            </div>
            <p className="mt-3 text-xs text-ink-muted">
              Keep adding evidence to improve analysis accuracy.
            </p>
          </div>
          {answeredKeys.length > 0 && (
            <div className="panel p-4">
              <p className="text-xs font-medium uppercase tracking-[0.15em] text-ink-muted">Recently answered</p>
              <ul className="mt-2 space-y-1.5">
                {answeredKeys.slice(-4).map((d) => (
                  <li key={d.key} className="flex items-center gap-2 text-xs text-ink-secondary">
                    <span className="text-success-400">✓</span>
                    {d.label}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      <details className="panel mt-8 overflow-hidden">
        <summary className="cursor-pointer select-none px-5 py-4 text-sm font-medium text-ink-primary">
          Additional details (optional) — powers success prediction, revenue estimate, market
          intelligence, competitor analysis, personas, and business model sections
        </summary>
        <div className="grid grid-cols-1 gap-6 border-t border-white/5 p-5 sm:grid-cols-3">
          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-muted">Company & funding</p>
            <label className="block text-xs text-ink-secondary">
              Total funding raised (USD)
              <input
                type="number"
                min={0}
                value={companyMetrics.total_funding_usd ?? ""}
                onChange={(e) =>
                  updateCompanyMetrics({ total_funding_usd: e.target.value === "" ? null : Number(e.target.value) })
                }
                className="mt-1 w-full rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2 text-sm text-ink-primary"
              />
            </label>
            <label className="block text-xs text-ink-secondary">
              Funding rounds so far
              <input
                type="number"
                min={0}
                value={companyMetrics.funding_rounds ?? ""}
                onChange={(e) =>
                  updateCompanyMetrics({ funding_rounds: e.target.value === "" ? null : Number(e.target.value) })
                }
                className="mt-1 w-full rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2 text-sm text-ink-primary"
              />
            </label>
            <label className="block text-xs text-ink-secondary">
              Year founded
              <input
                type="number"
                min={1900}
                max={2100}
                value={companyMetrics.founded_year ?? ""}
                onChange={(e) =>
                  updateCompanyMetrics({ founded_year: e.target.value === "" ? null : Number(e.target.value) })
                }
                className="mt-1 w-full rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2 text-sm text-ink-primary"
              />
            </label>
            <label className="block text-xs text-ink-secondary">
              Country code (e.g. usa)
              <input
                type="text"
                value={companyMetrics.country_code ?? ""}
                onChange={(e) => updateCompanyMetrics({ country_code: e.target.value || null })}
                className="mt-1 w-full rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2 text-sm text-ink-primary"
              />
            </label>
          </div>

          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-muted">Revenue assumptions</p>
            <label className="block text-xs text-ink-secondary">
              Price per customer / month (USD)
              <input
                type="number"
                min={0}
                value={revenueAssumptions.price_per_customer_usd ?? ""}
                onChange={(e) =>
                  updateRevenueAssumptions({
                    price_per_customer_usd: e.target.value === "" ? null : Number(e.target.value),
                  })
                }
                className="mt-1 w-full rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2 text-sm text-ink-primary"
              />
            </label>
            <label className="block text-xs text-ink-secondary">
              Initial customer count
              <input
                type="number"
                min={0}
                value={revenueAssumptions.initial_customers ?? ""}
                onChange={(e) =>
                  updateRevenueAssumptions({ initial_customers: e.target.value === "" ? null : Number(e.target.value) })
                }
                className="mt-1 w-full rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2 text-sm text-ink-primary"
              />
            </label>
            <label className="block text-xs text-ink-secondary">
              Expected monthly growth (%)
              <input
                type="number"
                value={revenueAssumptions.monthly_growth_rate_pct ?? ""}
                onChange={(e) =>
                  updateRevenueAssumptions({
                    monthly_growth_rate_pct: e.target.value === "" ? null : Number(e.target.value),
                  })
                }
                className="mt-1 w-full rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2 text-sm text-ink-primary"
              />
            </label>
            <label className="block text-xs text-ink-secondary">
              Gross margin (%)
              <input
                type="number"
                min={0}
                max={100}
                value={revenueAssumptions.gross_margin_pct ?? ""}
                onChange={(e) =>
                  updateRevenueAssumptions({ gross_margin_pct: e.target.value === "" ? null : Number(e.target.value) })
                }
                className="mt-1 w-full rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2 text-sm text-ink-primary"
              />
            </label>
          </div>

          <div className="space-y-3">
            <p className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-muted">Market context</p>
            <label className="block text-xs text-ink-secondary">
              Target market
              <input
                type="text"
                value={marketEvidence.target_market ?? ""}
                onChange={(e) => updateMarketEvidence({ target_market: e.target.value || null })}
                className="mt-1 w-full rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2 text-sm text-ink-primary"
              />
            </label>
            <label className="block text-xs text-ink-secondary">
              Customer type
              <input
                type="text"
                value={marketEvidence.customer_type ?? ""}
                onChange={(e) => updateMarketEvidence({ customer_type: e.target.value || null })}
                className="mt-1 w-full rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2 text-sm text-ink-primary"
              />
            </label>
            <label className="block text-xs text-ink-secondary">
              Geography
              <input
                type="text"
                value={marketEvidence.geography ?? ""}
                onChange={(e) => updateMarketEvidence({ geography: e.target.value || null })}
                className="mt-1 w-full rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2 text-sm text-ink-primary"
              />
            </label>
            <label className="block text-xs text-ink-secondary">
              Stage
              <select
                value={marketEvidence.startup_stage ?? ""}
                onChange={(e) => updateMarketEvidence({ startup_stage: e.target.value || null })}
                className="mt-1 w-full rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2 text-sm text-ink-primary"
              >
                <option value="">Unspecified</option>
                <option value="idea">Idea</option>
                <option value="mvp">MVP</option>
                <option value="early_traction">Early traction</option>
                <option value="growth">Growth</option>
              </select>
            </label>
            <label className="block text-xs text-ink-secondary">
              Known competitors (comma-separated)
              <input
                type="text"
                value={competitorsInput}
                onChange={(e) => setCompetitorsInput(e.target.value)}
                onBlur={() =>
                  updateMarketEvidence({
                    known_competitors: competitorsInput
                      .split(",")
                      .map((c) => c.trim())
                      .filter(Boolean),
                  })
                }
                className="mt-1 w-full rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2 text-sm text-ink-primary"
              />
            </label>
          </div>
        </div>
      </details>

      {error && (
        <p role="alert" className="mt-6 rounded-xl border border-danger-500/30 bg-danger-500/10 p-3 text-sm text-danger-400">
          {error}
        </p>
      )}

      <div className="mt-8 flex items-center justify-between">
        <button
          type="button"
          onClick={() => navigate("/new/idea")}
          className="rounded-lg border border-white/15 px-5 py-2.5 text-sm font-medium text-ink-secondary transition hover:border-signal-400/50 hover:bg-white/5"
        >
          Back
        </button>
        <MagneticButton
          onClick={handleSubmit}
          disabled={submitting}
          className="btn-energy rounded-xl bg-gradient-to-r from-signal-600 via-signal-500 to-current-500 px-8 py-3 text-sm font-semibold text-ink-primary shadow-glow transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? "Submitting…" : "Review & Analyze"}
        </MagneticButton>
      </div>
    </div>
  );
}
