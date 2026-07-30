import { render, screen, fireEvent } from "@testing-library/react";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";
import { AdditionalDetailsScene } from "../../src/components/evidence/AdditionalDetailsScene";

function baseProps(overrides: Partial<React.ComponentProps<typeof AdditionalDetailsScene>> = {}) {
  return {
    mode: "beginner" as const,
    companyMetrics: {},
    revenueAssumptions: {},
    marketEvidence: { known_competitors: [] },
    onCompanyMetricsChange: vi.fn(),
    onRevenueAssumptionsChange: vi.fn(),
    onMarketEvidenceChange: vi.fn(),
    ...overrides,
  };
}

describe("AdditionalDetailsScene", () => {
  it("frames every field as optional", () => {
    render(<AdditionalDetailsScene {...baseProps()} />);
    expect(screen.getByText(/optional/i)).toBeInTheDocument();
  });

  it("hides company & funding history fields in Beginner mode", () => {
    render(<AdditionalDetailsScene {...baseProps({ mode: "beginner" })} />);
    expect(screen.queryByLabelText(/total funding raised/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/gross margin/i)).not.toBeInTheDocument();
  });

  it("shows company & funding history fields, and exact pricing, only in Advanced mode", () => {
    render(<AdditionalDetailsScene {...baseProps({ mode: "advanced" })} />);
    expect(screen.getByLabelText(/total funding raised/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/price per customer/i)).toBeInTheDocument();
  });

  it("reports a numeric value as a real number", () => {
    const onCompanyMetricsChange = vi.fn();
    render(<AdditionalDetailsScene {...baseProps({ mode: "advanced", onCompanyMetricsChange })} />);
    fireEvent.change(screen.getByLabelText(/total funding raised/i), { target: { value: "50000" } });
    expect(onCompanyMetricsChange).toHaveBeenCalledWith({ total_funding_usd: 50000 });
  });

  it("reports null (never NaN) when a previously-filled field is cleared", () => {
    const onCompanyMetricsChange = vi.fn();
    render(
      <AdditionalDetailsScene
        {...baseProps({ mode: "advanced", companyMetrics: { total_funding_usd: 50000 }, onCompanyMetricsChange })}
      />,
    );
    fireEvent.change(screen.getByLabelText(/total funding raised/i), { target: { value: "" } });
    expect(onCompanyMetricsChange).toHaveBeenCalledWith({ total_funding_usd: null });
  });

  it("Beginner mode picks a representative price from a tier, not exact entry", () => {
    const onRevenueAssumptionsChange = vi.fn();
    render(<AdditionalDetailsScene {...baseProps({ mode: "beginner", onRevenueAssumptionsChange })} />);
    fireEvent.click(screen.getByRole("radio", { name: /\$20–100\/mo/i }));
    expect(onRevenueAssumptionsChange).toHaveBeenCalledWith({ price_per_customer_usd: 50 });
  });

  it("never asks Target market or Customer type again — already collected in Discovery", () => {
    render(<AdditionalDetailsScene {...baseProps()} />);
    expect(screen.queryByLabelText(/^target market$/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/^customer type$/i)).not.toBeInTheDocument();
  });

  it("collects competitors as removable tags, not a comma-separated string", () => {
    const onMarketEvidenceChange = vi.fn();
    render(
      <AdditionalDetailsScene
        {...baseProps({ marketEvidence: { known_competitors: ["Acme"] }, onMarketEvidenceChange })}
      />,
    );
    expect(screen.getByText("Acme")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /remove acme/i })).toBeInTheDocument();
  });

  it("has no accessibility violations in Beginner mode", async () => {
    const { container } = render(<AdditionalDetailsScene {...baseProps({ mode: "beginner" })} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("has no accessibility violations in Advanced mode", async () => {
    const { container } = render(<AdditionalDetailsScene {...baseProps({ mode: "advanced" })} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});
