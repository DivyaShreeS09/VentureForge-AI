import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { axe } from "jest-axe";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { NewAnalysisProvider } from "../src/context/NewAnalysisContext";
import { LanguageProvider } from "../src/context/LanguageContext";
import { EvidenceCollectionPage } from "../src/pages/EvidenceCollectionPage";
import { EVIDENCE_DIMENSIONS } from "../src/components/evidence/evidenceDimensions";
import * as api from "../src/services/api";

const STORAGE_KEY = "ventureforge.newAnalysis.v2";

function seedIdea() {
  window.localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      idea: {
        name: "Nova",
        problemSolution: "A subscription analytics dashboard for retail teams.",
        targetCustomer: "",
        customerSegments: [],
        currentStage: "Just an idea",
      },
      fundingAnswers: {},
      companyMetrics: {},
      revenueAssumptions: {},
      marketEvidence: { known_competitors: [] },
      mode: "beginner",
    }),
  );
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/new/evidence"]}>
      <LanguageProvider>
        <NewAnalysisProvider>
          <Routes>
            <Route path="/new/idea" element={<p>Idea Submission (stub)</p>} />
            <Route path="/new/evidence" element={<EvidenceCollectionPage />} />
            <Route path="/startups/:id/status" element={<p>Analysis Status (stub)</p>} />
          </Routes>
        </NewAnalysisProvider>
      </LanguageProvider>
    </MemoryRouter>,
  );
}

async function answerAllEvidenceQuestions() {
  for (const dim of EVIDENCE_DIMENSIONS) {
    await screen.findByRole("heading", { name: dim.question });
    const group = screen.getByRole("radiogroup", { name: dim.question });
    fireEvent.click(within(group).getAllByRole("radio")[0]);
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
  }
  await screen.findByRole("heading", { name: /a few optional details/i });
}

describe("EvidenceCollectionPage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    seedIdea();
  });

  it("starts on the first evidence question", () => {
    renderPage();
    expect(screen.getByRole("heading", { name: EVIDENCE_DIMENSIONS[0].question })).toBeInTheDocument();
  });

  it("blocks Continue until an answer is chosen for the current question", () => {
    renderPage();
    expect(screen.getByRole("button", { name: /continue/i })).toBeDisabled();
    const group = screen.getByRole("radiogroup", { name: EVIDENCE_DIMENSIONS[0].question });
    fireEvent.click(within(group).getAllByRole("radio")[0]);
    expect(screen.getByRole("button", { name: /continue/i })).toBeEnabled();
  });

  it("acknowledges the answer honestly the moment one is chosen", () => {
    renderPage();
    const group = screen.getByRole("radiogroup", { name: EVIDENCE_DIMENSIONS[0].question });
    fireEvent.click(within(group).getAllByRole("radio")[0]);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("Back on the very first question leaves the Evidence Conversation entirely", () => {
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: /back/i }));
    expect(screen.getByText(/idea submission \(stub\)/i)).toBeInTheDocument();
  });

  it("Back after answering returns to the previous question with the answer preserved", async () => {
    renderPage();
    const firstGroup = screen.getByRole("radiogroup", { name: EVIDENCE_DIMENSIONS[0].question });
    fireEvent.click(within(firstGroup).getAllByRole("radio")[0]);
    fireEvent.click(screen.getByRole("button", { name: /continue/i }));
    await screen.findByRole("heading", { name: EVIDENCE_DIMENSIONS[1].question });

    fireEvent.click(screen.getByRole("button", { name: /back/i }));
    await screen.findByRole("heading", { name: EVIDENCE_DIMENSIONS[0].question });
    const group = screen.getByRole("radiogroup", { name: EVIDENCE_DIMENSIONS[0].question });
    expect(within(group).getAllByRole("radio")[0]).toHaveAttribute("aria-checked", "true");
  });

  it("advances through all 8 questions to the optional-details step, where Continue never blocks", async () => {
    renderPage();
    await answerAllEvidenceQuestions();
    expect(screen.getByRole("button", { name: /review & analyze/i })).toBeEnabled();
  });

  it("submits the real collected evidence and navigates on success", async () => {
    vi.spyOn(api, "createStartup").mockResolvedValue({
      id: "abc123",
      name: "Nova",
      description: "A subscription analytics dashboard for retail teams.",
      funding_answers: {},
      company_metrics: {},
      revenue_assumptions: {},
      market_evidence: {},
      customer_rfm: null,
      created_at: "",
      updated_at: "",
    });
    renderPage();
    await answerAllEvidenceQuestions();
    fireEvent.click(screen.getByRole("button", { name: /review & analyze/i }));

    await waitFor(() => expect(api.createStartup).toHaveBeenCalledTimes(1));
    const payload = vi.mocked(api.createStartup).mock.calls[0][0];
    expect(Object.keys(payload.funding_answers)).toHaveLength(EVIDENCE_DIMENSIONS.length);
  });

  it("has no accessibility violations on the first question", async () => {
    const { container } = renderPage();
    expect(await axe(container)).toHaveNoViolations();
  });

  it("derives customer_type and startup_stage from Discovery answers instead of asking again", async () => {
    window.localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        idea: {
          name: "Nova",
          problemSolution: "A subscription analytics dashboard for retail teams.",
          targetCustomer: "Retail operations managers",
          customerSegments: [],
          currentStage: "Validating",
        },
        fundingAnswers: {},
        companyMetrics: {},
        revenueAssumptions: {},
        marketEvidence: { known_competitors: [] },
        mode: "beginner",
      }),
    );
    vi.spyOn(api, "createStartup").mockResolvedValue({
      id: "abc123",
      name: "Nova",
      description: "A subscription analytics dashboard for retail teams.",
      funding_answers: {},
      company_metrics: {},
      revenue_assumptions: {},
      market_evidence: {},
      customer_rfm: null,
      created_at: "",
      updated_at: "",
    });
    renderPage();
    await answerAllEvidenceQuestions();
    fireEvent.click(screen.getByRole("button", { name: /review & analyze/i }));

    await waitFor(() => expect(api.createStartup).toHaveBeenCalledTimes(1));
    const payload = vi.mocked(api.createStartup).mock.calls[0][0];
    expect(payload.market_evidence.customer_type).toBe("Retail operations managers");
    expect(payload.market_evidence.startup_stage).toBe("Validating");
  });

  it("switching to Advanced mode reveals exact pricing and company/funding fields", async () => {
    renderPage();
    await answerAllEvidenceQuestions();
    expect(screen.queryByLabelText(/how much funding have you raised/i)).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("radio", { name: "Advanced" }));
    expect(screen.getByLabelText(/how much funding have you raised/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/price per customer/i)).toBeInTheDocument();
  });
});
