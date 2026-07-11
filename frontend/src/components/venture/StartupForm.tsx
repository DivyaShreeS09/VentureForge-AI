import { useMemo, useState } from "react";
import type { FundingAnswers } from "../../types/api";

type Dimension = { key: keyof FundingAnswers; label: string; help: string; options: string[] };

/** Grouped by what an investor actually asks about first — not the raw dimension order the
 * backend rubric happens to define them in (see backend/app/ml/funding_readiness.py). Purely a
 * frontend presentation grouping; the payload sent to the API is unaffected. */
const DIMENSION_GROUPS: { title: string; dimensions: Dimension[] }[] = [
  {
    title: "Market & Problem",
    dimensions: [
      {
        key: "problem_clarity",
        label: "Problem clarity",
        help: "Can you state who has this problem and what it costs them in one sentence?",
        options: ["Not stated", "Broadly stated", "Specific & well-defined"],
      },
      {
        key: "customer_pain_evidence",
        label: "Evidence of customer pain",
        help: "Interviews, surveys, or support tickets documenting the pain — not just a hunch.",
        options: ["None", "Anecdotal", "Documented (interviews/data)"],
      },
      {
        key: "market_size_evidence",
        label: "Market size evidence",
        help: "A sourced estimate, not a guessed billion-dollar figure.",
        options: ["None", "Rough estimate", "Sourced TAM/SAM/SOM"],
      },
    ],
  },
  {
    title: "Product & Traction",
    dimensions: [
      {
        key: "product_maturity",
        label: "Product maturity",
        help: "What a real user could try today.",
        options: ["Idea only", "Prototype / MVP", "Live product with users"],
      },
      {
        key: "traction",
        label: "Traction",
        help: "Real usage or paying customers, not projected ones.",
        options: ["No users yet", "Early pilot users", "Paying / recurring customers"],
      },
      {
        key: "competitive_differentiation",
        label: "Competitive differentiation",
        help: "How this differs from the 2-3 closest alternatives.",
        options: ["Not stated", "Some differentiation", "Clear & defensible"],
      },
    ],
  },
  {
    title: "Team & Business Model",
    dimensions: [
      {
        key: "team_completeness",
        label: "Team completeness",
        help: "Does the founding team cover the core skills this venture needs?",
        options: ["Solo founder", "Partial team", "Core skills covered"],
      },
      {
        key: "revenue_model_clarity",
        label: "Revenue model clarity",
        help: "Pricing and unit economics, not just \"we'll figure it out.\"",
        options: ["Not defined", "Roughly defined", "Clear pricing & unit economics"],
      },
    ],
  },
];

const ALL_DIMENSIONS = DIMENSION_GROUPS.flatMap((g) => g.dimensions);

export interface StartupFormValues {
  name: string;
  description: string;
  funding_answers: FundingAnswers;
}

interface Props {
  onSubmit: (values: StartupFormValues) => void;
  submitting: boolean;
}

const fieldClasses =
  "mt-2 block w-full rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3 text-ink-primary " +
  "placeholder:text-ink-muted transition focus:border-signal-400/60 focus:outline-none focus:ring-2 focus:ring-signal-500/25";

/** Violet marks any answered dimension (active interaction); gold is reserved for the strongest
 * evidence tier (raw_score 2 — "achievement", per the brief's color-hierarchy rule), never for
 * merely answering a field. */
function selectClasses(value: number | null | undefined): string {
  const base =
    "mt-2 block w-full rounded-lg border bg-white/[0.04] px-3 py-2 text-sm text-ink-secondary " +
    "transition focus:outline-none focus:ring-2 ";
  if (value === 2) return base + "border-gold-500/40 bg-gold-500/[0.07] focus:border-gold-400/60 focus:ring-gold-500/25";
  if (value === 0 || value === 1) return base + "border-signal-500/30 bg-signal-500/[0.06] focus:border-signal-400/60 focus:ring-signal-500/25";
  return base + "border-white/10 focus:border-signal-400/60 focus:ring-signal-500/25";
}

export function StartupForm({ onSubmit, submitting }: Props) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [fundingAnswers, setFundingAnswers] = useState<FundingAnswers>({});
  const [validationError, setValidationError] = useState<string | null>(null);

  const answeredCount = Object.values(fundingAnswers).filter((v) => v !== null && v !== undefined).length;
  const completeness = useMemo(() => {
    const core = (name.trim() ? 1 : 0) + (description.trim().length >= 10 ? 1 : 0);
    return Math.round(((core + answeredCount / ALL_DIMENSIONS.length) / 3) * 100);
  }, [name, description, answeredCount]);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim()) {
      setValidationError("Startup name is required.");
      return;
    }
    if (description.trim().length < 10) {
      setValidationError("Description must be at least 10 characters.");
      return;
    }
    setValidationError(null);
    onSubmit({ name, description, funding_answers: fundingAnswers });
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-9" noValidate>
      <div>
        <div className="flex items-center justify-between text-xs">
          <span className="font-medium uppercase tracking-[0.15em] text-ink-muted">Submission completeness</span>
          <span className={`font-semibold ${completeness >= 100 ? "text-gold-400" : "text-signal-400"}`}>
            {completeness}%
          </span>
        </div>
        <div
          className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-white/5"
          role="progressbar"
          aria-valuenow={completeness}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Submission completeness"
        >
          <div
            className={`h-full rounded-full transition-[width] duration-500 ${
              completeness >= 100
                ? "bg-gradient-to-r from-signal-500 via-current-400 to-gold-400"
                : "bg-gradient-to-r from-signal-500 to-current-400"
            }`}
            style={{ width: `${completeness}%` }}
          />
        </div>
      </div>

      <div>
        <label htmlFor="startup-name" className="block text-sm font-medium text-ink-secondary">
          Startup name
        </label>
        <input
          id="startup-name"
          name="name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className={fieldClasses}
          placeholder="e.g. Nova Health"
          required
        />
      </div>

      <div>
        <label htmlFor="startup-description" className="block text-sm font-medium text-ink-secondary">
          Startup description
        </label>
        <p className="mt-1 text-xs text-ink-muted">
          What it does, for whom, and how — this text feeds the industry classifier directly.
        </p>
        <textarea
          id="startup-description"
          name="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={4}
          className={fieldClasses}
          placeholder="A telehealth platform connecting patients with clinicians for chronic care follow-up."
          required
          minLength={10}
        />
      </div>

      <fieldset className="space-y-6">
        <div>
          <legend className="text-sm font-medium text-ink-secondary">Funding readiness details</legend>
          <p className="mt-1 text-xs text-ink-muted">
            Optional — each dimension left unanswered scores 0 in the readiness assessment, not a
            favorable assumption. See the methodology note on the results page.
          </p>
        </div>

        {DIMENSION_GROUPS.map((group) => (
          <div key={group.title} className="rounded-xl border border-white/5 bg-white/[0.015] p-4">
            <h3 className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-muted">{group.title}</h3>
            <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-3">
              {group.dimensions.map(({ key, label, help, options }) => (
                <div key={key}>
                  <label htmlFor={`funding-${key}`} className="block text-xs font-medium text-ink-secondary">
                    {label}
                  </label>
                  <p className="mt-0.5 text-[11px] leading-snug text-ink-muted">{help}</p>
                  <select
                    id={`funding-${key}`}
                    name={key}
                    value={fundingAnswers[key] ?? ""}
                    onChange={(e) =>
                      setFundingAnswers((prev) => ({
                        ...prev,
                        [key]: e.target.value === "" ? null : Number(e.target.value),
                      }))
                    }
                    className={selectClasses(fundingAnswers[key])}
                  >
                    <option value="">Not answered</option>
                    {options.map((opt, idx) => (
                      <option key={opt} value={idx}>
                        {opt}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </div>
        ))}
      </fieldset>

      {validationError && (
        <p role="alert" className="rounded-xl border border-danger-500/30 bg-danger-500/10 p-4 text-sm text-danger-400">
          {validationError}
        </p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="btn-energy w-full rounded-xl bg-gradient-to-r from-signal-600 via-signal-500 to-current-500 px-6 py-4 text-base font-semibold text-ink-primary shadow-glow transition duration-300 hover:brightness-110 hover:shadow-glow-blue focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none sm:w-auto sm:px-10"
      >
        {submitting ? "Submitting…" : "Initiate Venture Analysis"}
      </button>
    </form>
  );
}
