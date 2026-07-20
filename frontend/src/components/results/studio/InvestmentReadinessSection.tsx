import type { ReactNode } from "react";
import type { FounderGuidanceItem, FundingAssessment, SuccessPrediction } from "../../../types/api";
import { ReadinessReactor } from "../../visualizations/ReadinessReactor";
import { Section } from "../Section";

/** Section 8 — Investment Readiness: one unified investor view combining Funding Readiness, the
 * Historical Pattern Signal, evidence quality, traction, and business model — all already
 * computed elsewhere on the backend; this only presents them together instead of as separate
 * disconnected cards. `children` slot renders the existing, real revenue-scenario editor. */
export function InvestmentReadinessSection({
  fundingAssessment,
  successPrediction,
  founderGuidanceItems,
  businessModelSummary,
  children,
}: {
  fundingAssessment: FundingAssessment;
  successPrediction: SuccessPrediction | null;
  founderGuidanceItems: FounderGuidanceItem[];
  businessModelSummary: string;
  children?: ReactNode;
}) {
  const rubricItems = founderGuidanceItems.filter((i) => !i.dimension.startsWith("capability:"));
  const confirmedCount = rubricItems.filter((i) => i.category === "strength").length;
  const traction = founderGuidanceItems.find((i) => i.dimension === "traction");

  return (
    <Section id="investment-readiness" title="Investment Readiness">
      <ReadinessReactor score={fundingAssessment.overall_score} level={fundingAssessment.level} />
      <p className="mt-4 text-xs italic text-ink-muted">{fundingAssessment.disclaimer}</p>

      <dl className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <dt className="text-xs uppercase tracking-[0.08em] text-ink-muted">Evidence Quality</dt>
          <dd className="mt-1 text-sm text-ink-primary">
            {confirmedCount} of {rubricItems.length} dimensions confirmed
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-[0.08em] text-ink-muted">Traction</dt>
          <dd className="mt-1 text-sm text-ink-primary">{traction ? traction.status : "Not yet assessed"}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-[0.08em] text-ink-muted">Business Model</dt>
          <dd className="mt-1 text-sm text-ink-primary">{businessModelSummary}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-[0.08em] text-ink-muted">Historical Pattern Signal</dt>
          <dd className="mt-1 text-sm text-ink-primary">
            {successPrediction ? successPrediction.pattern_signal_display : "Not available for this run"}
          </dd>
        </div>
      </dl>

      {successPrediction && (
        <p className="mt-4 rounded-xl border border-white/10 bg-white/[0.02] p-4 text-sm text-ink-secondary">
          {successPrediction.pattern_signal_sentence}
        </p>
      )}

      {children}
    </Section>
  );
}
