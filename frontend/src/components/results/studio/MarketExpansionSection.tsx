import type { IdeaConfidenceTier, IdeaExpansion, IdeaExpansionItem, Student3GrowthItem, StrategicOpportunity, StrategicOpportunityItem } from "../../../types/api";
import { Section } from "../Section";
import { ConfidenceTierBadge } from "./ConfidenceTierBadge";

interface DisplayItem {
  label: string;
  reason: string;
  confidence_tier: IdeaConfidenceTier;
}

function fromIdeaItems(items: IdeaExpansionItem[]): DisplayItem[] {
  return items.map((item) => ({ label: item.title, reason: item.reason, confidence_tier: item.confidence_tier }));
}

function fromStrategicItems(items: StrategicOpportunityItem[]): DisplayItem[] {
  return items.map((item) => ({ label: item.opportunity, reason: item.reason, confidence_tier: item.confidence_tier }));
}

function ItemList({ heading, items, emptyNote }: { heading: string; items: DisplayItem[]; emptyNote: string }) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-muted">{heading}</h3>
      {items.length > 0 ? (
        <ul className="mt-2 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
          {items.map((item, idx) => (
            <li key={`${item.label}-${idx}`} className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
              <div className="flex items-start justify-between gap-3">
                <p className="text-sm font-medium text-ink-primary">{item.label}</p>
                <ConfidenceTierBadge tier={item.confidence_tier} />
              </div>
              <p className="mt-1.5 text-xs text-ink-secondary">{item.reason}</p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-1.5 text-xs text-ink-muted">{emptyNote}</p>
      )}
    </div>
  );
}

// Phase 5 (Student 3) growth-channel recommendations have no confidence tier of their own (they're
// a fixed planning checklist, not evidence-tiered like Idea Expansion/Strategic Opportunity), so
// this renders its own small list rather than forcing it through ItemList's ConfidenceTierBadge.
function GrowthStrategyList({ items }: { items: Student3GrowthItem[] }) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-muted">Growth Strategy</h3>
      {items.length > 0 ? (
        <ul className="mt-2 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
          {items.map((item) => (
            <li key={item.area} className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
              <p className="text-[11px] uppercase tracking-[0.08em] text-ink-muted">{item.area}</p>
              <p className="mt-1 text-sm font-medium text-ink-primary">{item.recommendation}</p>
              <p className="mt-1.5 text-xs text-ink-secondary">{item.rationale}</p>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-1.5 text-xs text-ink-muted">No growth-strategy recommendations identified for this run.</p>
      )}
    </div>
  );
}

/** Section 6 — Market Expansion: reuses Phase 2 (Idea Expansion) and Phase 3 (Strategic
 * Opportunity Discovery) outputs, presented as one consolidated visual instead of two separate
 * report-style sections. Each field is sourced from exactly one place — no item is repeated
 * across subsections:
 *   - Customer Segments      <- idea_expansion.customer_segments
 *   - Adjacent Markets       <- strategic_opportunity.adjacent_opportunities (richer reasoning
 *                               than idea_expansion's own adjacent_industries, so that one is not
 *                               separately re-shown here)
 *   - Expansion Paths        <- idea_expansion.pivot_opportunities
 *   - Partnerships           <- idea_expansion.partnerships
 *   - Pricing                <- idea_expansion.pricing_models
 *   - Future Evolution       <- strategic_opportunity.future_expansion
 *   - Growth Strategy        <- student3_outputs.growth_strategy (Phase 5 / Student 3 — validation/
 *                               acquisition/partnership/retention/expansion/experiment/kpi
 *                               recommendations; distinct content, not shown anywhere else)
 */
export function MarketExpansionSection({
  ideaExpansion,
  strategicOpportunity,
  growthStrategy = [],
}: {
  ideaExpansion: IdeaExpansion | null;
  strategicOpportunity: StrategicOpportunity | null;
  growthStrategy?: Student3GrowthItem[];
}) {
  return (
    <Section id="market-expansion" title="Market Expansion">
      <div className="space-y-6">
        <ItemList
          heading="Customer Segments"
          items={fromIdeaItems(ideaExpansion?.customer_segments ?? [])}
          emptyNote="No additional customer segments identified for this run."
        />
        <ItemList
          heading="Adjacent Markets"
          items={fromStrategicItems(strategicOpportunity?.adjacent_opportunities ?? [])}
          emptyNote="No adjacent markets identified for this run."
        />
        <ItemList
          heading="Expansion Paths"
          items={fromIdeaItems(ideaExpansion?.pivot_opportunities ?? [])}
          emptyNote="No expansion paths identified for this run."
        />
        <ItemList
          heading="Partnerships"
          items={fromIdeaItems(ideaExpansion?.partnerships ?? [])}
          emptyNote="No partnership ideas identified for this run."
        />
        <ItemList
          heading="Pricing"
          items={fromIdeaItems(ideaExpansion?.pricing_models ?? [])}
          emptyNote="No pricing models identified for this run."
        />
        <ItemList
          heading="Future Evolution"
          items={fromStrategicItems(strategicOpportunity?.future_expansion ?? [])}
          emptyNote="No future-evolution possibilities identified for this run."
        />
        <GrowthStrategyList items={growthStrategy} />
      </div>
    </Section>
  );
}
