import { useCallback, useMemo, useState } from "react";
import type { Analysis } from "../../types/api";
import { useRegisterCommandSections } from "../../primitives/CommandCapsule";
import { useRegisterDockAction } from "../../primitives/DockActions";
import { buildInsights } from "../../utils/insights";
import { WorkflowTrace } from "./WorkflowTrace";
import { ExecutiveCommandCenter } from "./ExecutiveCommandCenter";
import { ExecutiveDashboard } from "./ExecutiveDashboard";
import { MissionControl } from "./MissionControl";
import { InvestorReview } from "./InvestorReview";
import { DeepAnalysis } from "./DeepAnalysis";
import { ContinueBuildingScene } from "./scenes/ContinueBuildingScene";

const TOP_LEVEL_SECTIONS = [
  { id: "section-command-center", label: "Command Center" },
  { id: "section-dashboard", label: "Dashboard" },
  { id: "section-mission-control", label: "Mission Control" },
  { id: "section-investor-review", label: "Investor Review" },
];

// Hoisted so its identity never changes across renders — kept out of the memoized dock-action
// object below purely for readability, not because a fresh `<svg>` element would itself be
// unstable (JSX elements are cheap to recreate); the action object as a whole still needs a
// stable reference (see the `useMemo` at its call site) or `useRegisterDockAction`'s effect
// re-fires on every render, which was found to make an entire test file hang.
const EXPORT_PDF_ICON = (
  <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
    <path d="M12 3v12m0 0-4-4m4 4 4-4" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

/** Act V — The Reveal, rebuilt as exactly 5 sections, each answering exactly one question:
 * Executive Command Center ("what is my company today?"), Executive Dashboard ("what do I
 * measure?"), Mission Control ("what should I do next?"), Investor Review ("what would an
 * investor say?"), Deep Analysis ("why?"). Every recurring fact (biggest risk, biggest strength,
 * immediate priority, each mission) is derived exactly once by `buildInsights` and referenced
 * everywhere else by anchor — never restated. Every section still reads only fields the backend
 * already computes. */
export function Reveal({
  analysis,
  onReanalyze,
  reanalyzing,
  startupName = null,
}: {
  analysis: Analysis;
  onReanalyze: () => void;
  reanalyzing: boolean;
  startupName?: string | null;
}) {
  const [correctedAnalysis, setCorrectedAnalysis] = useState<Analysis | null>(null);
  const effective = correctedAnalysis ?? analysis;
  const { mentor_interpretation: mentor, judge_summary } = effective;

  const insights = useMemo(() => (mentor ? buildInsights(effective, mentor) : []), [effective, mentor]);

  // Single page-level registration: `CommandCapsule`'s shared section list is replaced, not
  // merged, on every `useRegisterCommandSections` call, so exactly one place may own it.
  useRegisterCommandSections(TOP_LEVEL_SECTIONS);

  const exportPdf = useCallback(async () => {
    const { generateAnalysisPdf } = await import("../../utils/generatePdf");
    await generateAnalysisPdf(effective, startupName);
  }, [effective, startupName]);

  const canExportPdf = analysis.status === "COMPLETED" && Boolean(mentor);
  const dockAction = useMemo(
    () => (canExportPdf ? { id: "export-pdf", label: "Export PDF", icon: EXPORT_PDF_ICON, onClick: exportPdf } : null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [canExportPdf, exportPdf],
  );
  useRegisterDockAction(dockAction);

  if (analysis.status === "FAILED") {
    return (
      // No opaque `bg-forge-canvas` here — the global RootLayout mounts a "report" variant
      // AmbientBackground (report-background.jpg) behind every /analyses/:id route, and an
      // opaque color here would sit above that fixed layer in the stacking order and hide it
      // completely.
      <main className="min-h-[100dvh] font-forge-sans">
        <div className="mx-auto max-w-[860px] px-6 py-20 forge-sm:px-10">
          <p role="alert" className="text-forge-3 text-forge-risk">
            Analysis failed: {analysis.error_message}
          </p>
          <div className="mt-8">
            <p className="text-forge-1 uppercase tracking-[0.25em] text-forge-text-secondary">Workflow Trace</p>
            <div className="mt-4">
              <WorkflowTrace trace={analysis.workflow_trace} />
            </div>
          </div>
        </div>
      </main>
    );
  }

  if (!mentor) {
    return (
      // No opaque `bg-forge-canvas` here — the global RootLayout mounts a "report" variant
      // AmbientBackground (report-background.jpg) behind every /analyses/:id route, and an
      // opaque color here would sit above that fixed layer in the stacking order and hide it
      // completely.
      <main className="min-h-[100dvh] font-forge-sans">
        <div className="mx-auto max-w-[860px] px-6 py-20 forge-sm:px-10">
          <p className="text-forge-3 text-forge-text-secondary">This analysis has no mentor interpretation to reveal.</p>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-[100dvh] font-forge-sans">
      <ExecutiveCommandCenter analysis={effective} mentor={mentor} startupName={startupName} insights={insights} />
      <ExecutiveDashboard analysis={effective} />
      <MissionControl mentor={mentor} rankedActions={effective.student3_outputs?.ranked_actions ?? []} />
      {mentor.founder_report && <InvestorReview report={mentor.founder_report} mentor={mentor} />}
      <DeepAnalysis
        effective={effective}
        mentor={mentor}
        positioning={judge_summary?.venture_positioning ?? null}
        insights={insights}
        rankedActions={effective.student3_outputs?.ranked_actions ?? []}
        onCorrected={setCorrectedAnalysis}
        onSaved={setCorrectedAnalysis}
      />
      <ContinueBuildingScene analysis={effective} onReanalyze={onReanalyze} reanalyzing={reanalyzing} startupName={startupName} />
    </main>
  );
}
