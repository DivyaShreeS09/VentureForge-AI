import type { PrimaryOpportunity } from "../../../types/api";
import { Scene } from "../Scene";
import { ConfidenceTierBadge } from "../ConfidenceTierBadge";

/** Scene 3 — The Biggest Opportunity. Exactly one — never a list — explained in depth: why it
 * matters, why competitors miss it, why this founder can own it. Sourced from
 * `strategic_opportunity.primary_opportunity`, the richest single strategic field the backend
 * already computes but which the old dashboard never rendered anywhere. */
export function OpportunityScene({ opportunity }: { opportunity: PrimaryOpportunity }) {
  return (
    <Scene eyebrow="The Biggest Opportunity">
      <div className="flex items-start justify-between gap-4">
        <h2 className="max-w-[26ch] text-balance font-forge-serif text-forge-6 font-semibold leading-[1.2] text-forge-text">
          {opportunity.opportunity}
        </h2>
        <ConfidenceTierBadge tier={opportunity.confidence_tier} />
      </div>

      <p className="mt-6 max-w-[60ch] text-forge-3 text-forge-text-secondary">{opportunity.reason}</p>

      <div className="mt-8 grid grid-cols-1 gap-6 forge-sm:grid-cols-2">
        <div>
          <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-text-secondary">Who wants this</p>
          <p className="mt-1.5 text-forge-2 text-forge-text-secondary">{opportunity.buyer}</p>
        </div>
        <div>
          <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-text-secondary">Why now</p>
          <p className="mt-1.5 text-forge-2 text-forge-text-secondary">{opportunity.urgency}</p>
        </div>
        <div>
          <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-text-secondary">Why competitors miss it</p>
          <p className="mt-1.5 text-forge-2 text-forge-text-secondary">{opportunity.competition}</p>
        </div>
        <div>
          <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-text-secondary">Evidence for demand</p>
          <p className="mt-1.5 text-forge-2 text-forge-text-secondary">{opportunity.demand}</p>
        </div>
      </div>

      <div className="mt-8 border-t border-forge-text/[.08] pt-6">
        <p className="text-forge-2 text-forge-text-secondary">
          <span className="text-forge-text-secondary">Next step: </span>
          {opportunity.recommended_next_step}
        </p>
      </div>
    </Scene>
  );
}
