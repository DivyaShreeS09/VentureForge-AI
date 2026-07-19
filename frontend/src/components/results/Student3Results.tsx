import type { Student3Outputs } from "../../types/api";
import { Section } from "./Section";

export function Student3Results({ outputs }: { outputs: Student3Outputs }) {
  const segment = outputs.customer_segment;

  return (
    <>
      {segment && (
        <Section id="customer-segment" title="Customer Segment" source="deterministic">
          <p className="font-medium text-ink-primary">{segment.segment_name}</p>
          <p className="mt-1 text-sm text-ink-muted">
            {segment.fit_score === null ? "No model confidence is reported for clustering." : `Fit score: ${(segment.fit_score * 100).toFixed(0)}%`}
            {" · "}{segment.method.replace("_", " ")}
          </p>
          <p className="mt-3 text-sm text-ink-secondary">{segment.characteristics.join(" · ")}</p>
          <p className="mt-3 text-xs text-warning-400">{segment.limitations[0]}</p>
        </Section>
      )}

      <Section id="recommendations" title="Ranked Next Actions" source="deterministic">
        {outputs.ranked_actions.length === 0 ? (
          <p className="text-sm text-ink-muted">No additional action is available from the submitted readiness evidence.</p>
        ) : (
          <ol className="space-y-3">
            {outputs.ranked_actions.map((action) => (
              <li key={action.title} className="rounded-xl border border-white/10 p-4">
                <div className="flex justify-between gap-3">
                  <p className="font-medium">{action.title}</p>
                  <span className="text-xs text-signal-400">{action.priority_score}/100</span>
                </div>
                <p className="mt-1 text-sm text-ink-muted">Impact: {action.impact} · Effort: {action.effort} · {action.urgency}</p>
                <p className="mt-2 text-xs text-ink-secondary">Dependency: {action.dependency}</p>
              </li>
            ))}
          </ol>
        )}
      </Section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Section id="innovation" title="Innovation Opportunities" source="deterministic">
          <ul className="space-y-3">
            {outputs.innovation_opportunities.map((item) => (
              <li key={item.opportunity} className="rounded-xl border border-white/10 p-4">
                <p className="font-medium">{item.opportunity}</p>
                <p className="mt-1 text-sm text-ink-muted">{item.rationale}</p>
                <p className="mt-2 text-xs text-signal-400">Validate: {item.validation_requirement}</p>
              </li>
            ))}
          </ul>
        </Section>
        <Section id="risk-matrix" title="Risk Matrix" source="deterministic">
          <ul className="space-y-3">
            {outputs.risks.map((risk) => (
              <li key={risk.title} className="rounded-xl border border-danger-500/20 p-4">
                <p className="font-medium">{risk.title}</p>
                <p className="mt-1 text-xs uppercase text-danger-400">{risk.category} · {risk.severity} severity</p>
                <p className="mt-2 text-sm text-ink-muted">Mitigation: {risk.mitigation}</p>
              </li>
            ))}
          </ul>
        </Section>
      </div>

      <Section id="growth-strategy" title="Growth Strategy" source="deterministic">
        <ul className="space-y-3">
          {outputs.growth_strategy.map((item) => (
            <li key={item.area} className="rounded-xl border border-white/10 p-4">
              <p className="text-xs uppercase text-signal-400">{item.area}</p>
              <p className="mt-1 font-medium">{item.recommendation}</p>
              <p className="mt-1 text-sm text-ink-muted">{item.rationale}</p>
            </li>
          ))}
        </ul>
      </Section>

      <Section id="pitch-deck" title="Pitch Deck Preview" source="deterministic">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {outputs.pitch_deck.map((slide) => (
            <article key={slide.title} className="rounded-xl border border-white/10 p-4">
              <p className="font-medium">{slide.title}</p>
              <ul className="mt-2 list-inside list-disc text-sm text-ink-muted">
                {slide.content.map((line) => <li key={line}>{line}</li>)}
              </ul>
              <p className="mt-2 text-xs text-warning-400">{slide.evidence_status}</p>
            </article>
          ))}
        </div>
      </Section>
    </>
  );
}
