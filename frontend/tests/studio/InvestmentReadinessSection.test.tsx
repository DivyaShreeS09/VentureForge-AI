import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { InvestmentReadinessSection } from "../../src/components/results/studio/InvestmentReadinessSection";
import { buildMentorInterpretation } from "../fixtures/analysisFixtures";

const FUNDING = { rubric_version: "v1", overall_score: 45, level: "developing" as const, breakdown: [], missing_evidence: [], disclaimer: "d" };

describe("InvestmentReadinessSection", () => {
  it("unifies funding readiness, evidence quality, traction, business model, and historical pattern signal", () => {
    const mentor = buildMentorInterpretation();
    render(
      <InvestmentReadinessSection
        fundingAssessment={FUNDING}
        successPrediction={null}
        founderGuidanceItems={mentor.founder_guidance_items}
        businessModelSummary={mentor.business_model}
      />,
    );
    expect(screen.getByRole("img", { name: /45 out of 100/ })).toBeInTheDocument();
    expect(screen.getByText("Evidence Quality")).toBeInTheDocument();
    expect(screen.getByText("1 of 2 dimensions confirmed")).toBeInTheDocument();
    expect(screen.getByText("Validation opportunity")).toBeInTheDocument(); // traction status
    expect(screen.getByText("No business-model synthesis was generated for this run.")).toBeInTheDocument();
    expect(screen.getByText("Not available for this run")).toBeInTheDocument();
  });

  it("renders children (e.g. the revenue estimate editor) inside the section", () => {
    render(
      <InvestmentReadinessSection
        fundingAssessment={FUNDING}
        successPrediction={null}
        founderGuidanceItems={[]}
        businessModelSummary="x"
      >
        <p>Revenue editor slot</p>
      </InvestmentReadinessSection>,
    );
    expect(screen.getByText("Revenue editor slot")).toBeInTheDocument();
  });
});
