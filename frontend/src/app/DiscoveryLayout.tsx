import { useEffect, useState, type ReactNode } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Wordmark } from "../components/brand/Wordmark";
import { ProgressFilament } from "../primitives/ProgressFilament";
import { Dialog } from "../primitives/Dialog";
import { DiscoveryProgressSetterContext } from "./discoveryProgress";

// Coarse, route-level fallback only, used whenever the active page hasn't reported real
// internal progress via `useDiscoveryProgress` (see discoveryProgress.ts). Sprint 5 rebuilt
// EvidenceCollectionPage as a true one-question-at-a-time conversation and wired it to report
// its own fraction — this table now only matters for IdeaSubmissionPage's 3-scene flow, which
// hasn't opted in yet, and as the pre-opt-in initial value for either route.
const DISCOVERY_ROUTE_PROGRESS: Record<string, number> = {
  "/new/idea": 0.5,
  "/new/evidence": 1,
};

// Route transitions are handled once, above every layout (see SceneTransition's
// header comment) — this component only renders the Discovery Act's chrome: the
// progress filament and the confirm-before-exit wordmark/Esc handling.
export function DiscoveryLayout({ children }: { children: ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const [confirmExitOpen, setConfirmExitOpen] = useState(false);
  const [overrideProgress, setOverrideProgress] = useState<number | null>(null);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setConfirmExitOpen(true);
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  // A page's own reported progress resets on navigation — otherwise the previous route's
  // last-reported fraction would flash briefly on the next route before it reports its own.
  useEffect(() => {
    setOverrideProgress(null);
  }, [location.pathname]);

  const progress = overrideProgress ?? DISCOVERY_ROUTE_PROGRESS[location.pathname] ?? 0;

  return (
    <DiscoveryProgressSetterContext.Provider value={setOverrideProgress}>
      <ProgressFilament progress={progress} />
      <div className="fixed left-4 top-4 z-40">
        <Wordmark onClick={() => setConfirmExitOpen(true)} />
      </div>
      <Dialog
        open={confirmExitOpen}
        message="Leave for now? Your answers are saved — you can continue anytime from here."
        confirmLabel="Leave"
        cancelLabel="Keep going"
        onConfirm={() => {
          setConfirmExitOpen(false);
          navigate("/");
        }}
        onCancel={() => setConfirmExitOpen(false)}
      />
      {children}
    </DiscoveryProgressSetterContext.Provider>
  );
}
