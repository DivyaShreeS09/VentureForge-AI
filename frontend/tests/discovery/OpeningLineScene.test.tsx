import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { OpeningLineScene } from "../../src/components/discovery/OpeningLineScene";
import { LanguageProvider } from "../../src/context/LanguageContext";

function renderScene(ui: React.ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>);
}

function baseProps(overrides: Partial<React.ComponentProps<typeof OpeningLineScene>> = {}) {
  return {
    description: "",
    name: "",
    onDescriptionChange: vi.fn(),
    onNameChange: vi.fn(),
    onSubmit: vi.fn(),
    error: null,
    preview: null,
    previewLoading: false,
    previewError: null,
    ...overrides,
  };
}

describe("OpeningLineScene", () => {
  it("asks only the description question until enough has been written", () => {
    renderScene(<OpeningLineScene {...baseProps({ description: "short" })} />);
    expect(screen.getByRole("heading", { name: /what are you building/i })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /what should i call it/i })).not.toBeInTheDocument();
  });

  it("progressively discloses the name prompt once the description clears the minimum length", () => {
    renderScene(<OpeningLineScene {...baseProps({ description: "A tool that helps restaurants reduce waste." })} />);
    expect(screen.getByRole("heading", { name: /what should i call it/i })).toBeInTheDocument();
  });

  it("submits on Enter in the name field", () => {
    const onSubmit = vi.fn();
    renderScene(
      <OpeningLineScene
        {...baseProps({ description: "A tool that helps restaurants reduce waste.", onSubmit })}
      />,
    );
    fireEvent.keyDown(screen.getByLabelText(/what should i call it/i), { key: "Enter" });
    expect(onSubmit).toHaveBeenCalled();
  });

  it("surfaces a validation error as a real alert", () => {
    renderScene(<OpeningLineScene {...baseProps({ error: "Say a little more." })} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Say a little more.");
  });
});
