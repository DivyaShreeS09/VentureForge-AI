import { render, screen, fireEvent } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";
import { EvidenceQuestionScene } from "../../src/components/evidence/EvidenceQuestionScene";
import { EVIDENCE_DIMENSIONS } from "../../src/components/evidence/evidenceDimensions";
import { LanguageProvider } from "../../src/context/LanguageContext";

const PROBLEM_CLARITY = EVIDENCE_DIMENSIONS.find((d) => d.key === "problem_clarity")!;
const TRACTION = EVIDENCE_DIMENSIONS.find((d) => d.key === "traction")!;

function renderScene(ui: React.ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>);
}

describe("EvidenceQuestionScene", () => {
  it("renders the current dimension's question and all 5 answer options", () => {
    renderScene(<EvidenceQuestionScene dimension={PROBLEM_CLARITY} answer={undefined} stage="" onAnswer={vi.fn()} />);
    expect(screen.getByRole("heading", { name: /how well do you understand the problem/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /i'm still exploring the problem/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /i understand the pain deeply/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /i'm not sure yet/i })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /not applicable to my venture/i })).toBeInTheDocument();
  });

  it("calls onAnswer with the real evidence state and severity for the clicked option", () => {
    const onAnswer = vi.fn();
    renderScene(<EvidenceQuestionScene dimension={PROBLEM_CLARITY} answer={undefined} stage="" onAnswer={onAnswer} />);
    fireEvent.click(screen.getByRole("radio", { name: /i understand the pain deeply/i }));
    expect(onAnswer).toHaveBeenCalledWith({ state: "confirmed_positive", severity: 2 });
  });

  it("shows no acknowledgment before an answer is given", () => {
    renderScene(<EvidenceQuestionScene dimension={PROBLEM_CLARITY} answer={undefined} stage="" onAnswer={vi.fn()} />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("acknowledges the answer honestly once one is selected", () => {
    renderScene(
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
      <LanguageProvider>
        <EvidenceQuestionScene dimension={TRACTION} answer={undefined} stage="Just an idea" onAnswer={vi.fn()} />
      </LanguageProvider>,
    );
    expect(screen.getByText(/normal not to have users/i)).toBeInTheDocument();

    rerender(
      <LanguageProvider>
        <EvidenceQuestionScene dimension={TRACTION} answer={undefined} stage="Growing" onAnswer={vi.fn()} />
      </LanguageProvider>,
    );
    expect(screen.queryByText(/normal not to have users/i)).not.toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = renderScene(
      <EvidenceQuestionScene dimension={PROBLEM_CLARITY} answer={undefined} stage="" onAnswer={vi.fn()} />,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
