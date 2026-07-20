import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StartupSnapshot } from "../../src/components/results/studio/StartupSnapshot";
import { buildMentorInterpretation } from "../fixtures/analysisFixtures";

describe("StartupSnapshot", () => {
  it("renders all required snapshot fields", () => {
    render(
      <StartupSnapshot
        startupName="WasteLess"
        primaryDomain="Restaurant Operations Technology"
        mentor={buildMentorInterpretation()}
        fundingAssessment={{ rubric_version: "v1", overall_score: 45, level: "developing", breakdown: [], missing_evidence: [], disclaimer: "d" }}
        successPrediction={{
          pattern_signal_label: "mixed_comparison", pattern_signal_display: "Mixed comparison",
          pattern_signal_sentence: "s", predicted_label: "success", success_probability: 0.5,
          model_version: "v1", model_pipeline: "p", dataset_version: "v1", missing_features: [],
          is_uncertain: false, uncertainty_reasons: [], disclaimer: "d",
        }}
      />,
    );
    expect(screen.getByText("WasteLess")).toBeInTheDocument();
    expect(screen.getByText("Restaurant Operations Technology")).toBeInTheDocument();
    expect(screen.getByText("Independent restaurant owners.")).toBeInTheDocument();
    expect(screen.getByText("No business-model synthesis was generated for this run.")).toBeInTheDocument();
    expect(screen.getByText("Building Momentum")).toBeInTheDocument();
    expect(screen.getByText("45/100")).toBeInTheDocument();
    expect(screen.getByText("Mixed comparison")).toBeInTheDocument();
  });

  it("falls back gracefully when the startup name and success prediction are unavailable", () => {
    render(
      <StartupSnapshot
        startupName={null}
        primaryDomain={null}
        mentor={buildMentorInterpretation()}
        fundingAssessment={null}
        successPrediction={null}
      />,
    );
    expect(screen.getByText("Your Startup")).toBeInTheDocument();
    expect(screen.getByText("Not yet resolved")).toBeInTheDocument();
    expect(screen.getAllByText("Not yet assessed").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Not available for this run")).toBeInTheDocument();
  });
});
