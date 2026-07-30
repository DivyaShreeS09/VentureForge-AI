import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { WhoItsForScene } from "../../src/components/discovery/WhoItsForScene";
import type { IndustryPreview } from "../../src/types/api";

const PREVIEW: IndustryPreview = {
  available: true,
  predicted_industry: "b2b",
  confidence: 0.82,
  is_uncertain: false,
  uncertainty_reasons: [],
  secondary_industry: null,
  secondary_confidence: null,
  model_version: "v2",
  customer_hints: [
    { sector: "Hotels", matched_text: ["hotel"] },
    { sector: "Restaurants", matched_text: ["restaurant"] },
  ],
  detected_keywords: ["hotel", "restaurant"],
};

function baseProps(overrides: Partial<React.ComponentProps<typeof WhoItsForScene>> = {}) {
  return {
    preview: PREVIEW,
    previewLoading: false,
    previewError: null,
    targetCustomer: "",
    customerSegments: [],
    onTargetCustomerChange: vi.fn(),
    onToggleSegment: vi.fn(),
    ...overrides,
  };
}

describe("WhoItsForScene", () => {
  it("reveals the real predicted industry, never a placeholder category", () => {
    render(<WhoItsForScene {...baseProps()} />);
    expect(screen.getByRole("heading", { name: /you're building for the b2b market/i })).toBeInTheDocument();
  });

  it("hedges the headline when the backend itself is uncertain", () => {
    render(<WhoItsForScene {...baseProps({ preview: { ...PREVIEW, is_uncertain: true } })} />);
    expect(screen.getByRole("heading", { name: /this might be the b2b market/i })).toBeInTheDocument();
  });

  it("offers only real, backend-derived customer-hint chips — never invented role labels", () => {
    render(<WhoItsForScene {...baseProps()} />);
    expect(screen.getByRole("checkbox", { name: "Hotels" })).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Restaurants" })).toBeInTheDocument();
    expect(screen.getByText(/picked up on: hotel, restaurant/i)).toBeInTheDocument();
  });

  it("falls back to the free-text field alone when no hints matched", () => {
    render(<WhoItsForScene {...baseProps({ preview: { ...PREVIEW, customer_hints: [] } })} />);
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
    expect(screen.getByLabelText(/who specifically buys or uses this/i)).toBeInTheDocument();
  });

  it("always shows the founder's-own-words field, even when hints exist", () => {
    render(<WhoItsForScene {...baseProps()} />);
    expect(screen.getByLabelText(/who specifically buys or uses this/i)).toBeInTheDocument();
  });

  it("toggles a hint chip on click", () => {
    const onToggleSegment = vi.fn();
    render(<WhoItsForScene {...baseProps({ onToggleSegment })} />);
    fireEvent.click(screen.getByRole("checkbox", { name: "Hotels" }));
    expect(onToggleSegment).toHaveBeenCalledWith("Hotels");
  });

  it("shows a neutral prompt while no industry is available yet", () => {
    render(<WhoItsForScene {...baseProps({ preview: null })} />);
    expect(screen.getByRole("heading", { name: /who's this for/i })).toBeInTheDocument();
  });
});
