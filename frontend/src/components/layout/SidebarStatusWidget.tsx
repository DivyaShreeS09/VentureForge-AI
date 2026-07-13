import { useEffect, useState } from "react";
import { getSystemStatus } from "../../services/api";

type Health = "checking" | "operational" | "degraded" | "unknown";

/** A quiet status pill for the sidebar — reuses the same dev-only `/system/status` endpoint as
 * SystemStatusGate, but never blocks the app; it only ever informs. In production the endpoint
 * 404s by design (see getSystemStatus's doc comment), so this settles on "unknown" rather than
 * claiming an operational state it can't actually verify. */
export function SidebarStatusWidget() {
  const [health, setHealth] = useState<Health>("checking");

  useEffect(() => {
    let cancelled = false;
    getSystemStatus()
      .then((status) => {
        if (cancelled) return;
        if (status === null) {
          setHealth("unknown");
          return;
        }
        const ok = status.database.ok && status.industry_model.ok;
        setHealth(ok ? "operational" : "degraded");
      })
      .catch(() => !cancelled && setHealth("unknown"));
    return () => {
      cancelled = true;
    };
  }, []);

  const dotColor =
    health === "operational" ? "bg-success-500" : health === "degraded" ? "bg-danger-500" : "bg-ink-muted";
  const label =
    health === "checking"
      ? "Checking status…"
      : health === "operational"
        ? "All systems operational"
        : health === "degraded"
          ? "Service degraded"
          : "Status unavailable";

  return (
    <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/[0.03] p-3">
      <svg viewBox="0 0 24 24" className="h-7 w-7 shrink-0 text-signal-400" fill="none" aria-hidden="true">
        <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1" opacity="0.25" />
        <circle cx="12" cy="12" r="5.5" stroke="currentColor" strokeWidth="1" opacity="0.45" />
        <circle cx="12" cy="12" r="1.8" fill="currentColor" />
      </svg>
      <div>
        <p className="text-[11px] font-medium uppercase tracking-[0.15em] text-ink-muted">System Status</p>
        <div className="mt-1 flex items-center gap-2">
          <span
            className={`h-1.5 w-1.5 shrink-0 rounded-full ${dotColor} ${health === "operational" ? "animate-pulse-slow" : ""}`}
            aria-hidden="true"
          />
          <span className="text-xs text-ink-secondary">{label}</span>
        </div>
      </div>
    </div>
  );
}
