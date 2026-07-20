import { useEffect, useRef } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ForgeSequence } from "../components/forge/ForgeSequence";
import { ErrorBanner } from "../components/status/StatusBanner";
import { useAsync } from "../hooks/useAsync";
import { analyzeStartup } from "../services/api";

export function AnalysisStatusPage() {
  const { startupId } = useParams<{ startupId: string }>();
  const navigate = useNavigate();
  const { error, run } = useAsync(analyzeStartup);
  const started = useRef(false);

  useEffect(() => {
    if (!startupId || started.current) return;
    started.current = true;
    run(startupId).then((analysis) => {
      if (analysis) navigate(`/analyses/${analysis.id}`, { replace: true });
    });
  }, [startupId, run, navigate]);

  function retry() {
    started.current = false;
    if (startupId) {
      started.current = true;
      run(startupId).then((analysis) => {
        if (analysis) navigate(`/analyses/${analysis.id}`, { replace: true });
      });
    }
  }

  return (
    <div className="flex min-h-screen flex-col">
      <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col justify-center px-6 py-12 sm:px-10">
        <p className="text-xs font-medium uppercase tracking-[0.25em] text-signal-400">Step 4 · Building Your Mentor Report</p>
        <h1 className="mt-2 text-display text-3xl sm:text-4xl">Your Mentor Is Reviewing Your Idea</h1>
        <p className="mt-3 max-w-xl text-ink-secondary">
          Reading your idea, checking your evidence, and preparing your personalized mentor
          report. This is real analysis running, not a simulated timer.
        </p>

        <div className="mt-12">
          {error ? (
            <div className="space-y-4">
              <ErrorBanner message={error} />
              <button
                onClick={retry}
                className="rounded-lg border border-white/15 px-5 py-2.5 text-sm font-medium text-ink-secondary transition hover:border-signal-400/50 hover:bg-white/5 focus-visible:outline-none"
              >
                Retry analysis
              </button>
            </div>
          ) : (
            <ForgeSequence trace={null} />
          )}
        </div>
      </main>
    </div>
  );
}
