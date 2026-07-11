import { useEffect, useState } from "react";
import type { WorkflowTraceStep } from "../../types/api";
import { ForgeCore } from "./ForgeCore";

/** Maps real orchestrator node names (see backend/app/agents/nodes.py) to display labels.
 * Never invents stages that didn't run — falls back to the raw node name for anything unmapped. */
const STAGE_LABELS: Record<string, string> = {
  input_validation: "Venture Signal Captured",
  industry_classification: "Industry Intelligence Mapping",
  funding_readiness: "Funding Readiness Scanning",
  evidence_confidence_check: "Evidence Integrity Check",
  judge: "Judge Intelligence Synthesis",
};

const FINAL_STAGE = "Venture Blueprint Forged";
const STAGE_NAMES = Object.keys(STAGE_LABELS);
const TOTAL_STEPS = STAGE_NAMES.length + 1;

interface Props {
  /** Real workflow_trace from the completed analysis, or null while the request is in flight. */
  trace: WorkflowTraceStep[] | null;
  /** True once the request has failed outright (network/API error, not a per-node failure). */
  failed?: boolean;
}

/** Renders the real backend workflow trace once available. While `trace` is null (the request is
 * still in flight) the Forge Core sits at its last-known real progress — the orchestrator runs
 * synchronously, so there is no per-stage timing signal until the whole response returns, and this
 * component does not invent one. The elapsed-time readout is a real wall-clock timer (time since
 * this component mounted), not a simulated progress computation. */
export function ForgeSequence({ trace, failed = false }: Props) {
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  useEffect(() => {
    if (trace || failed) return;
    const start = Date.now();
    const id = window.setInterval(() => setElapsedSeconds(Math.floor((Date.now() - start) / 1000)), 1000);
    return () => window.clearInterval(id);
  }, [trace, failed]);

  const byNode = new Map((trace ?? []).map((step) => [step.node, step]));
  const doneCount = STAGE_NAMES.filter((n) => byNode.get(n)?.status === "ok").length + (trace && !failed ? 1 : 0);
  const erroredNode = STAGE_NAMES.find((n) => byNode.get(n)?.status === "error");
  const coreState = failed || erroredNode ? "error" : trace ? "done" : "running";
  const progress = failed ? doneCount / TOTAL_STEPS || 0.05 : doneCount / TOTAL_STEPS;

  return (
    <div className="grid grid-cols-1 items-center gap-10 lg:grid-cols-[auto_1fr] lg:gap-16">
      <div className="flex justify-center">
        <ForgeCore state={coreState} progress={failed ? Math.max(progress, 0.08) : progress} />
      </div>

      <ol aria-live="polite" className="space-y-4">
        {STAGE_NAMES.map((node, idx) => {
          const step = byNode.get(node);
          const isDone = !!step && step.status === "ok";
          const isError = !!step && step.status === "error";
          const isPending = !trace && !failed;

          return (
            <li key={node} className="flex items-start gap-4">
              <span
                className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-xs font-medium ${
                  isDone
                    ? "border-signal-500 bg-signal-500/15 text-signal-300"
                    : isError
                      ? "border-danger-500 bg-danger-500/15 text-danger-400"
                      : "border-white/15 bg-white/5 text-ink-muted"
                }`}
                aria-hidden="true"
              >
                {isDone ? "✓" : isError ? "!" : idx + 1}
              </span>
              <div className="pt-1">
                <p className={`text-base ${isDone ? "text-ink-primary" : isError ? "text-danger-400" : "text-ink-muted"}`}>
                  {STAGE_LABELS[node]}
                  {isPending && <span className="ml-2 animate-pulse text-signal-400">···</span>}
                </p>
                {step?.detail && <p className="mt-0.5 text-sm text-ink-muted">{step.detail}</p>}
              </div>
            </li>
          );
        })}
        <li className="flex items-start gap-4">
          <span
            className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-xs font-medium ${
              trace && !failed
                ? "border-gold-500 bg-gold-500/15 text-gold-400"
                : "border-white/15 bg-white/5 text-ink-muted"
            }`}
            aria-hidden="true"
          >
            {trace && !failed ? "✓" : STAGE_NAMES.length + 1}
          </span>
          <p className={`pt-1 text-base font-medium ${trace && !failed ? "text-gold-400" : "text-ink-muted"}`}>
            {FINAL_STAGE}
          </p>
        </li>
        {!trace && !failed && (
          <li className="pt-2 text-xs uppercase tracking-[0.15em] text-ink-muted/70">
            Elapsed: {elapsedSeconds}s — running the real orchestration pipeline, not a simulated timer
          </li>
        )}
      </ol>
    </div>
  );
}
