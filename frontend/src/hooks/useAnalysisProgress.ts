import { useEffect, useState } from "react";
import { analysisEventsUrl, getAnalysis } from "../services/api";
import type { Analysis } from "../types/api";

const POLL_INTERVAL_MS = 1500;
/** If no real event has arrived within this window (initial connection failed, or a reconnect
 * loop stalled), fall back to plain polling of the exact same real endpoint. Generous on purpose
 * — an EventSource reconnect attempt or a slow node shouldn't trigger a needless fallback. */
const STALE_AFTER_MS = 8_000;
const TERMINAL = new Set(["COMPLETED", "FAILED"]);

interface Result {
  analysis: Analysis | null;
  /** True once real intermediate progress has been observed at least once — lets the caller
   * distinguish "haven't heard anything yet" from "genuinely still on the very first stage". */
  connected: boolean;
}

/** Act IV (The Forging) — subscribes to the real, incrementally-persisted analysis row. Prefers
 * the backend's SSE stream (a genuine push the instant a real orchestrator node completes, see
 * backend/app/api/v1/analyses.py's `stream_analysis_events`); falls back to polling
 * `GET /analyses/{id}` — the same real endpoint, just observed on a timer — only if no real event
 * arrives within `STALE_AFTER_MS`. Both paths render the exact same `Analysis` row; neither one
 * ever synthesizes progress. Stops all activity the moment a terminal status is reached. */
export function useAnalysisProgress(analysisId: string | null): Result {
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!analysisId) return;
    const id = analysisId;
    setAnalysis(null);
    setConnected(false);

    let cancelled = false;
    let pollId: number | undefined;
    let staleTimerId: number | undefined;
    const source = new EventSource(analysisEventsUrl(id));

    function stop() {
      if (pollId !== undefined) window.clearInterval(pollId);
      if (staleTimerId !== undefined) window.clearTimeout(staleTimerId);
      source.close();
    }

    function armStaleWatchdog() {
      if (staleTimerId !== undefined) window.clearTimeout(staleTimerId);
      staleTimerId = window.setTimeout(startPolling, STALE_AFTER_MS);
    }

    function startPolling() {
      if (pollId !== undefined || cancelled) return;
      pollId = window.setInterval(async () => {
        try {
          const data = await getAnalysis(id);
          if (cancelled) return;
          setAnalysis(data);
          setConnected(true);
          if (TERMINAL.has(data.status)) stop();
        } catch {
          // A transient poll failure isn't fatal — the next tick tries again.
        }
      }, POLL_INTERVAL_MS);
    }

    source.onmessage = (event) => {
      if (cancelled) return;
      try {
        const data = JSON.parse(event.data) as Analysis;
        setAnalysis(data);
        setConnected(true);
        armStaleWatchdog();
        if (TERMINAL.has(data.status)) stop();
      } catch {
        // Malformed event — ignore this one message rather than tearing down the connection.
      }
    };
    armStaleWatchdog();

    return () => {
      cancelled = true;
      stop();
    };
  }, [analysisId]);

  return { analysis, connected };
}
