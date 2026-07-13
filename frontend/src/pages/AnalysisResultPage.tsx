import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { AnalysisResult } from "../components/results/AnalysisResult";
import { CommandBar } from "../components/results/CommandBar";
import { ErrorBanner, LoadingBanner } from "../components/status/StatusBanner";
import { useAsync } from "../hooks/useAsync";
import { analyzeStartup, getAnalysis, getStartup } from "../services/api";
import { recordAnalysis } from "../services/localHistory";

export function AnalysisResultPage() {
  const { analysisId } = useParams<{ analysisId: string }>();
  const navigate = useNavigate();
  const { data, loading, error, run } = useAsync(getAnalysis);
  const [startupName, setStartupName] = useState<string | null>(null);
  const [reanalyzing, setReanalyzing] = useState(false);

  useEffect(() => {
    if (analysisId) run(analysisId);
  }, [analysisId, run]);

  useEffect(() => {
    if (!data) return;
    let cancelled = false;
    getStartup(data.startup_id)
      .then((startup) => {
        if (!cancelled) {
          setStartupName(startup.name);
          if (data.status === "COMPLETED") recordAnalysis(startup.name, data);
        }
      })
      .catch(() => {
        /* The command bar shows a graceful fallback label — this lookup is presentational only. */
      });
    return () => {
      cancelled = true;
    };
  }, [data]);

  async function handleReanalyze() {
    if (!data) return;
    setReanalyzing(true);
    try {
      const next = await analyzeStartup(data.startup_id);
      navigate(`/analyses/${next.id}`);
    } finally {
      setReanalyzing(false);
    }
  }

  return (
    <div className="min-h-screen">
      {data && (
        <CommandBar
          startupName={startupName}
          status={data.status}
          modelVersion={data.industry_model_version}
          timestamp={data.updated_at}
          onReanalyze={handleReanalyze}
          reanalyzing={reanalyzing}
        />
      )}
      <main className="mx-auto max-w-7xl px-6 py-10 sm:px-10">
        {!data && (
          <>
            <p className="text-xs font-medium uppercase tracking-[0.25em] text-signal-400">Venture Blueprint</p>
            <h1 className="mt-2 text-display text-3xl">Assessment Results</h1>
          </>
        )}
        <div className="mt-8">
          {loading && <LoadingBanner message="Loading analysis..." />}
          {error && <ErrorBanner message={error} />}
          {data && <AnalysisResult analysis={data} />}
        </div>
      </main>
    </div>
  );
}
