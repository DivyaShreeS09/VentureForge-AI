import { AnimatePresence, motion } from "framer-motion";
import type { ReactNode } from "react";
import { useMotionTier, type MotionTier } from "./transitions";

interface SceneTransitionProps {
  /** Typically the route pathname — changing it triggers the exit/enter pair. */
  transitionKey: string;
  /** `scene` (280ms) within an Act, `threshold` (560ms) between Acts — see
   * src/motion/act.ts's `tierForTransition`. Rendered exactly once, wrapping
   * `<Routes>` in App.tsx — NOT per-layout: React Router unmounts a route's whole
   * element tree atomically on navigation, so a per-layout AnimatePresence never
   * sees the outgoing layout's exit animation when the route crosses into a
   * different layout. One shared instance, above all layouts, is what actually lets
   * the previous screen animate out before the next one animates in. */
  tier: MotionTier;
  children: ReactNode;
}

// Design System Bible §8 — the one shared route-transition implementation; no
// individual layout builds its own.
export function SceneTransition({ transitionKey, tier, children }: SceneTransitionProps) {
  const transition = useMotionTier(tier);

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={transitionKey}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={transition}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
