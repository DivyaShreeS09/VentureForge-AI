import {
  useCallback,
  useMemo,
  useRef,
  useState,
} from "react";
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
import { voiceAgent } from "../voice/VoiceAgent";

const TOP_LEVEL_SECTIONS = [
  {
    id: "section-command-center",
    label: "Command Center",
  },
  {
    id: "section-dashboard",
    label: "Dashboard",
  },
  {
    id: "section-mission-control",
    label: "Mission Control",
  },
  {
    id: "section-investor-review",
    label: "Investor Review",
  },
];

const EXPORT_PDF_ICON = (
  <svg
    viewBox="0 0 24 24"
    className="h-5 w-5"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
    aria-hidden="true"
  >
    <path
      d="M12 3v12m0 0-4-4m4 4 4-4"
      strokeLinecap="round"
      strokeLinejoin="round"
    />

    <path
      d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

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
  const [
    correctedAnalysis,
    setCorrectedAnalysis,
  ] = useState<Analysis | null>(null);

  /*
   * Contains every visible result section.
   *
   * The single speaker reads from this container.
   */
  const resultContentRef =
    useRef<HTMLDivElement>(null);

  const effective =
    correctedAnalysis ?? analysis;

  const {
    mentor_interpretation: mentor,
    judge_summary,
  } = effective;

  const insights = useMemo(
    () =>
      mentor
        ? buildInsights(
            effective,
            mentor,
          )
        : [],
    [effective, mentor],
  );

  useRegisterCommandSections(
    TOP_LEVEL_SECTIONS,
  );

  const exportPdf =
    useCallback(async () => {
      const {
        generateAnalysisPdf,
      } = await import(
        "../../utils/generatePdf"
      );

      await generateAnalysisPdf(
        effective,
        startupName,
      );
    }, [
      effective,
      startupName,
    ]);

  const canExportPdf =
    analysis.status ===
      "COMPLETED" &&
    Boolean(mentor);

  const dockAction = useMemo(
    () =>
      canExportPdf
        ? {
            id: "export-pdf",
            label: "Export PDF",
            icon: EXPORT_PDF_ICON,
            onClick: exportPdf,
          }
        : null,
    [canExportPdf, exportPdf],
  );

  useRegisterDockAction(
    dockAction,
  );

  /*
   * ONE SPEAKER FOR THE WHOLE RESULT PAGE.
   *
   * Instead of manually rebuilding every AI result,
   * we read the actual rendered page text.
   *
   * So dynamically generated:
   * - verdict
   * - scores
   * - strengths
   * - risks
   * - recommendations
   * - investor feedback
   * - missions
   * - deep analysis
   *
   * are all spoken automatically.
   */
  function speakWholeResult() {
    const container =
      resultContentRef.current;

    if (!container) {
      return;
    }

    let pageText =
      container.innerText;

    /*
     * Remove speaker symbols if any old child
     * speaker still exists while we clean them.
     */
    pageText = pageText
      .replace(/🔊/g, " ")
      .replace(/🔇/g, " ")
      .replace(/\s+/g, " ")
      .trim();

    if (!pageText) {
      return;
    }

    /*
     * Stop previous speech first.
     */
    if (
      "speechSynthesis" in
      window
    ) {
      window.speechSynthesis.cancel();
    }

    voiceAgent.speak(
      pageText,
      {
        rate: 0.85,
        pitch: 1,
        volume: 1,
        lang: "en-US",
      },
    );
  }

  /*
   * FAILED ANALYSIS
   */
  if (
    analysis.status ===
    "FAILED"
  ) {
    return (
      <main className="min-h-[100dvh] font-forge-sans">
        <div className="mx-auto max-w-[860px] px-6 py-20 forge-sm:px-10">
          <p
            role="alert"
            className="text-forge-3 text-forge-risk"
          >
            Analysis failed:{" "}
            {
              analysis.error_message
            }
          </p>

          <div className="mt-8">
            <p className="text-forge-1 uppercase tracking-[0.25em] text-forge-text-secondary">
              Workflow Trace
            </p>

            <div className="mt-4">
              <WorkflowTrace
                trace={
                  analysis.workflow_trace
                }
              />
            </div>
          </div>
        </div>
      </main>
    );
  }

  /*
   * NO MENTOR RESULT
   */
  if (!mentor) {
    return (
      <main className="min-h-[100dvh] font-forge-sans">
        <div className="mx-auto max-w-[860px] px-6 py-20 forge-sm:px-10">
          <p className="text-forge-3 text-forge-text-secondary">
            This analysis has no
            mentor interpretation
            to reveal.
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="relative min-h-[100dvh] font-forge-sans">

      {/* =========================================
          ONE SPEAKER FOR THE WHOLE RESULTS PAGE
          ========================================= */}

      <div className="sticky top-4 z-50 mx-auto flex w-full max-w-[1100px] justify-end px-6 pointer-events-none forge-sm:px-10">
        <button
          type="button"
          onClick={
            speakWholeResult
          }
          aria-label="Read entire analysis aloud"
          title="Read entire analysis aloud"
          className="pointer-events-auto flex h-12 w-12 items-center justify-center rounded-full border border-white/10 bg-forge-canvas/90 text-xl shadow-lg backdrop-blur-md transition hover:bg-white/10 active:scale-95"
        >
          🔊
        </button>
      </div>

      {/* =========================================
          ALL RESULT CONTENT
          ========================================= */}

      <div
        ref={resultContentRef}
      >
        <ExecutiveCommandCenter
          analysis={effective}
          mentor={mentor}
          startupName={
            startupName
          }
          insights={insights}
        />

        <ExecutiveDashboard
          analysis={effective}
        />

        <MissionControl
          mentor={mentor}
          rankedActions={
            effective
              .student3_outputs
              ?.ranked_actions ??
            []
          }
        />

        {mentor.founder_report && (
          <InvestorReview
            report={
              mentor.founder_report
            }
            mentor={mentor}
          />
        )}

        <DeepAnalysis
          effective={
            effective
          }
          mentor={mentor}
          positioning={
            judge_summary
              ?.venture_positioning ??
            null
          }
          insights={insights}
          rankedActions={
            effective
              .student3_outputs
              ?.ranked_actions ??
            []
          }
          onCorrected={
            setCorrectedAnalysis
          }
          onSaved={
            setCorrectedAnalysis
          }
        />

        <ContinueBuildingScene
          analysis={effective}
          onReanalyze={
            onReanalyze
          }
          reanalyzing={
            reanalyzing
          }
          startupName={
            startupName
          }
        />
      </div>
    </main>
  );
}