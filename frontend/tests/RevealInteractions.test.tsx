import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PositioningCorrection } from "../src/components/reveal/PositioningCorrection";
import { RevenueScenarios } from "../src/components/reveal/RevenueScenarios";
import type { RevenueEstimate } from "../src/types/api";

function mockFetch(handlers: { taxonomy?: () => unknown; revenuePatch?: () => unknown | Promise<never> }) {
  return vi.fn((url: string) => {
    if (typeof url === "string" && url.includes("/taxonomy")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => handlers.taxonomy?.() ?? { taxonomy_version: "v1", domains: [], allowed_secondary_domains: [] },
      });
    }
    if (typeof url === "string" && url.includes("/revenue-assumptions")) {
      if (!handlers.revenuePatch) {
        return Promise.resolve({ ok: false, status: 500, json: async () => ({ detail: "server error" }) });
      }
      const result = handlers.revenuePatch();
      return Promise.resolve({ ok: true, status: 200, json: async () => result });
    }
    return Promise.resolve({ ok: false, status: 404, json: async () => ({ detail: "not found" }) });
  });
}

describe("PositioningCorrection — taxonomy loading (moved from AnalysisResult)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows a loading state, then populates the dropdown from the live taxonomy endpoint", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        taxonomy: () => ({
          taxonomy_version: "v1",
          domains: [
            { id: "Payments Infrastructure", label: "Payments Infrastructure", description: "", deployment_sectors: [] },
            { id: "EdTech", label: "EdTech", description: "", deployment_sectors: [] },
          ],
          allowed_secondary_domains: ["Payments Infrastructure", "EdTech"],
        }),
      }),
    );

    render(<PositioningCorrection analysisId="a1" currentPrimaryDomain="Payments Infrastructure" onCorrected={vi.fn()} />);
    expect(screen.getByText(/Loading available positioning domains/)).toBeInTheDocument();

    await waitFor(() => expect(screen.queryByText(/Loading available positioning domains/)).not.toBeInTheDocument());
    const select = screen.getByLabelText("Not the right industry?") as HTMLSelectElement;
    expect(Array.from(select.options).map((o) => o.value)).toEqual(["Payments Infrastructure", "EdTech"]);
  });

  it("degrades to a minimal fallback list and surfaces an error when the taxonomy fetch fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.reject(new TypeError("network down"))),
    );

    render(<PositioningCorrection analysisId="a1" currentPrimaryDomain="Payments Infrastructure" onCorrected={vi.fn()} />);
    await waitFor(() => expect(screen.getByText(/Could not load the full taxonomy/)).toBeInTheDocument());
    expect((screen.getByLabelText("Not the right industry?") as HTMLSelectElement).options.length).toBeGreaterThan(0);
  });
});

const revenueEstimate: RevenueEstimate = {
  engine_version: "v2-deterministic-with-defaults",
  revenue_defaults_version: "v1",
  available: true,
  default_basis: "domain_default",
  missing_assumptions: ["price_per_customer_usd", "initial_customers", "monthly_growth_rate_pct", "gross_margin_pct"],
  assumptions: {
    price_per_customer_usd: { value: 99, unit: "USD/month", assumption_source: "suggested_default", explanation: "A starting point.", editable: true },
    initial_customers: { value: 5, unit: "customers", assumption_source: "suggested_default", explanation: "A starting point.", editable: true },
    monthly_growth_rate_pct: { value: 8, unit: "%/month", assumption_source: "suggested_default", explanation: "A starting point.", editable: true },
    gross_margin_pct: { value: 70, unit: "%", assumption_source: "suggested_default", explanation: "A starting point.", editable: true },
  },
  scenarios: {
    conservative: { annual_revenue_usd: 1000, annual_gross_profit_usd: 700, month_12_customers: 8, month_12_monthly_revenue_usd: 90 },
    base: { annual_revenue_usd: 1200, annual_gross_profit_usd: 840, month_12_customers: 10, month_12_monthly_revenue_usd: 120 },
    optimistic: { annual_revenue_usd: 1500, annual_gross_profit_usd: 1050, month_12_customers: 13, month_12_monthly_revenue_usd: 150 },
  },
  disclaimer: "Deterministic scenario calculator, not a trained model.",
};

describe("RevenueScenarios — revenue assumption save flow (moved from AnalysisResult)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("distinguishes an unsaved edit preview from persisted values, and clears the banner on successful save", async () => {
    vi.stubGlobal(
      "fetch",
      mockFetch({
        revenuePatch: () => ({
          revenue_estimate: {
            ...revenueEstimate,
            assumptions: {
              ...revenueEstimate.assumptions,
              price_per_customer_usd: { value: 250, unit: "USD/month", assumption_source: "user_supplied", explanation: "Founder-supplied assumption.", editable: true },
            },
          },
        }),
      }),
    );

    render(<RevenueScenarios analysisId="a1" revenueEstimate={revenueEstimate} onSaved={vi.fn()} />);
    const priceInput = screen.getByLabelText("Price / customer") as HTMLInputElement;

    fireEvent.change(priceInput, { target: { value: "250" } });
    expect(screen.getByText(/Unsaved preview/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Save assumptions/ }));
    await waitFor(() => expect(screen.queryByText(/Unsaved preview/)).not.toBeInTheDocument());
  });

  it("keeps the founder's draft visible and shows an error when the save request fails", async () => {
    vi.stubGlobal("fetch", mockFetch({}));

    render(<RevenueScenarios analysisId="a1" revenueEstimate={revenueEstimate} onSaved={vi.fn()} />);
    const priceInput = screen.getByLabelText("Price / customer") as HTMLInputElement;
    fireEvent.change(priceInput, { target: { value: "310" } });

    fireEvent.click(screen.getByRole("button", { name: /Save assumptions/ }));
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());

    expect((screen.getByLabelText("Price / customer") as HTMLInputElement).value).toBe("310");
  });
});
