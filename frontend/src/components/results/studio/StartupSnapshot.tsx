import type { ReactNode } from "react";
import type { FundingAssessment, MentorInterpretation, SuccessPrediction } from "../../../types/api";

const STAGE_LABEL: Record<string, string> = {
  ready: "Investor Ready",
  developing: "Building Momentum",
  early_stage: "Idea Formation",
};

/** Section 1 — Startup Snapshot: one premium overview card, the first thing a founder sees.
 * Every field reads directly from already-computed data (venture positioning, mentor's idea
 * understanding, funding readiness, historical pattern signal) — nothing here is a new
 * computation, only a single consolidated first glance. */
export function StartupSnapshot({
  startupName,
  primaryDomain,
  mentor,
  fundingAssessment,
  successPrediction,
  children,
}: {
  startupName: string | null;
  primaryDomain: string | null;
  mentor: MentorInterpretation;
  fundingAssessment: FundingAssessment | null;
  successPrediction: SuccessPrediction | null;
  children?: ReactNode;
}) {
  const stageLabel = fundingAssessment ? STAGE_LABEL[fundingAssessment.level] ?? fundingAssessment.level : "Not yet assessed";

  return (
    <section aria-labelledby="snapshot-heading" className="panel panel-glow p-6 sm:p-8">
      <p className="text-xs font-medium uppercase tracking-[0.15em] text-ink-muted">Startup Snapshot</p>
      <h2 id="snapshot-heading" className="mt-2 text-display text-2xl text-ink-primary sm:text-3xl">
        {startupName ?? "Your Startup"}
      </h2>
      <p className="mt-3 max-w-2xl text-base text-ink-secondary">{mentor.mentor_verdict.concise_verdict}</p>

      <dl className="mt-6 grid grid-cols-1 gap-x-8 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">
        <div>
          <dt className="text-xs uppercase tracking-[0.08em] text-ink-muted">Industry</dt>
          <dd className="mt-1 text-sm text-ink-primary">{primaryDomain ?? "Not yet resolved"}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-[0.08em] text-ink-muted">Target Customer</dt>
          <dd className="mt-1 text-sm text-ink-primary">{mentor.idea_understanding.target_user}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-[0.08em] text-ink-muted">Business Model</dt>
          <dd className="mt-1 text-sm text-ink-primary">{mentor.business_model}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-[0.08em] text-ink-muted">Current Stage</dt>
          <dd className="mt-1 text-sm text-ink-primary">{stageLabel}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-[0.08em] text-ink-muted">Investment Readiness</dt>
          <dd className="mt-1 text-sm text-ink-primary">
            {fundingAssessment ? `${fundingAssessment.overall_score}/100` : "Not yet assessed"}
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-[0.08em] text-ink-muted">Historical Pattern Signal</dt>
          <dd className="mt-1 text-sm text-ink-primary">
            {successPrediction ? successPrediction.pattern_signal_display : "Not available for this run"}
          </dd>
        </div>
      </dl>

      {children}
    </section>
  );
}
