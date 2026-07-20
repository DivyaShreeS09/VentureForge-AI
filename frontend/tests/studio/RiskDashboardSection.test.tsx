import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RiskDashboardSection } from "../../src/components/results/studio/RiskDashboardSection";
import type { StrategicRisk } from "../../src/types/api";

const RISKS: StrategicRisk[] = [
  { risk: "Low priority risk", category: "timing", why: "w", likelihood: "low", impact: "low", mitigation: "m", confidence_tier: "reasonable_hypothesis", source: "deterministic" },
  { risk: "High priority risk", category: "regulatory", why: "w2", likelihood: "high", impact: "high", mitigation: "m2", confidence_tier: "confirmed_from_evidence", source: "deterministic" },
];

describe("RiskDashboardSection", () => {
  it("sorts risks by likelihood x impact, highest priority first", () => {
    render(<RiskDashboardSection risks={RISKS} />);
    const items = screen.getAllByRole("listitem");
    expect(items[0].textContent).toContain("High priority risk");
    expect(items[1].textContent).toContain("Low priority risk");
  });

  it("shows likelihood, impact, owner, status, and mitigation for each risk", () => {
    render(<RiskDashboardSection risks={RISKS} />);
    expect(screen.getAllByText("Owner: Founder").length).toBe(2);
    expect(screen.getAllByText("Status: Open").length).toBe(2);
    expect(screen.getByText("m2")).toBeInTheDocument();
  });

  it("never presents a risk as a founder weakness", () => {
    render(<RiskDashboardSection risks={RISKS} />);
    expect(screen.queryByText(/weakness/i)).not.toBeInTheDocument();
  });

  it("shows an empty state when there are no risks", () => {
    render(<RiskDashboardSection risks={[]} />);
    expect(screen.getByText("No strategic risks identified for this run.")).toBeInTheDocument();
  });
});
