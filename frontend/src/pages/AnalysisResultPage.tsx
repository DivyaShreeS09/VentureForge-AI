import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { Reveal } from "../components/reveal/Reveal";
import {
  ErrorBanner,
  LoadingBanner,
} from "../components/status/StatusBanner";
import { useAsync } from "../hooks/useAsync";
import {
  getAnalysis,
  getStartup,
} from "../services/api";
import {
  deleteHistoryEntry,
  recordAnalysis,
} from "../services/localHistory";

export function AnalysisResultPage() {
  const { analysisId } =
    useParams<{
      analysisId: string;
    }>();

  const navigate = useNavigate();

  const {
    data,
    loading,
    error,
    errorStatus,
    run,
  } = useAsync(getAnalysis);

  const [
    reanalyzing,
    setReanalyzing,
  ] = useState(false);

  const [
    startupName,
    setStartupName,
  ] = useState<string | null>(
    null,
  );

  /*
   * Load the current analysis.
   */
  useEffect(() => {
    if (analysisId) {
      run(analysisId);
    }
  }, [analysisId, run]);

  /*
   * Remove a broken local-history
   * reference if the analysis
   * genuinely no longer exists.
   */
  useEffect(() => {
    if (
      analysisId &&
      errorStatus === 404
    ) {
      deleteHistoryEntry(
        analysisId,
      );
    }
  }, [
    analysisId,
    errorStatus,
  ]);

  /*
   * Load the startup name when the
   * analysis has completed.
   */
  useEffect(() => {
    if (
      !data ||
      data.status !== "COMPLETED"
    ) {
      return;
    }

    let cancelled = false;

    getStartup(data.startup_id)
      .then((startup) => {
        if (cancelled) {
          return;
        }

        recordAnalysis(
          startup.name,
          data,
        );

        setStartupName(
          startup.name,
        );
      })
      .catch(() => {
        /*
         * Startup-name lookup is only
         * supplementary.
         *
         * A failure here must not block
         * the final Reveal page.
         */
      });

    return () => {
      cancelled = true;
    };
  }, [data]);

  /*
   * Start another analysis using
   * the existing status/polling flow.
   */
  function handleReanalyze() {
    if (!data) {
      return;
    }

    setReanalyzing(true);

    navigate(
      `/startups/${data.startup_id}/status`,
    );
  }

  /*
   * Loading / error state.
   */
  if (
    loading ||
    error ||
    !data
  ) {
    return (
      <main className="min-h-[100dvh] font-forge-sans">
        <div className="mx-auto max-w-[860px] px-6 py-20 forge-sm:px-10">
          {loading && (
            <LoadingBanner message="Loading analysis..." />
          )}

          {error && (
            <ErrorBanner
              message={error}
            />
          )}
        </div>
      </main>
    );
  }

  /*
   * FINAL RESULT PAGE
   *
   * IMPORTANT:
   * Reveal.tsx owns the ONE global
   * speaker for the complete output.
   *
   * Do not add another speaker here.
   */
  return (
    <Reveal
      analysis={data}
      onReanalyze={
        handleReanalyze
      }
      reanalyzing={
        reanalyzing
      }
      startupName={
        startupName
      }
    />
  );
}