import { useReducedMotion, type Transition } from "framer-motion";

/**
 * Design System Bible §8 / Build Contract §1.9 — exactly three motion tiers exist in
 * this product. No component may define an inline duration or easing curve; every
 * animated element imports one of these three presets.
 */
export const motionTiers = {
  micro: { duration: 0.12, ease: [0.4, 0, 0.2, 1] } satisfies Transition,
  scene: { duration: 0.28, ease: [0.16, 1, 0.3, 1] } satisfies Transition,
  threshold: { duration: 0.56, ease: [0.16, 1, 0.3, 1] } satisfies Transition,
} as const;

export type MotionTier = keyof typeof motionTiers;

/** Design System Bible §8 reduced-motion rule: every `scene`/`threshold` transition
 * collapses to an instant state change plus a 150ms opacity crossfade. `micro` states
 * (hover/focus) are left untouched — they carry meaning, not spectacle, and are cheap
 * enough not to need reduction. No component reads `prefers-reduced-motion` directly;
 * all of them call this hook instead, so the fallback behavior can't drift between
 * components (Implementation Master Plan §9).
 */
export function useMotionTier(tier: MotionTier): Transition {
  const reduced = useReducedMotion();
  if (!reduced) return motionTiers[tier];
  if (tier === "micro") return motionTiers.micro;
  return { duration: 0.15, ease: "linear" };
}
