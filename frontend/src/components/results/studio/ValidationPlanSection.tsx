import type { MentorValidationAction } from "../../../types/api";
import { buildValidationDisplay } from "../../../utils/founderDecision";
import { Section } from "../Section";

/** Section 5 — Validation Plan: the existing `validation_plan` (already computed
 * deterministically — see backend/app/agents/mentor_synthesis.py) presented as top assumptions,
 * paired with how to test each one, its success metric, failure signal, estimated time, and the
 * expected learning — everything a founder needs to actually run the test, not just a question. */
export function ValidationPlanSection({ validationPlan }: { validationPlan: MentorValidationAction[] }) {
  const items = buildValidationDisplay(validationPlan);

  return (
    <Section id="validation-plan" title="Validation Plan">
      {items.length > 0 ? (
        <ul className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {items.map((item) => (
            <li key={item.source_gap} className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
              <p className="text-sm font-medium text-ink-primary">{item.question_to_answer}</p>
              <dl className="mt-3 space-y-2 text-xs text-ink-secondary">
                <div>
                  <dt className="text-ink-muted">How to test</dt>
                  <dd>{item.method}</dd>
                </div>
                <div>
                  <dt className="text-ink-muted">Success metric</dt>
                  <dd>{item.success_criterion}</dd>
                </div>
                <div>
                  <dt className="text-ink-muted">Failure signal</dt>
                  <dd>{item.failure_signal}</dd>
                </div>
                <div>
                  <dt className="text-ink-muted">Estimated time</dt>
                  <dd>{item.estimated_time}</dd>
                </div>
                <div>
                  <dt className="text-ink-muted">Expected learning</dt>
                  <dd>{item.expected_learning}</dd>
                </div>
              </dl>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-ink-muted">Every core assumption already has confirmed evidence — nothing left to validate right now.</p>
      )}
    </Section>
  );
}
