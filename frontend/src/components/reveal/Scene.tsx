import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { useMotionTier } from "../../motion/transitions";

interface Props {
  eyebrow: string;
  children: ReactNode;
  /** Scene 1 only — full viewport height, no scroll needed to read the verdict. */
  hero?: boolean;
}

/** One scene, one question — the shared shell for every full-bleed section of the Reveal.
 * Deliberately not a card/panel: no border, no background surface, no shadow — the Bible bans
 * "dashboard" framing, so a scene is just generous whitespace and a fade-in, never a container.
 *
 * Fades in once on mount (not scroll-triggered `whileInView`): a real-browser check found that
 * `whileInView` leaves every scene below the first fold stuck at `opacity: 0` until a user
 * actually scrolls to it — invisible to a fast scroller, a full-page capture, or anyone who tabs
 * past it without a smooth scroll. Mount-triggered fade matches the pattern already established
 * by ThresholdPage/ForgeSequence and is guaranteed to resolve to visible. */
export function Scene({ eyebrow, children, hero = false }: Props) {
  const transition = useMotionTier("threshold");
  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={transition}
      className={`mx-auto flex w-full max-w-[860px] flex-col px-6 forge-sm:px-10 ${
        hero ? "min-h-[100dvh] justify-center py-16" : "py-20 forge-sm:py-28"
      }`}
    >
      <p className="text-forge-1 uppercase tracking-[0.25em] text-forge-label">{eyebrow}</p>
      <div className="mt-4">{children}</div>
    </motion.section>
  );
}
