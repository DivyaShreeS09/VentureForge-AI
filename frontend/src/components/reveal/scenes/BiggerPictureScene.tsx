import type {
  Analysis,
  BusinessModel,
  CompetitorAnalysis,
  IdeaExpansion,
  MarketIntelligence,
  RevenueEstimate,
  Student3GrowthItem,
  StrategicOpportunity,
} from "../../../types/api";
import { CollapsedScene } from "../CollapsedScene";
import { ConfidenceTierBadge } from "../ConfidenceTierBadge";
import { RevenueScenarios } from "../RevenueScenarios";

function ItemList({ title, items }: { title: string; items: { title: string; reason: string; confidence_tier: import("../../../types/api").IdeaConfidenceTier }[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <p className="text-forge-2 font-medium text-forge-text">{title}</p>
      {/* eslint-disable-next-line jsx-a11y/no-redundant-roles */}
      <ul role="list" className="mt-3 space-y-3">
        {items.map((item) => (
          // eslint-disable-next-line jsx-a11y/no-redundant-roles
          <li key={item.title} role="listitem">
            <div className="flex items-start justify-between gap-3">
              <p className="text-forge-2 text-forge-text">{item.title}</p>
              <ConfidenceTierBadge tier={item.confidence_tier} />
            </div>
            <p className="mt-1 text-forge-1 text-forge-text-secondary">{item.reason}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Scene 6 — The Bigger Picture. Competitors, expansion, pricing, business model, market, future
 * opportunities — everything else, collapsed by default. Merges MarketExpansionSection,
 * RiskDashboardSection's non-primary risks, and the previously-unrendered `business_model` object
 * and `market_intelligence` fields into one place. */
export function BiggerPictureScene({
  analysisId,
  ideaExpansion,
  strategicOpportunity,
  competitorAnalysis,
  marketIntelligence,
  businessModel,
  revenueEstimate,
  growthStrategy,
  onSaved,
}: {
  analysisId: string;
  ideaExpansion: IdeaExpansion | null;
  strategicOpportunity: StrategicOpportunity | null;
  competitorAnalysis: CompetitorAnalysis | null;
  marketIntelligence: MarketIntelligence | null;
  businessModel: BusinessModel | null;
  revenueEstimate: RevenueEstimate | null;
  growthStrategy: Student3GrowthItem[];
  onSaved: (updated: Analysis) => void;
}) {
  const verifiedCompetitors = competitorAnalysis?.verified_competitors ?? [];
  const indirectAlternatives = competitorAnalysis?.indirect_alternatives ?? [];

  return (
    <CollapsedScene eyebrow="The Bigger Picture" summary="Competitors, expansion, pricing, and where this could go.">
      <div className="space-y-10">
        {(verifiedCompetitors.length > 0 || indirectAlternatives.length > 0) && (
          <div>
            <p className="text-forge-2 font-medium text-forge-text">Competitors</p>
            {verifiedCompetitors.length > 0 && (
              // eslint-disable-next-line jsx-a11y/no-redundant-roles
              <ul role="list" className="mt-3 space-y-2">
                {verifiedCompetitors.map((c) => (
                  // eslint-disable-next-line jsx-a11y/no-redundant-roles
                  <li key={c.name} role="listitem" className="text-forge-2 text-forge-text-secondary">
                    <span className="text-forge-text">{c.name}</span> — {c.differentiation_gap}
                  </li>
                ))}
              </ul>
            )}
            {indirectAlternatives.length > 0 && (
              <p className="mt-2 text-forge-1 text-forge-text-secondary">
                Indirect alternatives: {indirectAlternatives.map((a) => a.category).join(", ")}
              </p>
            )}
          </div>
        )}

        {marketIntelligence && (
          <div>
            <p className="text-forge-2 font-medium text-forge-text">Market</p>
            <p className="mt-2 text-forge-2 text-forge-text-secondary">{marketIntelligence.market_summary}</p>
            {marketIntelligence.opportunity_drivers.length > 0 && (
              <p className="mt-2 text-forge-1 text-forge-text-secondary">
                Driving this: {marketIntelligence.opportunity_drivers.join("; ")}
              </p>
            )}
            {marketIntelligence.constraints.length > 0 && (
              <p className="mt-1 text-forge-1 text-forge-text-secondary">
                Constraints: {marketIntelligence.constraints.join("; ")}
              </p>
            )}
          </div>
        )}

        {businessModel && (
          <div>
            <p className="text-forge-2 font-medium text-forge-text">Business Model</p>
            <div className="mt-3 grid grid-cols-1 gap-4 forge-sm:grid-cols-2">
              <p className="text-forge-2 text-forge-text-secondary">
                <span className="text-forge-text-secondary">Value: </span>
                {businessModel.value_proposition}
              </p>
              <p className="text-forge-2 text-forge-text-secondary">
                <span className="text-forge-text-secondary">Revenue: </span>
                {businessModel.revenue_streams}
              </p>
              <p className="text-forge-2 text-forge-text-secondary">
                <span className="text-forge-text-secondary">Channels: </span>
                {businessModel.channels}
              </p>
              <p className="text-forge-2 text-forge-text-secondary">
                <span className="text-forge-text-secondary">Scalability: </span>
                {businessModel.scalability}
              </p>
            </div>
          </div>
        )}

        {revenueEstimate?.scenarios && (
          <div>
            <p className="text-forge-2 font-medium text-forge-text">Pricing &amp; Revenue</p>
            <div className="mt-3">
              <RevenueScenarios analysisId={analysisId} revenueEstimate={revenueEstimate} onSaved={onSaved} />
            </div>
          </div>
        )}

        {ideaExpansion && (
          <>
            <ItemList title="Customer Segments" items={ideaExpansion.customer_segments} />
            <ItemList title="Expansion Paths" items={ideaExpansion.pivot_opportunities} />
            <ItemList title="Partnerships" items={ideaExpansion.partnerships} />
          </>
        )}

        {strategicOpportunity && strategicOpportunity.future_expansion.length > 0 && (
          <ItemList
            title="Future Evolution"
            items={strategicOpportunity.future_expansion.map((f) => ({
              title: f.opportunity,
              reason: f.reason,
              confidence_tier: f.confidence_tier,
            }))}
          />
        )}

        {strategicOpportunity && strategicOpportunity.adjacent_opportunities.length > 0 && (
          <ItemList
            title="Adjacent Markets"
            items={strategicOpportunity.adjacent_opportunities.map((a) => ({
              title: a.opportunity,
              reason: a.reason,
              confidence_tier: a.confidence_tier,
            }))}
          />
        )}

        {growthStrategy.length > 0 && (
          <div>
            <p className="text-forge-2 font-medium text-forge-text">Growth Strategy</p>
            {/* eslint-disable-next-line jsx-a11y/no-redundant-roles */}
            <ul role="list" className="mt-3 space-y-2">
              {growthStrategy.map((item) => (
                // eslint-disable-next-line jsx-a11y/no-redundant-roles
                <li key={item.recommendation} role="listitem" className="text-forge-2 text-forge-text-secondary">
                  {item.recommendation}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </CollapsedScene>
  );
}
