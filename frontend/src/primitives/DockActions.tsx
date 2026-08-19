import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export interface DockAction {
  id: string;
  label: string;
  icon: ReactNode;
  onClick: () => void;
}

const DockActionsContext = createContext<{
  action: DockAction | null;
  setAction: (action: DockAction | null) => void;
} | null>(null);

/** Mirrors `CommandCapsuleProvider`'s shape exactly: one shared slot, rendered once in
 * `RootLayout`, that any page can register a contextual action into. Today only the Reveal page
 * uses it (an "Export PDF" dock icon that only exists once a completed analysis exists) — the
 * dock itself (`Dock.tsx`) has no page-specific knowledge otherwise. */
export function DockActionsProvider({ children }: { children: ReactNode }) {
  const [action, setAction] = useState<DockAction | null>(null);
  const value = useMemo(() => ({ action, setAction }), [action]);
  return <DockActionsContext.Provider value={value}>{children}</DockActionsContext.Provider>;
}

/** Registers a single contextual dock action for as long as the calling component is mounted —
 * clears itself on unmount, so navigating away from the Reveal page automatically removes the
 * Export PDF icon everywhere else, matching `useRegisterCommandSections`'s exact lifecycle. */
export function useRegisterDockAction(action: DockAction | null) {
  const ctx = useContext(DockActionsContext);
  if (!ctx) throw new Error("useRegisterDockAction must be used within DockActionsProvider");
  const { setAction } = ctx;

  useEffect(() => {
    setAction(action);
    return () => setAction(null);
    // Intentionally re-runs on every render where the caller passes a new `action` object (its
    // `onClick` closure often captures page state like a corrected analysis) — bailing out on a
    // narrower key like `action.id` alone would freeze the dock action to whatever it captured on
    // first mount, silently going stale after e.g. a positioning correction updates the analysis.
  }, [action, setAction]);
}

export function useDockAction(): DockAction | null {
  const ctx = useContext(DockActionsContext);
  if (!ctx) throw new Error("useDockAction must be used within DockActionsProvider");
  return ctx.action;
}
