interface Props {
  insightId: string;
  label: string;
}

/** A same-page anchor back to where an `Insight` is actually stated in full (the Executive
 * Command Center or Mission Control) — used everywhere else on the Reveal page that used to
 * restate the same sentence. Native `<a href="#...">` + `scroll-mt-24` on the target (already
 * applied in `ExecutiveCommandCenter`/`MissionControl`) gives free smooth, accessible, keyboard-
 * reachable in-page navigation with no extra JS. */
export function InsightLink({ insightId, label }: Props) {
  return (
    <a
      href={`#${insightId}`}
      className="inline-flex items-center gap-1 text-forge-2 font-medium text-forge-accent-2 underline decoration-forge-accent-2/40 underline-offset-4 hover:decoration-forge-accent-2"
    >
      See: {label} ↑
    </a>
  );
}
