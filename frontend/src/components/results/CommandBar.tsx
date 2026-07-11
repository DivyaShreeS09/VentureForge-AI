import { Link } from "react-router-dom";
import { Wordmark } from "../brand/Wordmark";

const STATUS_STYLES: Record<string, string> = {
  COMPLETED: "border-success-500/30 bg-success-500/10 text-success-400",
  FAILED: "border-danger-500/30 bg-danger-500/10 text-danger-400",
  PENDING: "border-white/15 bg-white/5 text-ink-muted",
  RUNNING: "border-signal-500/30 bg-signal-500/10 text-signal-300",
};

interface Props {
  startupName: string | null;
  status: string;
  modelVersion: string | null;
  timestamp: string;
  onReanalyze: () => void;
  reanalyzing: boolean;
}

/** Top command bar for the Results Command Center: identity, the real startup name and analysis
 * status, the model version actually used, the real timestamp, and the two actions available —
 * re-run the pipeline (creates a new analysis record, per the app's analysis-history design) or
 * start a new venture. Nothing here is computed client-side beyond formatting. */
export function CommandBar({ startupName, status, modelVersion, timestamp, onReanalyze, reanalyzing }: Props) {
  return (
    <header className="sticky top-0 z-20 border-b border-white/5 bg-void-950/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-6 py-4 sm:px-10">
        <div className="flex flex-wrap items-center gap-4">
          <Wordmark />
          <span className="h-5 w-px bg-white/10" aria-hidden="true" />
          <div>
            <p className="text-sm font-medium text-ink-primary">{startupName ?? "Untitled venture"}</p>
            <p className="text-xs text-ink-muted">
              {modelVersion ? `Model ${modelVersion}` : "Model unavailable"} ·{" "}
              {new Date(timestamp).toLocaleString()}
            </p>
          </div>
          <span className={`rounded-full border px-3 py-1 text-xs font-medium capitalize ${STATUS_STYLES[status] ?? STATUS_STYLES.PENDING}`}>
            {status.toLowerCase()}
          </span>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onReanalyze}
            disabled={reanalyzing}
            className="rounded-lg border border-white/15 px-4 py-2 text-sm font-medium text-ink-secondary transition hover:border-signal-400/50 hover:bg-white/5 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50"
          >
            {reanalyzing ? "Re-analyzing…" : "Re-analyze"}
          </button>
          <Link
            to="/"
            className="rounded-lg bg-gradient-to-r from-signal-600 to-current-500 px-4 py-2 text-sm font-medium text-ink-primary transition hover:brightness-110"
          >
            New venture
          </Link>
        </div>
      </div>
    </header>
  );
}
