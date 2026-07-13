import { motion } from "framer-motion";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useNewAnalysis } from "../context/NewAnalysisContext";

const STEPS = ["Idea Details", "Business Model", "Team & Market", "Review"] as const;

const fieldClasses =
  "mt-2 block w-full rounded-xl border border-white/10 bg-white/[0.04] px-4 py-3 text-ink-primary " +
  "placeholder:text-ink-muted transition focus:border-signal-400/60 focus:outline-none focus:ring-2 focus:ring-signal-500/25";

function StepIndicator({ current }: { current: number }) {
  return (
    <ol className="flex items-center gap-3">
      {STEPS.map((label, idx) => {
        const step = idx + 1;
        const isDone = step < current;
        const isActive = step === current;
        return (
          <li key={label} className="flex items-center gap-3">
            <div className="flex flex-col items-center gap-1.5">
              <span
                className={`flex h-8 w-8 items-center justify-center rounded-full border text-xs font-semibold transition ${
                  isActive
                    ? "border-signal-400 bg-signal-500/20 text-ink-primary shadow-glow"
                    : isDone
                      ? "border-signal-500/60 bg-signal-500/10 text-signal-300"
                      : "border-white/15 bg-white/5 text-ink-muted"
                }`}
              >
                {isDone ? "✓" : step}
              </span>
              <span className={`text-[11px] ${isActive ? "text-ink-primary" : "text-ink-muted"}`}>{label}</span>
            </div>
            {idx < STEPS.length - 1 && <span className="mb-4 h-px w-8 bg-white/10 sm:w-14" aria-hidden="true" />}
          </li>
        );
      })}
    </ol>
  );
}

/** Backend only accepts name + description + funding_answers. Steps 1-3 here are a frontend
 * authoring aid — each guided section prompts for a specific angle, and all of it is folded into
 * one enriched `description` string (see NewAnalysisContext.buildDescription) before it's ever
 * sent anywhere. No new backend field is invented. Evidence (funding_answers) is collected on the
 * next page, not here. */
export function IdeaSubmissionPage() {
  const navigate = useNavigate();
  const { idea, updateIdea, buildDescription } = useNewAnalysis();
  const [step, setStep] = useState(1);
  const [error, setError] = useState<string | null>(null);

  function goNext() {
    if (step === 1) {
      if (!idea.name.trim()) {
        setError("Startup / idea name is required.");
        return;
      }
      if (idea.problemSolution.trim().length < 10) {
        setError("Describe your idea in at least 10 characters.");
        return;
      }
    }
    setError(null);
    if (step < STEPS.length) setStep(step + 1);
    else navigate("/new/evidence");
  }

  function goBack() {
    setError(null);
    if (step > 1) setStep(step - 1);
  }

  const description = buildDescription();

  return (
    <div className="mx-auto max-w-3xl px-6 py-14 sm:px-10">
      <p className="text-xs font-medium uppercase tracking-[0.25em] text-signal-400">Idea Submission</p>
      <h1 className="mt-2 text-display text-3xl">Let's start with your idea</h1>
      <p className="mt-2 text-ink-secondary">The more details you provide, the more accurate our analysis.</p>

      <div className="mt-8">
        <StepIndicator current={step} />
      </div>

      <motion.div
        key={step}
        initial={{ opacity: 0, x: 12 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        className="panel mt-8 space-y-6 p-6 sm:p-8"
      >
        {step === 1 && (
          <>
            <h2 className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-muted">Basic Information</h2>
            <div>
              <label htmlFor="idea-name" className="block text-sm font-medium text-ink-secondary">
                Startup / Idea Name
              </label>
              <input
                id="idea-name"
                className={fieldClasses}
                placeholder="e.g. HealthVision AI"
                value={idea.name}
                onChange={(e) => updateIdea({ name: e.target.value })}
              />
            </div>
            <div>
              <label htmlFor="idea-pitch" className="block text-sm font-medium text-ink-secondary">
                One-line Pitch
              </label>
              <input
                id="idea-pitch"
                className={fieldClasses}
                placeholder="A one-line summary of your startup"
                value={idea.onePitch}
                onChange={(e) => updateIdea({ onePitch: e.target.value })}
              />
            </div>
            <div>
              <label htmlFor="idea-description" className="block text-sm font-medium text-ink-secondary">
                Describe your startup idea in detail
              </label>
              <p className="mt-1 text-xs text-ink-muted">
                What problem are you solving? How does your solution work? This feeds the industry
                classifier directly.
              </p>
              <textarea
                id="idea-description"
                rows={5}
                maxLength={2000}
                className={fieldClasses}
                placeholder="What problem are you solving? How does your solution work?"
                value={idea.problemSolution}
                onChange={(e) => updateIdea({ problemSolution: e.target.value })}
              />
              <p className="mt-1 text-right text-xs text-ink-muted">{idea.problemSolution.length} / 2000</p>
            </div>
          </>
        )}

        {step === 2 && (
          <>
            <h2 className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-muted">Business Model</h2>
            <div>
              <label htmlFor="idea-industry" className="block text-sm font-medium text-ink-secondary">
                Industry &amp; Market
              </label>
              <p className="mt-1 text-xs text-ink-muted">
                What industry does this operate in, and how does it make money? Industry itself is
                predicted by the classifier from your description — this section adds context, it
                doesn't set the category directly.
              </p>
              <textarea
                id="idea-industry"
                rows={4}
                className={fieldClasses}
                placeholder="e.g. B2B SaaS for healthcare providers, subscription pricing per clinician seat."
                value={idea.industryMarket}
                onChange={(e) => updateIdea({ industryMarket: e.target.value })}
              />
            </div>
          </>
        )}

        {step === 3 && (
          <>
            <h2 className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-muted">Team &amp; Market</h2>
            <div>
              <label htmlFor="idea-customer" className="block text-sm font-medium text-ink-secondary">
                Target Customer
              </label>
              <textarea
                id="idea-customer"
                rows={3}
                className={fieldClasses}
                placeholder="Who specifically buys or uses this?"
                value={idea.targetCustomer}
                onChange={(e) => updateIdea({ targetCustomer: e.target.value })}
              />
            </div>
            <div>
              <label htmlFor="idea-stage" className="block text-sm font-medium text-ink-secondary">
                Current Stage
              </label>
              <textarea
                id="idea-stage"
                rows={3}
                className={fieldClasses}
                placeholder="Idea, prototype, launched, revenue-generating..."
                value={idea.currentStage}
                onChange={(e) => updateIdea({ currentStage: e.target.value })}
              />
            </div>
          </>
        )}

        {step === 4 && (
          <>
            <h2 className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-muted">Review</h2>
            <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
              <p className="text-sm font-medium text-ink-primary">{idea.name || "Untitled venture"}</p>
              {idea.onePitch && <p className="mt-1 text-sm text-signal-300">{idea.onePitch}</p>}
              <p className="mt-3 whitespace-pre-wrap text-sm text-ink-secondary">{description}</p>
            </div>
            <p className="text-xs text-ink-muted">
              This is exactly what will be sent to the industry classifier. Continue to add funding-
              readiness evidence next.
            </p>
          </>
        )}

        {error && (
          <p role="alert" className="rounded-xl border border-danger-500/30 bg-danger-500/10 p-3 text-sm text-danger-400">
            {error}
          </p>
        )}

        <div className="flex items-center justify-between pt-2">
          <button
            type="button"
            onClick={goBack}
            disabled={step === 1}
            className="rounded-lg border border-white/15 px-5 py-2.5 text-sm font-medium text-ink-secondary transition hover:border-signal-400/50 hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Back
          </button>
          <button
            type="button"
            onClick={goNext}
            className="btn-energy rounded-xl bg-gradient-to-r from-signal-600 via-signal-500 to-current-500 px-6 py-2.5 text-sm font-semibold text-ink-primary shadow-glow transition hover:brightness-110"
          >
            Continue
          </button>
        </div>
      </motion.div>

      <p className="mt-4 flex items-center gap-1.5 text-xs text-ink-muted">
        <span className="h-1.5 w-1.5 rounded-full bg-success-500" aria-hidden="true" />
        Autosaved locally
      </p>
    </div>
  );
}
