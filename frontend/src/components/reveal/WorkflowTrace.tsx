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

/** Renders the real, persisted `workflow_trace` — the exact sequence of orchestrator nodes that
 * ran, in order, with real status. Never reconstructed or guessed. Deep Evidence only. */
export function WorkflowTrace({ trace }: { trace: WorkflowTraceStep[] | null }) {
  if (!trace || trace.length === 0) {
    return <p className="text-forge-2 text-forge-text-secondary">No workflow trace was recorded for this run.</p>;
  }

  return (
    // eslint-disable-next-line jsx-a11y/no-redundant-roles
    <ol role="list" className="space-y-2">
      {trace.map((step, idx) => (
        // eslint-disable-next-line jsx-a11y/no-redundant-roles
        <li key={`${step.node}-${idx}`} role="listitem" className="flex items-baseline gap-3 text-forge-2">
          <span className="w-5 shrink-0 font-forge-mono text-forge-1 text-forge-text-secondary">{idx + 1}</span>
          <span className="text-forge-text-secondary">
            {NODE_LABELS[step.node] ?? step.node} <span className="text-forge-text-secondary">({step.status})</span>
            {step.detail && <span className="block text-forge-1 text-forge-text-secondary">{step.detail}</span>}
          </span>
        </li>
      ))}
    </ol>
  );
}
