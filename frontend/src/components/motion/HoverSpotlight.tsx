import { useReducedMotion } from "framer-motion";
import { useRef, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  className?: string;
}

/** Replaces the old page-wide cursor-following circle with a soft, low-opacity radial highlight
 * clipped entirely inside this one element (a button or card) — visible only while the pointer is
 * over that specific component, never the whole page. Disabled for touch pointers and
 * `prefers-reduced-motion`, in which case this is a plain wrapper with no listener attached. */
export function HoverSpotlight({ children, className = "" }: Props) {
  const prefersReduced = useReducedMotion();
  const spotRef = useRef<HTMLDivElement>(null);
  const isCoarsePointer = typeof window !== "undefined" && window.matchMedia("(pointer: coarse)").matches;
  const enabled = !prefersReduced && !isCoarsePointer;

  function handleMove(e: React.MouseEvent<HTMLDivElement>) {
    if (!enabled || !spotRef.current) return;
    const rect = e.currentTarget.getBoundingClientRect();
    spotRef.current.style.background = `radial-gradient(210px circle at ${e.clientX - rect.left}px ${
      e.clientY - rect.top
    }px, rgba(255,255,255,0.06), transparent 70%)`;
  }

  function handleLeave() {
    if (spotRef.current) spotRef.current.style.background = "transparent";
  }

  return (
    <div
      className={`relative overflow-hidden ${className}`}
      onMouseMove={enabled ? handleMove : undefined}
      onMouseLeave={enabled ? handleLeave : undefined}
    >
      {enabled && <div ref={spotRef} className="pointer-events-none absolute inset-0" aria-hidden="true" />}
      {children}
    </div>
  );
}
