import { GlassCard } from "../../primitives/GlassCard";
import type { Insight } from "../../utils/insights";
import { highlightKeywords } from "../../utils/highlightKeywords";

const ROW_LABEL_TONE: Record<string, string> = {
  Evidence: "text-forge-cyan",
  "Investor concern": "text-forge-rose",
  Recommendation: "text-forge-cyan",
  "Definition of done": "text-forge-gold",
  Timeline: "text-forge-helper",
};

function Row({ label, value }: { label: string; value?: string }) {
  if (!value) return null;
  return (
    <div className="border-t border-forge-text/[.08] py-3 first:border-t-0 first:pt-0">
      <p className={`text-forge-1 uppercase tracking-[0.1em] ${ROW_LABEL_TONE[label] ?? "text-forge-helper"}`}>{label}</p>
      <p className="mt-1 text-forge-2 text-forge-desc">{highlightKeywords(value)}</p>
    </div>
  );
}

const STATUS_TONE: Record<Insight["status"], string> = {
  critical: "text-forge-rose",
  developing: "text-forge-notsure",
  strong: "text-forge-emerald",
};

/** Full detail for exactly one `Insight` (see `utils/insights.ts`) — evidence, investor concern,
 * recommendation, definition of done, timeline. Rendered exactly once, inside Deep Analysis, for
 * whichever insight needs the full picture (the Executive Command Center's tile is the short
 * glance; this is the one detailed expansion — a "zoom level," not a second copy of the same
 * sentence). */
export function InsightDetailCard({ insight, id }: { insight: Insight; id?: string }) {
  return (
    <GlassCard id={id} className="scroll-mt-24 p-6 forge-sm:p-8">
      <p className={`text-forge-1 font-medium uppercase tracking-[0.15em] ${STATUS_TONE[insight.status]}`}>{insight.title}</p>
      <p className="mt-2 max-w-[58ch] font-forge-serif text-forge-4 font-medium leading-snug text-forge-heading">
        {highlightKeywords(insight.why)}
      </p>
      <div className="mt-4">
        <Row label="Evidence" value={insight.evidence} />
        <Row label="Investor concern" value={insight.investorConcern} />
        <Row label="Recommendation" value={insight.recommendation} />
        <Row label="Definition of done" value={insight.definitionOfDone} />
        <Row label="Timeline" value={insight.timeline} />
      </div>
    </GlassCard>
  );
}
