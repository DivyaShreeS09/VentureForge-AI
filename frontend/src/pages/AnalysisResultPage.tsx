import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Reveal } from "../components/reveal/Reveal";
import { ErrorBanner, LoadingBanner } from "../components/status/StatusBanner";
import { useAsync } from "../hooks/useAsync";
import { getAnalysis, getStartup } from "../services/api";
import { deleteHistoryEntry, recordAnalysis } from "../services/localHistory";

export function AnalysisResultPage() {
  const { analysisId } = useParams<{ analysisId: string }>();
  const navigate = useNavigate();
  const { data, loading, error, errorStatus, run } = useAsync(getAnalysis);
  const [reanalyzing, setReanalyzing] = useState(false);
  const [startupName, setStartupName] = useState<string | null>(null);

  useEffect(() => {
    if (analysisId) run(analysisId);
  }, [analysisId, run]);

  useEffect(() => {
    // A 404 here means the backend has genuinely never heard of this ID (dev DB reset, manual
    // deletion) — self-heal by pruning the matching local History row so it stops offering a
    // permanently-broken "View" link, rather than leaving a stale reference around forever.
    if (analysisId && errorStatus === 404) deleteHistoryEntry(analysisId);
  }, [analysisId, errorStatus]);

  useEffect(() => {
    if (!data || data.status !== "COMPLETED") return;
    let cancelled = false;
    getStartup(data.startup_id)
      .then((startup) => {
        if (cancelled) return;
        recordAnalysis(startup.name, data);
        // The Executive Hero (Operating System Sprint) needs the real startup name above the
        // fold — this endpoint was already being fetched for local history, just not surfaced.
        setStartupName(startup.name);
      })
      .catch(() => {
        /* Local history is a browser-side convenience only — a lookup failure here never blocks the Reveal itself. */
      });
    return () => {
      cancelled = true;
    };
  }, [data]);

  function handleReanalyze() {
    if (!data) return;
    setReanalyzing(true);
    // Route through the same polling status page a first-time analysis uses
    // (`EvidenceCollectionPage.tsx` navigates here too) rather than creating the analysis here
    // and jumping straight to Reveal. `POST /startups/{id}/analyze` returns immediately with the
    // row still RUNNING (see AnalysisStatusPage's own docstring) — fetching it once and rendering
    // Reveal right away meant `mentor_interpretation` was reliably still null, producing "This
    // analysis has no mentor interpretation to reveal." `AnalysisStatusPage` already knows how to
    // create the analysis *and* poll it via `useAnalysisProgress` until it's genuinely COMPLETED
    // before navigating to Reveal — reusing it here fixes the root cause instead of adding a
    // second polling implementation.
    navigate(`/startups/${data.startup_id}/status`);
  }

  if (loading || error || !data) {
    return (
      <main className="min-h-[100dvh] font-forge-sans">
        <div className="mx-auto max-w-[860px] px-6 py-20 forge-sm:px-10">
          {loading && <LoadingBanner message="Loading analysis..." />}
          {error && <ErrorBanner message={error} />}
        </div>
      </main>
    );
  }

  return <Reveal analysis={data} onReanalyze={handleReanalyze} reanalyzing={reanalyzing} startupName={startupName} />;
}
