import { useEffect, useRef } from "react";
import type { MotionTier } from "./transitions";

// Which Act a route belongs to, purely for transition-tier selection (Design System
// Bible §8: `scene` tier moving between beats inside an Act, `threshold` tier moving
// between Acts). Route *matching* (which page renders) stays entirely in App.tsx's
// <Routes> — this is a parallel, narrower classification used only to pick a motion
// duration.
export type Act = "threshold" | "discovery" | "reveal";

export function actOfPath(pathname: string): Act {
  if (pathname.startsWith("/new/")) return "discovery";
  if (pathname.startsWith("/analyses/")) return "reveal";
  // "/", the Forging status route, and "/history" all currently render with no
  // persistent chrome (Design System Bible §2's "none" rows) — grouped together here
  // so moving between them is still always a full `threshold`-tier transition, never
  // treated as an in-Act `scene` move.
  return "threshold";
}

export function tierForTransition(fromPathname: string | null, toPathname: string): MotionTier {
  if (fromPathname === null) return "threshold";
  return actOfPath(fromPathname) === actOfPath(toPathname) ? "scene" : "threshold";
}

/** Computes the tier for the transition about to happen (comparing the *previous*
 * pathname to the current one), then records the current pathname as "previous" for
 * next time — after the value currently needed has already been read, via a
 * post-commit effect. */
export function useTransitionTier(pathname: string): MotionTier {
  const prevRef = useRef<string | null>(null);
  const tier = tierForTransition(prevRef.current, pathname);

  useEffect(() => {
    prevRef.current = pathname;
  }, [pathname]);

  return tier;
}
