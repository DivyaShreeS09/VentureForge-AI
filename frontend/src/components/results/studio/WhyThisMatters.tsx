import type { MarketIntelligence, MentorInterpretation } from "../../../types/api";
import { Section } from "../Section";

const MAX_BULLETS = 6;

/** Section 2 — Why This Startup Matters: at most 6 concise bullets on problem, customer, market
 * need, and the current opportunity — every bullet sourced from data already computed elsewhere
 * on this page (idea understanding, market intelligence, mentor verdict), never restated
 * verbatim as its own separate card. */
export function WhyThisMatters({
  mentor,
  marketIntelligence,
}: {
  mentor: MentorInterpretation;
  marketIntelligence: MarketIntelligence | null;
}) {
  const bullets = [
    `Problem: ${mentor.idea_understanding.problem}`,
    `Customer: ${mentor.idea_understanding.target_user}`,
    `Market need: ${marketIntelligence?.market_summary ?? mentor.customer_and_market}`,
    `Current opportunity: ${mentor.mentor_verdict.strongest_signal}`,
    `Competitive landscape: ${mentor.competitor_landscape}`,
    `Business context: ${mentor.idea_understanding.business_context}`,
  ].slice(0, MAX_BULLETS);

  return (
    <Section id="why-this-matters" title="Why This Startup Matters">
      <ul className="space-y-3">
        {bullets.map((bullet) => (
          <li key={bullet} className="flex gap-3 text-sm text-ink-secondary">
            <span aria-hidden="true" className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-signal-400" />
            <span>{bullet}</span>
          </li>
        ))}
      </ul>
    </Section>
  );
}
