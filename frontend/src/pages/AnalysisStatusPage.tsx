import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ForgeSequence } from "../components/forge/ForgeSequence";
import { useAnalysisProgress } from "../hooks/useAnalysisProgress";
import { useAsync } from "../hooks/useAsync";
import { Button } from "../primitives";
import { analyzeStartup } from "../services/api";

/** Act IV — "The Forging". `POST /startups/{id}/analyze` now returns immediately (Sprint 6): the
 * real orchestrator run continues in the background, and this page subscribes to its genuine,
 * incremental progress via `useAnalysisProgress` (SSE, falling back to polling the same real
 * endpoint) rather than waiting on one long blocking call. Transitions into the Reveal
 * (`/analyses/{id}`) itself the instant the backend actually reports COMPLETED — never a fixed
 * delay, never a click required once the real work is genuinely done. */
export function AnalysisStatusPage() {
  const { startupId } = useParams<{ startupId: string }>();
  const navigate = useNavigate();
  const { error: startError, run } = useAsync(analyzeStartup);
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const started = useRef(false);
  const navigated = useRef(false);

  useEffect(() => {
    if (!startupId || started.current) return;
    started.current = true;
    run(startupId).then((analysis) => {
      if (analysis) setAnalysisId(analysis.id);
    });
  }, [startupId, run]);

  const { analysis } = useAnalysisProgress(analysisId);

  useEffect(() => {
    if (analysis?.status === "COMPLETED" && !navigated.current) {
      navigated.current = true;
      navigate(`/analyses/${analysis.id}`, { replace: true });
    }
  }, [analysis, navigate]);

  function retry() {
    if (!startupId) return;
    started.current = true;
    navigated.current = false;
    setAnalysisId(null);
    run(startupId).then((res) => {
      if (res) setAnalysisId(res.id);
    });
  }

  const requestFailed = !!startError;
  const orchestratorFailed = analysis?.status === "FAILED";

  return (
    // No opaque background here — RootLayout's global "quiet" AmbientBackground shows through,
    // giving this page its own calm cosmic atmosphere behind the glass command panel above.
    <main className="flex min-h-[100dvh] w-full flex-col items-center justify-center px-6 py-20 font-forge-sans forge-sm:px-10">
      <div className="mx-auto flex w-full max-w-3xl flex-col items-center text-center">
        <h1 className="font-forge-serif text-forge-6 font-semibold leading-[1.15] text-forge-text forge-sm:text-forge-7">
          Thinking Through Your Venture
        </h1>
        <p className="mt-3 max-w-xl text-forge-3 text-forge-text-secondary">
          Real analysis is running right now — every stage below reflects genuine work, not a timer.
        </p>

        <div className="mt-12 w-full">
          <ForgeSequence analysis={analysis} failed={requestFailed} />
        </div>

        {(requestFailed || orchestratorFailed) && (
          <div className="mt-10 flex flex-col items-center gap-4">
            <p role="alert" className="text-forge-2 text-forge-risk">
              {requestFailed ? startError : (analysis?.error_message ?? "The analysis could not finish.")}
            </p>
            <Button variant="secondary" onClick={retry}>
              Retry analysis
            </Button>
          </div>
        )}
      </div>
    </main>
  );
}
