import { motion } from "framer-motion";
import { useMotionTier } from "../../motion/transitions";
import { computeEvidenceStrength } from "./evidenceDimensions";
import type { FundingAnswers } from "../../types/api";

interface Props {
  answers: FundingAnswers;
}

/** Confidence evolution — a single quiet line and slim bar, not a glowing dashboard gauge (the
 * pre-Sprint-5 accordion's radial gauge was decoration; Design System Bible §11/§13 call for
 * exactly this shape: a fact stated once, the fill doing the rest). Mirrors the same
 * `funding_readiness.py` renormalization already used elsewhere — never a synthesized number. */
export function UnderstandingMeter({ answers }: Props) {
  const transition = useMotionTier("scene");
  const percent = computeEvidenceStrength(answers);
  const answeredCount = Object.keys(answers).length;

  if (answeredCount === 0) return null;

  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-forge-1 text-forge-text-tertiary">Evidence strength so far: {percent}%</p>
      <div className="h-1 w-full max-w-[220px] overflow-hidden rounded-full bg-forge-text/[.12]">
        <motion.div
          className="h-full rounded-full bg-forge-accent-2"
          initial={false}
          animate={{ width: `${percent}%` }}
          transition={transition}
        />
      </div>
    </div>
  );
}
