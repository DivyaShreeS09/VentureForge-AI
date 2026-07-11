import { useCallback, useEffect, useState } from "react";
import { getSystemStatus } from "../../services/api";
import type { SystemStatus } from "../../types/api";

type Check = { name: string; ok: boolean; reason: string };

function _failedChecks(status: SystemStatus): Check[] {
  const checks: Check[] = [];
  if (!status.database.ok) {
    checks.push({ name: "Database", ok: false, reason: status.database.detail ?? "Unreachable." });
  }
  if (!status.industry_model.ok) {
    checks.push({
      name: "Industry classifier",
      ok: false,
      reason: status.industry_model.detail ?? "Model artifact not found.",
    });
  }
  return checks;
}

/**
 * Blocks the app behind a polished full-screen notice only when a service the app actually
 * depends on (database, trained model) is down — never for the optional LLM layer, which is
 * allowed to be unconfigured. Silently lets children through if the dev-only `/system/status`
 * endpoint itself is unavailable (e.g. in production, where it 404s by design): this overlay is a
 * developer-experience convenience, not something the app depends on to function.
 */
export function SystemStatusGate({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<SystemStatus | null | "loading">("loading");

  const check = useCallback(() => {
    setStatus("loading");
    getSystemStatus()
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  useEffect(() => {
    check();
  }, [check]);

  if (status === "loading") return null;
  if (status === null) return <>{children}</>;

  const failed = _failedChecks(status);
  if (failed.length === 0) return <>{children}</>;

  return (
    <div
      role="alert"
      aria-live="assertive"
      className="fixed inset-0 z-50 flex items-center justify-center bg-void-950/95 p-6 backdrop-blur-md"
    >
      <div className="panel panel-glow w-full max-w-lg p-8">
        <p className="text-xs font-medium uppercase tracking-[0.2em] text-danger-400">
          Service Unavailable
        </p>
        <h1 className="mt-3 text-display text-2xl text-ink-primary">
          VentureForge AI can't reach everything it needs.
        </h1>
        <ul className="mt-6 space-y-4">
          {failed.map((f) => (
            <li key={f.name} className="rounded-xl border border-danger-500/20 bg-danger-500/5 p-4">
              <p className="font-medium text-danger-400">{f.name}</p>
              <p className="mt-1 text-sm text-ink-muted">{f.reason}</p>
            </li>
          ))}
        </ul>
        <div className="mt-6 rounded-xl border border-white/10 bg-white/[0.03] p-4 text-xs text-ink-muted">
          <p className="font-medium uppercase tracking-[0.1em] text-ink-muted">Development setup hint</p>
          <p className="mt-1">
            Confirm PostgreSQL is running and <code className="text-ink-secondary">DATABASE_URL</code> in{" "}
            <code className="text-ink-secondary">backend/.env</code> matches it, then run{" "}
            <code className="text-ink-secondary">alembic upgrade head</code> from{" "}
            <code className="text-ink-secondary">backend/</code>. If the model is missing, train it with{" "}
            <code className="text-ink-secondary">python -m ml.src.training.train_industry_classifier</code>.
            See README.md for the full setup sequence.
          </p>
        </div>
        <button
          onClick={check}
          className="mt-6 rounded-lg border border-white/15 px-4 py-2.5 text-sm font-medium text-ink-secondary transition hover:border-signal-400/50 hover:bg-white/5 focus-visible:outline-none"
        >
          Retry connection
        </button>
      </div>
    </div>
  );
}
