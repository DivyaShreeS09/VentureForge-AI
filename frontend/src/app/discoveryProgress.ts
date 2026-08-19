import { createContext, useContext, useEffect } from "react";

type ProgressSetter = (value: number | null) => void;

/** DiscoveryLayout's route-level progress table (0.5 / 1) is only a fallback for a route with
 * no internal steps of its own. A page that *does* have real internal steps (the Evidence
 * Conversation's one-question-at-a-time flow) calls `useDiscoveryProgress` to report its own
 * fraction-of-the-way-through-this-route value, which DiscoveryLayout prefers over the coarse
 * table whenever it's set. Unmounting (or passing `null`) reverts to the coarse fallback — no
 * page is required to opt in. */
export const DiscoveryProgressSetterContext = createContext<ProgressSetter | null>(null);

export function useDiscoveryProgress(value: number | null): void {
  const setProgress = useContext(DiscoveryProgressSetterContext);
  useEffect(() => {
    setProgress?.(value);
    return () => setProgress?.(null);
  }, [setProgress, value]);
}
