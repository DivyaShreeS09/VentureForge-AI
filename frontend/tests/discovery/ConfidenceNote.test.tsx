import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ConfidenceNote, formatIndustryLabel } from "../../src/components/discovery/ConfidenceNote";
import type { IndustryPreview } from "../../src/types/api";

const BASE: IndustryPreview = {
  available: true,
  predicted_industry: "b2b",
  confidence: 0.82,
  is_uncertain: false,
  uncertainty_reasons: [],
  secondary_industry: null,
  secondary_confidence: null,
  model_version: "v2",
  customer_hints: [],
  detected_keywords: [],
};

describe("formatIndustryLabel", () => {
  it("upper-cases the known b2b/b2c acronym forms", () => {
    expect(formatIndustryLabel("b2b")).toBe("B2B");
    expect(formatIndustryLabel("b2c")).toBe("B2C");
  });

  it("falls back to capitalizing the first letter for any other label", () => {
    expect(formatIndustryLabel("consumer")).toBe("Consumer");
    expect(formatIndustryLabel("healthcare")).toBe("Healthcare");
  });
});

describe("ConfidenceNote", () => {
  it("renders nothing when there is nothing to say yet", () => {
    const { container } = render(<ConfidenceNote preview={null} loading={false} error={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows a quiet loading message, never a fabricated result, while waiting", () => {
    render(<ConfidenceNote preview={null} loading error={null} />);
    expect(screen.getByText(/reading what you've written/i)).toBeInTheDocument();
  });

  it("shows an honest, non-blocking message on a transport error", () => {
    render(<ConfidenceNote preview={null} loading={false} error="Couldn't reach the server." />);
    expect(screen.getByText(/couldn't reach the server/i)).toBeInTheDocument();
    expect(screen.getByText(/you can still continue/i)).toBeInTheDocument();
  });

  it("renders a confirmed-tier chip only when the backend itself is not uncertain", () => {
    render(<ConfidenceNote preview={BASE} loading={false} error={null} />);
    expect(screen.getByText(/looks like b2b/i)).toBeInTheDocument();
  });

  it("renders a not-sure-yet-tier chip when the backend itself reports uncertainty", () => {
    render(<ConfidenceNote preview={{ ...BASE, is_uncertain: true }} loading={false} error={null} />);
    expect(screen.getByText(/might be b2b — not fully sure yet/i)).toBeInTheDocument();
  });

  it("keeps showing a real previous answer instead of a loading message while a newer one is in flight", () => {
    render(<ConfidenceNote preview={BASE} loading error={null} />);
    expect(screen.getByText(/looks like b2b/i)).toBeInTheDocument();
    expect(screen.queryByText(/reading what you've written/i)).not.toBeInTheDocument();
  });

  it("never renders when the backend honestly reports unavailability", () => {
    const { container } = render(
      <ConfidenceNote preview={{ ...BASE, available: false, predicted_industry: null }} loading={false} error={null} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
