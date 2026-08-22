import { motion } from "framer-motion";
import { GlassCard } from "../../primitives/GlassCard";
import type {
  Analysis,
  MentorInterpretation,
} from "../../types/api";
import { deriveFounderDecision } from "../../utils/founderDecision";
import {
  findInsight,
  type Insight,
} from "../../utils/insights";
import { useMotionTier } from "../../motion/transitions";
import { highlightKeywords } from "../../utils/highlightKeywords";

const DECISION_TONE: Record<string, string> = {
  "Should Build": "text-forge-emerald",
  "Proceed Carefully": "text-forge-notsure",
  "Needs Validation": "text-forge-notsure",
  "High Risk": "text-forge-rose",
};

interface Props {
  analysis: Analysis;
  mentor: MentorInterpretation;
  startupName: string | null;
  insights: Insight[];
}

/** Section 1 of 5 — Executive Command Center. */
export function ExecutiveCommandCenter({
  analysis,
  mentor,
  startupName,
  insights,
}: Props) {
  const decision =
    deriveFounderDecision(mentor);

  const tone =
    DECISION_TONE[
      decision.label
    ] ?? "text-forge-text";

  const industry =
    analysis.industry_prediction
      ?.primary_industry ??
    analysis.industry_prediction
      ?.predicted_industry ??
    null;

  const stage =
    mentor.founder_report
      ?.executive_verdict
      .current_stage.content ??
    null;

  const rawSuccessPct =
    analysis.success_prediction
      ? Math.round(
          analysis
            .success_prediction
            .success_probability *
            100,
        )
      : null;

  const successPct =
    rawSuccessPct !== null &&
    Number.isFinite(
      rawSuccessPct,
    )
      ? rawSuccessPct
      : null;

  const fundingScore =
    analysis
      .funding_assessment
      ?.overall_score ?? null;

  const strength =
    findInsight(
      insights,
      "insight-biggest-strength",
    );

  const risk =
    findInsight(
      insights,
      "insight-biggest-risk",
    );

  const priority =
    findInsight(
      insights,
      "insight-immediate-priority",
    );

  const verdictText =
    mentor.mentor_verdict
      .concise_verdict;

  const strengthText =
    strength?.why ?? "";

  const riskText =
    risk?.why ?? "";

  const priorityText =
    priority?.why ?? "";

  const stagger =
    useMotionTier("scene");

  return (
    <section
      id="section-command-center"
      className="mx-auto flex min-h-[100dvh] w-full max-w-[1100px] flex-col justify-center px-6 py-16 forge-sm:px-10"
    >
      {/* VENTURE IDENTITY */}

      <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
        <h1 className="animate-breathe text-balance bg-gradient-to-br from-white via-forge-gold to-[#e0a93f] bg-clip-text font-forge-serif text-forge-8 font-bold leading-[1.05] text-transparent [filter:drop-shadow(0_0_28px_rgba(255,200,87,0.35))] [text-shadow:0_2px_18px_rgba(255,200,87,0.25)] forge-sm:text-forge-9">
          {startupName ??
            "Your Venture"}
        </h1>

        {industry && (
          <span className="text-forge-2 uppercase tracking-[0.15em] text-forge-helper">
            {industry}
          </span>
        )}

        {stage && (
          <span className="text-forge-2 uppercase tracking-[0.15em] text-forge-helper">
            · {stage}
          </span>
        )}
      </div>

      {/* AI VERDICT */}

      <p className="mt-5 max-w-[62ch] text-balance font-forge-serif text-forge-5 font-medium leading-[1.35] text-forge-heading">
        {highlightKeywords(
          verdictText,
        )}
      </p>

      {/* DECISION / SCORE CARD */}

      <GlassCard
        interactive
        glow="accent-2"
        className="mt-8 flex flex-wrap items-center gap-x-8 gap-y-4 px-6 py-5 forge-sm:px-8"
      >
        {/* Investment decision */}

        <div>
          <p className="text-forge-1 uppercase tracking-[0.15em] text-forge-label">
            Investment ready?
          </p>

          <p
            className={`mt-1 font-forge-serif text-forge-5 font-semibold ${tone}`}
          >
            {decision.label}
          </p>
        </div>

        {/* Success probability */}

        {successPct !==
          null && (
          <div>
            <p className="text-forge-1 uppercase tracking-[0.15em] text-forge-label">
              Success probability
            </p>

            <p className="mt-1 font-forge-serif text-forge-5 font-semibold text-forge-gold">
              {successPct}%
            </p>
          </div>
        )}

        {/* Funding readiness */}

        {fundingScore !==
          null && (
          <div>
            <p className="text-forge-1 uppercase tracking-[0.15em] text-forge-label">
              Funding readiness
            </p>

            <p className="mt-1 font-forge-serif text-forge-5 font-semibold text-forge-gold">
              {fundingScore}/100
            </p>
          </div>
        )}
      </GlassCard>

      {/* BIGGEST STRENGTH / RISK / PRIORITY */}

      <motion.div
        initial="hidden"
        animate="show"
        variants={{
          hidden: {},
          show: {
            transition: {
              staggerChildren:
                0.06,
            },
          },
        }}
        className="mt-6 grid grid-cols-1 gap-px overflow-hidden rounded-forge-lg bg-forge-text/[.08] forge-sm:grid-cols-3"
      >
        {/* Biggest strength */}

        <motion.div
          id={strength?.id}
          variants={{
            hidden: {
              opacity: 0,
              y: 8,
            },
            show: {
              opacity: 1,
              y: 0,
              transition:
                stagger,
            },
          }}
          className="scroll-mt-24 bg-forge-canvas px-5 py-4"
        >
          <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-emerald">
            Biggest strength
          </p>

          <p className="mt-1 text-forge-2 font-medium text-forge-desc">
            {highlightKeywords(
              strengthText,
            )}
          </p>
        </motion.div>

        {/* Biggest risk */}

        <motion.div
          id={risk?.id}
          variants={{
            hidden: {
              opacity: 0,
              y: 8,
            },
            show: {
              opacity: 1,
              y: 0,
              transition:
                stagger,
            },
          }}
          className="scroll-mt-24 bg-forge-canvas px-5 py-4"
        >
          <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-rose">
            Biggest risk
          </p>

          <p className="mt-1 text-forge-2 font-medium text-forge-desc">
            {highlightKeywords(
              riskText,
            )}
          </p>
        </motion.div>

        {/* Immediate next step */}

        <motion.div
          id={priority?.id}
          variants={{
            hidden: {
              opacity: 0,
              y: 8,
            },
            show: {
              opacity: 1,
              y: 0,
              transition:
                stagger,
            },
          }}
          className="scroll-mt-24 bg-forge-canvas px-5 py-4"
        >
          <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-cyan">
            Immediate next step
          </p>

          <p className="mt-1 text-forge-2 font-medium text-forge-desc">
            {highlightKeywords(
              priorityText,
            )}
          </p>
        </motion.div>
      </motion.div>
    </section>
  );
}