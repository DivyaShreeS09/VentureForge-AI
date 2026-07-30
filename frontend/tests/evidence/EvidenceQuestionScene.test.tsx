import { render, screen, fireEvent } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";
import { EvidenceQuestionScene } from "../../src/components/evidence/EvidenceQuestionScene";
import { EVIDENCE_DIMENSIONS } from "../../src/components/evidence/evidenceDimensions";

const PROBLEM_CLARITY = EVIDENCE_DIMENSIONS.find((d) => d.key === "problem_clarity")!;
const TRACTION = EVIDENCE_DIMENSIONS.find((d) => d.key === "traction")!;

describe("EvidenceQuestionScene", () => {
  it("renders the current dimension's question and all 5 answer options", () => {
    render(<EvidenceQuestionScene dimension={PROBLEM_CLARITY} answer={undefined} stage="" onAnswer={vi.fn()} />);
    expect(screen.getByRole("heading", { name: /state the problem/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /not yet — still fuzzy/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /yes — specific and well-defined/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /i'm not sure yet/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /not applicable to my venture/i })).toBeInTheDocument();
  });

  it("calls onAnswer with the real evidence state and severity for the clicked option", () => {
    const onAnswer = vi.fn();
    render(<EvidenceQuestionScene dimension={PROBLEM_CLARITY} answer={undefined} stage="" onAnswer={onAnswer} />);
    fireEvent.click(screen.getByRole("radio", { name: /yes — specific and well-defined/i }));
    expect(onAnswer).toHaveBeenCalledWith({ state: "confirmed_positive", severity: 2 });
  });

  it("shows no acknowledgment before an answer is given", () => {
    render(<EvidenceQuestionScene dimension={PROBLEM_CLARITY} answer={undefined} stage="" onAnswer={vi.fn()} />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("acknowledges the answer honestly once one is selected", () => {
    render(
      <EvidenceQuestionScene
        dimension={PROBLEM_CLARITY}
        answer={{ state: "confirmed_negative", severity: null }}
        stage=""
        onAnswer={vi.fn()}
      />,
    );
    expect(screen.getByRole("status")).toHaveTextContent(/not a flaw in the idea/i);
  });

  it("shows a stage-aware note only for early-stage founders on a stage-sensitive dimension", () => {
    const { rerender } = render(
      <EvidenceQuestionScene dimension={TRACTION} answer={undefined} stage="Just an idea" onAnswer={vi.fn()} />,
    );
    expect(screen.getByText(/expected/i)).toBeInTheDocument();

    rerender(<EvidenceQuestionScene dimension={TRACTION} answer={undefined} stage="Growing" onAnswer={vi.fn()} />);
    expect(screen.queryByText(/expected/i)).not.toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <EvidenceQuestionScene dimension={PROBLEM_CLARITY} answer={undefined} stage="" onAnswer={vi.fn()} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
