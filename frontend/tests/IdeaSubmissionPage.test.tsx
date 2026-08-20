import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { axe } from "jest-axe";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { NewAnalysisProvider } from "../src/context/NewAnalysisContext";
import { LanguageProvider } from "../src/context/LanguageContext";
import { IdeaSubmissionPage } from "../src/pages/IdeaSubmissionPage";
import * as api from "../src/services/api";

function renderPage() {
  return render(
    <MemoryRouter>
      <LanguageProvider>
        <NewAnalysisProvider>
          <IdeaSubmissionPage />
        </NewAnalysisProvider>
      </LanguageProvider>
    </MemoryRouter>,
  );
}

describe("IdeaSubmissionPage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.spyOn(api, "previewIndustry").mockResolvedValue({
      available: false,
      predicted_industry: null,
      confidence: null,
      is_uncertain: null,
      uncertainty_reasons: [],
      secondary_industry: null,
      secondary_confidence: null,
      model_version: null,
      customer_hints: [],
      detected_keywords: [],
    });
  });

  it("starts on the Opening Line", () => {
    renderPage();
    expect(screen.getByRole("heading", { name: /what are you building/i })).toBeInTheDocument();
  });

  it("blocks Continue without a name", () => {
    renderPage();
    fireEvent.change(screen.getByLabelText(/what are you building\?/i), {
      target: { value: "A long enough description of the idea." },
    });
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    expect(screen.getByRole("alert")).toHaveTextContent(/name/i);
  });

  it("blocks Continue with a too-short description, even after the name field has appeared", async () => {
    renderPage();
    const descriptionField = screen.getByLabelText(/what are you building\?/i);
    fireEvent.change(descriptionField, { target: { value: "A long enough description to reveal the name field." } });
    fireEvent.change(await screen.findByLabelText(/what should i call it/i), { target: { value: "Nova" } });
    // Founder trims the description back down below the minimum before continuing.
    fireEvent.change(descriptionField, { target: { value: "short" } });

    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    expect(screen.getByRole("alert")).toHaveTextContent(/say a little more/i);
  });

  it("advances to Who It's For once the Opening Line is valid", async () => {
    renderPage();
    fireEvent.change(screen.getByLabelText(/what are you building\?/i), {
      target: { value: "A subscription analytics dashboard for retail teams." },
    });
    fireEvent.change(await screen.findByLabelText(/what should i call it/i), { target: { value: "Nova" } });
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));

    expect(await screen.findByLabelText(/who specifically buys or uses this/i)).toBeInTheDocument();
  });

  it("advances from Who It's For to Where You Are", async () => {
    renderPage();
    fireEvent.change(screen.getByLabelText(/what are you building\?/i), {
      target: { value: "A subscription analytics dashboard for retail teams." },
    });
    fireEvent.change(await screen.findByLabelText(/what should i call it/i), { target: { value: "Nova" } });
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    await screen.findByLabelText(/who specifically buys or uses this/i);

    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    expect(await screen.findByRole("radiogroup", { name: /where are you right now/i })).toBeInTheDocument();
  });

  it("Back steps to the previous scene", async () => {
    renderPage();
    fireEvent.change(screen.getByLabelText(/what are you building\?/i), {
      target: { value: "A subscription analytics dashboard for retail teams." },
    });
    fireEvent.change(await screen.findByLabelText(/what should i call it/i), { target: { value: "Nova" } });
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    await screen.findByLabelText(/who specifically buys or uses this/i);

    fireEvent.click(screen.getByRole("button", { name: /back/i }));
    expect(await screen.findByRole("heading", { name: /what are you building/i })).toBeInTheDocument();
  });

  it("autosaves idea fields to localStorage", () => {
    renderPage();
    fireEvent.change(screen.getByLabelText(/what are you building\?/i), { target: { value: "Nova idea text" } });

    const raw = window.localStorage.getItem("ventureforge.newAnalysis.v2");
    expect(raw).toBeTruthy();
    expect(JSON.parse(raw as string).idea.problemSolution).toBe("Nova idea text");
  });

  it("has no accessibility violations on the Opening Line", async () => {
    const { container } = renderPage();
    expect(await axe(container)).toHaveNoViolations();
  });
});
