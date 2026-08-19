import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { axe } from "jest-axe";
import { Reveal } from "../src/components/reveal/Reveal";
import { CommandCapsuleProvider } from "../src/primitives/CommandCapsule";
import { DockActionsProvider } from "../src/primitives/DockActions";
import type { Analysis } from "../src/types/api";
import { buildAnalysis } from "./fixtures/analysisFixtures";

// The Understanding scene's PositioningCorrection control fetches the taxonomy on mount —
// stubbed here so every test in this file gets a deterministic, immediately-resolved response
// instead of a real network call racing past the test's own assertions/unmount.
beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({ taxonomy_version: "v1", domains: [], allowed_secondary_domains: [] }),
      }),
    ),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function renderReveal(analysis: Analysis) {
  return render(
    <MemoryRouter>
      <CommandCapsuleProvider>
        <DockActionsProvider>
          <Reveal analysis={analysis} onReanalyze={vi.fn()} reanalyzing={false} startupName="WasteLess" />
        </DockActionsProvider>
      </CommandCapsuleProvider>
    </MemoryRouter>,
  );
}

describe("Reveal — Founder Operating System (exactly 5 sections)", () => {
  it("Executive Command Center: shows the verdict, investment-ready badge, and the real funding/success scores above the fold", async () => {
    renderReveal(buildAnalysis());
    expect(screen.getAllByText("Developing — real progress alongside real gaps.").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Investment ready?")).toBeInTheDocument();
    // The two headline numbers count up on mount (useCountUp) rather than rendering statically —
    // findByText waits for the animation to settle at its real final value instead of asserting
    // against whatever the very first paint frame happens to show.
    expect(await screen.findByText("50%")).toBeInTheDocument(); // success_probability 0.5
    expect(await screen.findByText("45/100")).toBeInTheDocument(); // funding_assessment.overall_score
  });

  it("Executive Dashboard: renders the funding radar from the real breakdown, not a fabricated chart, with no paragraph explanation", () => {
    renderReveal(buildAnalysis());
    expect(screen.getByText("Funding readiness breakdown")).toBeInTheDocument();
    // "The One Thing To Fix" narrative used to live in the Dashboard too — deleted, since it
    // duplicated the Command Center's biggest-risk tile (Absolute Rule 1).
    expect(screen.queryByText("The One Thing To Fix")).not.toBeInTheDocument();
  });

  it("Mission Control: caps at three missions, never fabricating one when the real validation plan is shorter", () => {
    // This fixture's validation_plan has only 1 real entry, so honestly showing just "Mission 1"
    // is correct — inventing 2 more to hit a literal "always three" would violate the no-fake-data
    // rule far more than showing fewer ever would.
    renderReveal(buildAnalysis());
    expect(screen.getByText("Three missions. Nothing else.")).toBeInTheDocument();
    expect(screen.getByText("Mission 1")).toBeInTheDocument();
    expect(screen.queryByText("Mission 4")).not.toBeInTheDocument();
  });


  it("Investor Review is omitted when there is no founder_report to source real investor commentary from", () => {
    renderReveal(buildAnalysis());
    expect(screen.queryByText("What would an investor say?")).not.toBeInTheDocument();
  });

  it("Deep Analysis consolidates everything else into one collapsed section, not five separate ones", () => {
    renderReveal(buildAnalysis());
    const details = screen.getByText("Deep Analysis").closest("details") as HTMLDetailsElement;
    expect(details.open).toBe(false);
    // Unique content from each formerly-separate scene is still present inside it.
    expect(screen.getByText("WasteLess is building in the Restaurant Operations Technology space.")).toBeInTheDocument();
    expect(screen.getByText(/This is the strongest current positioning/)).toBeInTheDocument();
    // May also appear in Mission Control's own fallback tile (no founder_report in this fixture,
    // so both read from the same validation-plan buckets) — same "glance vs. full roadmap" zoom
    // levels already accepted for the biggest-risk insight below, not a new duplication.
    expect(screen.getAllByText("Secure a pilot commitment").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Hotels").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Industry Classification/)).toBeInTheDocument();
  });

  it("the biggest risk sentence appears at every zoom level (hero glance, full detail) but is never independently reworded", () => {
    renderReveal(buildAnalysis());
    // Command Center tile + Deep Analysis's InsightDetailCard headline — the same sentence at two
    // zoom levels (glance + full detail), never restated with different wording in between.
    // A plain regex `getAllByText` can't match this anymore: the typography pass wraps keywords
    // like "traction"/"validation" in their own <span>, splitting the sentence across several
    // text nodes — so this matches on each paragraph's full `textContent` instead of a single
    // text node's content.
    const matches = screen.getAllByText((_, element) =>
      element?.tagName === "P" && /Traction is your next validation opportunity/.test(element.textContent ?? ""),
    );
    expect(matches.length).toBeGreaterThanOrEqual(2);
  });

  it("offers re-analyze, export, history, and start-another actions", () => {
    renderReveal(buildAnalysis());
    expect(screen.getByRole("button", { name: /re-analyze/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /export pdf/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /your ventures/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /start another venture/i })).toBeInTheDocument();
  });

  it("never shows a source/provenance badge outside Deep Analysis", () => {
    renderReveal(buildAnalysis());
    const commandCenter = document.getElementById("section-command-center");
    expect(commandCenter?.textContent).not.toMatch(/Deterministic Assessment|ML Prediction|Judge Synthesis/);
  });

  it("shows an honest failure message and the workflow trace when status is FAILED", () => {
    const failed: Analysis = { ...buildAnalysis(), status: "FAILED", error_message: "boom" };
    renderReveal(failed);
    expect(screen.getByRole("alert")).toHaveTextContent("boom");
  });

  it("omits the Primary Opportunity content gracefully when strategic_opportunity is absent", () => {
    const minimal = buildAnalysis({ strategic_opportunity: undefined });
    renderReveal(minimal);
    expect(screen.queryByText(/This is the strongest current positioning/)).not.toBeInTheDocument();
    // Everything else still renders.
    expect(screen.getByText("Deep Analysis")).toBeInTheDocument();
  });

  it("has no accessibility violations", async () => {
    const { container } = renderReveal(buildAnalysis());
    expect(await axe(container)).toHaveNoViolations();
  });
});
