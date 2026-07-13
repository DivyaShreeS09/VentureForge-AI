import { motion, useMotionValue, useReducedMotion, useSpring, useTransform } from "framer-motion";
import type { ReactNode } from "react";

interface Props {
  children: ReactNode;
  className?: string;
}

const MAX_TILT = 4;

/** A subtle 3-5deg perspective tilt toward the cursor, used on the small set of "hero" surfaces
 * (the reference calls for this on cards generally, but applying real 3D tilt to every dense
 * results card produces motion sickness at scale — this component exists so call sites opt in
 * deliberately rather than a blanket global rule). No-ops under reduced-motion. */
export function TiltCard({ children, className = "" }: Props) {
  const prefersReduced = useReducedMotion();
  const rawX = useMotionValue(0.5);
  const rawY = useMotionValue(0.5);
  const springX = useSpring(rawX, { stiffness: 200, damping: 22 });
  const springY = useSpring(rawY, { stiffness: 200, damping: 22 });
  const rotateX = useTransform(springY, [0, 1], [MAX_TILT, -MAX_TILT]);
  const rotateY = useTransform(springX, [0, 1], [-MAX_TILT, MAX_TILT]);

  function handleMove(e: React.MouseEvent<HTMLDivElement>) {
    if (prefersReduced) return;
    const rect = e.currentTarget.getBoundingClientRect();
    rawX.set((e.clientX - rect.left) / rect.width);
    rawY.set((e.clientY - rect.top) / rect.height);
  }

  function handleLeave() {
    rawX.set(0.5);
    rawY.set(0.5);
  }

  return (
    <motion.div
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      style={prefersReduced ? undefined : { rotateX, rotateY, transformPerspective: 800 }}
      className={className}
    >
      {children}
    </motion.div>
  );
}
