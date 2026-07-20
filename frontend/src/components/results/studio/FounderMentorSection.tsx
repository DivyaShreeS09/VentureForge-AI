import type { MentorInterpretation } from "../../../types/api";
import { Section } from "../Section";

/** Section 9 — Founder Mentor: the final, one-page, plain-language mentor summary. Friendly,
 * actionable, no technical terminology — always ends with the top 3 highest-impact actions,
 * reusing the same prioritized `top_next_actions` shown earlier in the roadmap, restated here as
 * the single closing takeaway rather than a duplicated list. */
export function FounderMentorSection({ mentor }: { mentor: MentorInterpretation }) {
  const topThree = mentor.top_next_actions.slice(0, 3);

  return (
    <Section id="founder-mentor" title="Founder Mentor">
      <p className="text-base text-ink-primary">{mentor.idea_understanding.summary}</p>
      <p className="mt-3 text-sm text-ink-secondary">{mentor.mentor_verdict.concise_verdict}</p>

      <p className="mt-5 text-sm font-medium text-ink-primary">
        Here are the three highest-impact actions I'd recommend this week.
      </p>
      <ol className="mt-3 list-inside list-decimal space-y-2 text-sm text-ink-secondary">
        {topThree.map((action) => (
          <li key={action}>{action}</li>
        ))}
      </ol>
    </Section>
  );
}
