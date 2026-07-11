import type { WorkflowTraceStep } from "../../types/api";

const NODE_LABELS: Record<string, string> = {
  input_validation: "Input Validation",
  invalid_input: "Invalid Input",
  industry_classification: "Industry Classification",
  funding_readiness: "Funding Readiness",
  evidence_confidence_check: "Evidence & Confidence Check",
  judge: "Judge Synthesis",
  persistence: "Persistence",
  final_response: "Final Response",
};

/** Renders the real, persisted `workflow_trace` from the completed analysis — the exact sequence
 * of LangGraph orchestrator nodes that ran, in order, with their real status. Never reconstructed
 * or guessed; if the trace is empty, that's shown honestly rather than a fabricated timeline. */
export function WorkflowTrace({ trace }: { trace: WorkflowTraceStep[] | null }) {
  if (!trace || trace.length === 0) {
    return <p className="text-sm text-ink-muted">No workflow trace was recorded for this run.</p>;
  }

  return (
    <ol className="space-y-3">
      {trace.map((step, idx) => (
        <li key={`${step.node}-${idx}`} className="flex items-start gap-4">
          <span
            className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border text-[11px] font-medium ${
              step.status === "ok"
                ? "border-signal-500/40 bg-signal-500/10 text-signal-300"
                : step.status === "error"
                  ? "border-danger-500/40 bg-danger-500/10 text-danger-400"
                  : "border-white/15 bg-white/5 text-ink-muted"
            }`}
            aria-hidden="true"
          >
            {idx + 1}
          </span>
          <div>
            <p className="text-sm font-medium text-ink-secondary">
              {NODE_LABELS[step.node] ?? step.node}{" "}
              <span className="ml-1 text-xs font-normal capitalize text-ink-muted">({step.status})</span>
            </p>
            {step.detail && <p className="mt-0.5 text-xs text-ink-muted">{step.detail}</p>}
          </div>
        </li>
      ))}
    </ol>
  );
}
