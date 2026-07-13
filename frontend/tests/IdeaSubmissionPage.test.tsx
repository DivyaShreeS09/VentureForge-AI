import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it } from "vitest";
import { NewAnalysisProvider } from "../src/context/NewAnalysisContext";
import { IdeaSubmissionPage } from "../src/pages/IdeaSubmissionPage";

function renderPage() {
  return render(
    <MemoryRouter>
      <NewAnalysisProvider>
        <IdeaSubmissionPage />
      </NewAnalysisProvider>
    </MemoryRouter>,
  );
}

describe("IdeaSubmissionPage", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("blocks advancing past step 1 without a name", () => {
    renderPage();
    fireEvent.change(screen.getByLabelText(/describe your startup idea in detail/i), {
      target: { value: "A long enough description of the idea." },
    });
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));

    expect(screen.getByRole("alert")).toHaveTextContent(/name is required/i);
    expect(screen.getByText("Basic Information")).toBeInTheDocument();
  });

  it("blocks advancing past step 1 with a too-short description", () => {
    renderPage();
    fireEvent.change(screen.getByLabelText(/startup \/ idea name/i), { target: { value: "Nova" } });
    fireEvent.change(screen.getByLabelText(/describe your startup idea in detail/i), {
      target: { value: "short" },
    });
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));

    expect(screen.getByRole("alert")).toHaveTextContent(/at least 10 characters/i);
  });

  it("advances to Business Model once step 1 is valid", () => {
    renderPage();
    fireEvent.change(screen.getByLabelText(/startup \/ idea name/i), { target: { value: "Nova" } });
    fireEvent.change(screen.getByLabelText(/describe your startup idea in detail/i), {
      target: { value: "A subscription analytics dashboard for retail teams." },
    });
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));

    expect(screen.getByRole("heading", { name: "Business Model" })).toBeInTheDocument();
  });

  it("autosaves idea fields to localStorage", () => {
    renderPage();
    fireEvent.change(screen.getByLabelText(/startup \/ idea name/i), { target: { value: "Nova" } });

    const raw = window.localStorage.getItem("ventureforge.newAnalysis.v1");
    expect(raw).toBeTruthy();
    expect(JSON.parse(raw as string).idea.name).toBe("Nova");
  });
});
