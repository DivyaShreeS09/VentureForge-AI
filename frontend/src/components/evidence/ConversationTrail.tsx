import type { FundingAnswers } from "../../types/api";
import type { EvidenceDimension } from "./evidenceDimensions";

interface Props {
  dimensions: EvidenceDimension[];
  answers: FundingAnswers;
  /** Index of the dimension currently being asked — excluded, since it isn't "memory" yet. */
  currentIndex: number;
}

const STATUS_LABEL: Record<string, string> = {
  confirmed_positive: "Answered",
  confirmed_negative: "Answered",
  not_sure_yet: "Open question",
  not_applicable: "Skipped",
};

/** Conversation memory — a quiet, honest transcript of what the founder has already told the
 * mentor, so nothing feels forgotten or re-asked. Deliberately understated (Build Contract: calm
 * confidence, never a dashboard) — a short list of labels and plain-language status words, no
 * scores or icons competing with the current question. */
export function ConversationTrail({ dimensions, answers, currentIndex }: Props) {
  const answered = dimensions
    .map((d, index) => ({ dimension: d, index }))
    .filter(({ dimension, index }) => index < currentIndex && answers[dimension.key] !== undefined);

  if (answered.length === 0) return null;

  return (
    // Tailwind's preflight sets `list-style: none` globally, which in Chrome/Safari also
    // silently strips the implicit ARIA list/listitem roles unless restored explicitly (found
    // while verifying Sprint 6's own stage checklist in a real browser — same gap here). Not
    // actually redundant despite the lint rule's assumption.
    // eslint-disable-next-line jsx-a11y/no-redundant-roles
    <ul aria-label="What you've told me so far" role="list" className="flex flex-col gap-1.5">
      {answered.map(({ dimension }) => {
        const entry = answers[dimension.key];
        const label = entry ? STATUS_LABEL[entry.state] : "";
        return (
          // eslint-disable-next-line jsx-a11y/no-redundant-roles
          <li key={dimension.key} role="listitem" className="flex items-baseline gap-2 text-forge-1 text-forge-text-tertiary">
            <span aria-hidden="true" className="h-1 w-1 shrink-0 rounded-full bg-forge-text-tertiary" />
            <span>
              {dimension.question.replace(/\?$/, "")} — {label}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
