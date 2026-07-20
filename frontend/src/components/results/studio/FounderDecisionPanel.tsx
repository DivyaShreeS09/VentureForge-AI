import type { MentorInterpretation } from "../../../types/api";
import type { FounderDecisionLabel } from "../../../utils/founderDecision";
import { deriveFounderDecision } from "../../../utils/founderDecision";
import { Section } from "../Section";

const LABEL_STYLE: Record<FounderDecisionLabel, string> = {
  "Should Build": "border-success-500/40 bg-success-500/10 text-success-400",
  "Proceed Carefully": "border-signal-500/40 bg-signal-500/10 text-signal-400",
  "Needs Validation": "border-warning-500/40 bg-warning-500/10 text-warning-400",
  "High Risk": "border-danger-500/40 bg-danger-500/10 text-danger-400",
};

/** Section 3 — Founder Decision Panel: the single most important section on the page. Renders
 * one of exactly four recommendations (see utils/founderDecision.ts), always paired with the
 * concrete reasoning behind it — explicitly labeled a recommendation, never a prediction. */
export function FounderDecisionPanel({ mentor }: { mentor: MentorInterpretation }) {
  const decision = deriveFounderDecision(mentor);

  return (
    <Section id="founder-decision" title="Founder Decision Panel">
      <span
        className={`inline-block rounded-full border px-4 py-1.5 text-sm font-semibold uppercase tracking-[0.08em] ${LABEL_STYLE[decision.label]}`}
      >
        {decision.label}
      </span>
      <p className="mt-4 text-base text-ink-primary">{decision.reason}</p>

      <ul className="mt-5 space-y-2 border-t border-white/5 pt-4">
        {decision.detail.map((line) => (
          <li key={line} className="text-sm text-ink-secondary">
            {line}
          </li>
        ))}
      </ul>

      <p className="mt-4 text-xs italic text-ink-muted">
        This is a recommendation based on your current evidence, not a prediction of success or
        failure — it will change as you validate more.
      </p>
    </Section>
  );
}
