import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ConversationTrail } from "../../src/components/evidence/ConversationTrail";
import { EVIDENCE_DIMENSIONS } from "../../src/components/evidence/evidenceDimensions";
import type { FundingAnswers } from "../../src/types/api";

describe("ConversationTrail", () => {
  it("renders nothing before any question has been answered", () => {
    const { container } = render(
      <ConversationTrail dimensions={EVIDENCE_DIMENSIONS} answers={{}} currentIndex={0} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("lists only dimensions strictly before the current index, never the one being asked now", () => {
    const answers: FundingAnswers = {
      problem_clarity: { state: "confirmed_positive", severity: 2 },
      customer_pain_evidence: { state: "not_sure_yet", severity: null },
    };
    render(<ConversationTrail dimensions={EVIDENCE_DIMENSIONS} answers={answers} currentIndex={1} />);
    expect(screen.getByText(/can you state the problem in one clear sentence — answered/i)).toBeInTheDocument();
    expect(screen.queryByText(/customer_pain/i)).not.toBeInTheDocument();
  });

  it("labels a not_sure_yet answer as an open question, never a weakness", () => {
    const answers: FundingAnswers = {
      problem_clarity: { state: "not_sure_yet", severity: null },
    };
    render(<ConversationTrail dimensions={EVIDENCE_DIMENSIONS} answers={answers} currentIndex={1} />);
    expect(screen.getByText(/open question/i)).toBeInTheDocument();
  });
});
