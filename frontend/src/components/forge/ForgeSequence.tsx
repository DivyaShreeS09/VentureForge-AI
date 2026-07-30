import { AnimatePresence, motion } from "framer-motion";
import { useMotionTier } from "../../motion/transitions";
import { formatIndustryLabel } from "../discovery/ConfidenceNote";
import { GlassCard } from "../../primitives";
import { ForgeCore } from "./ForgeCore";
import { deriveStageStatuses, STAGE_ORDER } from "./stageOrder";
import type { Analysis } from "../../types/api";

interface Props {
  /** The real, incrementally-updated Analysis row (see useAnalysisProgress) — null only before
   * the very first real event/poll has arrived. */
  analysis: Analysis | null;
  /** An outright connection/request failure (never reached the backend at all) — distinct from
   * `analysis.status === "FAILED"`, which is a real orchestrator failure. */
  failed?: boolean;
}

/** One honest, natural-language sentence per stage, surfaced the moment the real field it's
 * drawn from actually appears — never a synthesized "confidence" number, never text for a stage
 * that hasn't produced this field yet. This is "progressive insight generation" and "confidence
 * crystallization": each is a genuine intermediate output already in the Analysis row, just
 * revealed as soon as it's real instead of held back until the whole run finishes. */
function insightFor(stage: string, analysis: Analysis): string | null {
  switch (stage) {
    case "Understanding Your Industry": {
      const industry = analysis.industry_prediction;
      if (!industry?.predicted_industry) return null;
      const label = formatIndustryLabel(industry.predicted_industry);
      return industry.is_uncertain ? `This might be the ${label} space.` : `Looks like the ${label} space.`;
    }
    case "Scoring Your Readiness": {
      const level = analysis.funding_assessment?.level;
      if (!level) return null;
      const phrase = level === "ready" ? "well-positioned" : level === "developing" ? "developing" : "early-stage";
      return `Reading your evidence as ${phrase} right now.`;
    }
    case "Comparing Historical Patterns":
      return analysis.success_prediction?.pattern_signal_sentence ?? null;
    case "Modeling Your Revenue":
      return analysis.revenue_estimate?.scenarios ? "A base-case revenue scenario is ready." : null;
    case "Studying Your Market": {
      // This stage spans 4 real nodes (market/competitors/personas/business model) — the longest
      // silent stretch without this, since none of those fields had a mapping yet.
      const proposition = analysis.business_model?.value_proposition;
      return proposition ? `Working out the core value: ${proposition}` : null;
    }
    case "Mapping Your Growth Strategy": {
      // Spans 6 real Phase 5 nodes — surfaces the first ranked action the moment it's real.
      const topAction = analysis.student3_outputs?.ranked_actions?.[0]?.title;
      return topAction ? `A likely first priority: ${topAction}` : null;
    }
    case "Preparing Your Mentor Report":
      return analysis.judge_summary?.overall_assessment ?? null;
    default:
      return null;
  }
}

/** Act IV — "The Forging". Renders the real backend workflow (current_stage/current_node/status
 * from useAnalysisProgress) as a calm, founder-facing stage checklist plus one honest insight
 * sentence at a time — never a fabricated percentage-of-completion narrative, never a stage
 * marked done before the backend itself reports it. */
export function ForgeSequence({ analysis, failed = false }: Props) {
  const sceneTransition = useMotionTier("scene");
  const isTerminal = analysis?.status === "COMPLETED" || analysis?.status === "FAILED";
  const coreState = failed || analysis?.status === "FAILED" ? "error" : analysis?.status === "COMPLETED" ? "done" : "running";
  const stages = deriveStageStatuses(analysis?.current_stage ?? null, !!isTerminal);
  const doneCount = stages.filter((s) => s.state === "done").length;
  const progress = isTerminal ? 1 : doneCount / STAGE_ORDER.length;

  const currentInsight = analysis && !failed ? insightFor(analysis.current_stage ?? "", analysis) : null;
  const fallbackText = analysis?.current_stage ? `${analysis.current_stage}…` : "Reading what you've told me…";
  const displayText = failed ? "Something interrupted the forging — you can retry below." : (currentInsight ?? fallbackText);

  return (
    <div className="grid grid-cols-1 items-center gap-10 lg:grid-cols-[auto_1fr] lg:gap-16">
      <div className="flex justify-center">
        <ForgeCore state={coreState} progress={progress} />
      </div>

      {/* The one glass panel on this screen — Analysis is this product's "living AI command
          center" hero moment (Hero Moment Requirement), so a single floating panel over the
          ambient starfield is deliberate here, not a default applied everywhere. */}
      <GlassCard glow="accent-2" className="p-6 forge-sm:p-8">
        {/* Tailwind's preflight sets `list-style: none` globally, which in Chrome/Safari also
            silently strips the implicit ARIA list/listitem roles unless restored explicitly —
            confirmed missing in a real browser (jest-axe's static analysis doesn't catch this).
            The roles below are not actually redundant despite the lint rule's assumption. */}
        {/* eslint-disable-next-line jsx-a11y/no-redundant-roles */}
        <ol aria-label="Forging progress" role="list" className="space-y-3">
          {stages.map((stage) => (
            // eslint-disable-next-line jsx-a11y/no-redundant-roles
            <li key={stage.label} role="listitem" className="flex items-center gap-3">
              <span
                aria-hidden="true"
                className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                  stage.state === "done"
                    ? "bg-forge-confirmed"
                    : stage.state === "current"
                      ? "bg-forge-accent"
                      : "bg-forge-text/[.16]"
                }`}
              />
              <span className={`text-forge-3 ${stage.state === "upcoming" ? "text-forge-text-tertiary" : "text-forge-text"}`}>
                {stage.label}
              </span>
            </li>
          ))}
        </ol>

        <AnimatePresence mode="wait">
          <motion.p
            key={displayText}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={sceneTransition}
            role="status"
            aria-live="polite"
            className="mt-6 min-h-[1.5em] text-forge-2 text-forge-text-secondary"
          >
            {displayText}
          </motion.p>
        </AnimatePresence>
      </GlassCard>
    </div>
  );
}
