import { motion } from "framer-motion";
import { useMotionTier } from "../motion/transitions";

export interface ProgressFilamentProps {
  /** 0–1. No percentage or step-count label is ever rendered alongside this — the
   * Discovery Act's only progress indicator is the fill itself (Design System Bible
   * §7). */
  progress: number;
}

// Design System Bible §7 — a 2px line across the top of the viewport, filling
// left-to-right in the accent color against a 12%-opacity track. The Discovery Act's
// only progress indicator.
export function ProgressFilament({ progress }: ProgressFilamentProps) {
  const transition = useMotionTier("scene");
  const clamped = Math.min(1, Math.max(0, progress));

  return (
    <div
      role="progressbar"
      aria-valuenow={Math.round(clamped * 100)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label="Progress through this section"
      className="fixed inset-x-0 top-0 z-40 h-[3px] bg-forge-text/[.08]"
    >
      <motion.div
        className="relative h-full bg-forge-accent-2"
        initial={false}
        animate={{ width: `${clamped * 100}%` }}
        transition={transition}
      >
        {/* A soft warm bloom at the fill's leading edge — reads as a molten filament
            advancing, not a bare CSS width transition. Hidden until real progress exists so
            the track never opens with a stray glow sitting at 0%. */}
        {clamped > 0 && (
          <span
            aria-hidden="true"
            className="absolute right-0 top-1/2 h-3 w-3 -translate-y-1/2 translate-x-1/2 rounded-full bg-forge-accent-2 blur-[5px]"
          />
        )}
      </motion.div>
    </div>
  );
}
