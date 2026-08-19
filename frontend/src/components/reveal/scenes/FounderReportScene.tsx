import { motion } from "framer-motion";
import { useMotionTier } from "../../../motion/transitions";
import type { FounderReport, FounderReportAppendix, TaggedText } from "../../../types/api";
import { Scene } from "../Scene";
import { FounderReportTag } from "../FounderReportTag";
import { highlightKeywords } from "../../../utils/highlightKeywords";

/** One tagged claim: the sentence itself, plus its mandatory evidence/inference/recommendation/
 * assumption/experiment label — never rendered without it (see FounderReportTag). */
function Claim({ item }: { item: TaggedText | null | undefined }) {
  if (!item) return null;
  return (
    <div className="flex flex-col gap-1 forge-sm:flex-row forge-sm:items-baseline forge-sm:justify-between forge-sm:gap-4">
      <p className="text-forge-2 text-forge-desc">{highlightKeywords(item.content)}</p>
      <FounderReportTag category={item.category} />
    </div>
  );
}

function ClaimList({ items }: { items: TaggedText[] }) {
  if (items.length === 0) return null;
  return (
    // eslint-disable-next-line jsx-a11y/no-redundant-roles
    <ul role="list" className="space-y-3">
      {items.map((item, i) => (
        // eslint-disable-next-line jsx-a11y/no-redundant-roles
        <li key={i} role="listitem">
          <Claim item={item} />
        </li>
      ))}
    </ul>
  );
}

function ReportSection({ title, id, children }: { title: string; id?: string; children: React.ReactNode }) {
  return (
    <div id={id} className="scroll-mt-24 border-t border-forge-text/[.08] pt-8">
      <p className="text-forge-1 uppercase tracking-[0.15em] text-forge-label">{title}</p>
      <div className="mt-4">{children}</div>
    </div>
  );
}

/** Exported so `Reveal.tsx` can fold these into its single, page-level
 * `useRegisterCommandSections` call — only one component may own that registration at a time
 * (it replaces, not merges, the shared list), so this scene no longer calls the hook itself. The
 * old "Executive Hero" entry is gone along with the section it pointed to (see below). */
export const FOUNDER_REPORT_NAV_SECTIONS = [
  { id: "section-discoveries", label: "What We Discovered" },
  { id: "section-competitive-position", label: "Competitive Position" },
  { id: "section-next-30-days", label: "Next 30 Days" },
  { id: "section-market-strategy", label: "Market Strategy" },
  { id: "section-appendix", label: "Deep Dive" },
];

// Presentation-only read of founder_iq_report's existing `understanding_level` enum strings (see
// backend/app/agents/founder_intelligence.py) into a 0-4 bar fill — no new scoring, no new data.
const IQ_LEVEL_FILL: Record<string, number> = {
  "strong understanding": 4,
  "developing understanding": 2,
  "early-stage understanding": 1,
  "acknowledged gap — honestly flagged, not unknown to you": 2,
  "knowledge gap — not yet thought through": 1,
  "not assessed": 0,
};

function IqBar({ level }: { level: string }) {
  const fill = IQ_LEVEL_FILL[level] ?? 1;
  return (
    <div className="flex gap-1" aria-hidden="true">
      {[0, 1, 2, 3].map((i) => (
        <span key={i} className={`h-1.5 w-8 rounded-full ${i < fill ? "bg-forge-accent" : "bg-forge-text/[.12]"}`} />
      ))}
    </div>
  );
}

/** Combines the two ranked lists (advantages/problems) into exactly one ordered set of up to 5
 * discovery cards, alternating so a strength never sits alone at either end — presentation-only
 * interleaving of data that already exists, never a new ranking. */
function buildDiscoveries(report: FounderReport) {
  type Discovery = { key: string; kind: "advantage" | "problem"; dimension: string; headline: string; detail: React.ReactNode };
  const advantages: Discovery[] = report.three_biggest_advantages.map((a) => ({
    key: `a-${a.dimension}`,
    kind: "advantage",
    dimension: a.dimension,
    headline: a.advantage.content,
    detail: (
      <>
        <Claim item={a.evidence} />
        <Claim item={a.why_it_matters} />
        <Claim item={a.business_value} />
        <div className="mt-3 rounded-forge-md bg-forge-accent/[.08] p-4">
          <p className="text-forge-2 font-medium text-forge-cyan">How to leverage it</p>
          <div className="mt-1"><Claim item={a.how_to_leverage} /></div>
        </div>
      </>
    ),
  }));
  const problems: Discovery[] = report.three_biggest_problems.map((p) => ({
    key: `p-${p.dimension}`,
    kind: "problem",
    dimension: p.dimension,
    headline: p.problem.content,
    detail: (
      <>
        <Claim item={p.evidence} />
        <Claim item={p.why_it_matters} />
        <Claim item={p.business_consequence} />
        <div className="mt-3 rounded-forge-md bg-forge-accent/[.08] p-4">
          <p className="text-forge-2 font-medium text-forge-cyan">Do this next</p>
          <div className="mt-1"><Claim item={p.recommended_fix} /></div>
        </div>
      </>
    ),
  }));
  const combined: Discovery[] = [];
  let ai = 0;
  let pi = 0;
  while (combined.length < 5 && (ai < advantages.length || pi < problems.length)) {
    if (ai < advantages.length) combined.push(advantages[ai++]);
    if (combined.length < 5 && pi < problems.length) combined.push(problems[pi++]);
  }
  return combined;
}

/** Executive Dashboard Experience Sprint — an at-a-glance dashboard with guided exploration, not a
 * sequential story: everything the founder needs within 15 seconds sits in the hero, every
 * section below is scannable (cards/badges/timelines, never paragraphs), and full technical depth
 * lives behind one optional "Deep Dive" disclosure that never interrupts the main flow. Every
 * fact still comes from the exact same `mentor.founder_report` payload the backend already builds
 * (backend/app/agents/founder_report.py) — this component only changes presentation. */
export function FounderReportScene({ report }: { report: FounderReport }) {
  const sceneTransition = useMotionTier("scene");
  const discoveries = buildDiscoveries(report);
  const weeks = report.appendix.pilot_roadmap.weeks;
  const marketLabels = ["Pricing", "Go-To-Market", "First Customer", "Competitive Edge", "Feature Priority"];

  return (
    <Scene eyebrow="The Founder Report">
      {/* The Executive Hero this scene used to open with (name/stage/verdict/investment-ready/
          biggest risk & strength/highest-priority) is now shown exactly once, page-level, in
          `ExecutiveHero.tsx` — repeating it here was the single largest redundancy the live audit
          (Phase 0 of this sprint) found. Everything below picks up from "What We Discovered." */}
      <div className="space-y-16">
        {/* SECTION 2 — WHAT WE DISCOVERED: exactly 5 scannable cards, one sentence each. */}
        <ReportSection title="What We Discovered" id="section-discoveries">
          <ul role="list" className="grid grid-cols-1 gap-4 forge-sm:grid-cols-2">
            {discoveries.map((d, i) => (
              <motion.li
                key={d.key}
                initial={{ opacity: 0, y: 8 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-40px" }}
                transition={{ ...sceneTransition, delay: Math.min(i * 0.05, 0.2) }}
                className={`h-full ${i === 0 ? "forge-sm:col-span-2" : ""}`}
              >
                <details className="group flex h-full flex-col rounded-forge-lg border border-forge-text/[.08] bg-forge-surface-1 p-5">
                  <summary className="flex cursor-pointer list-none items-start justify-between gap-4">
                    <p className="text-forge-2 font-medium text-forge-heading">
                      <span aria-hidden="true" className={d.kind === "advantage" ? "text-forge-emerald" : "text-forge-rose"}>
                        {d.kind === "advantage" ? "✓ " : "⚠ "}
                      </span>
                      {highlightKeywords(d.headline)}
                    </p>
                    <span aria-hidden="true" className="shrink-0 text-forge-2 text-forge-text-tertiary transition-transform group-open:rotate-180">⌄</span>
                  </summary>
                  <div className="mt-4 space-y-3 border-t border-forge-text/[.08] pt-4">{d.detail}</div>
                </details>
              </motion.li>
            ))}
          </ul>
        </ReportSection>

        {/* Top Three Decisions and Investor View used to duplicate Mission Control and the
            Investor Review section (same `founder_strategy`/`investor_view` fields) — removed
            per Absolute Rule 1; both sections link back here instead of restating this content. */}

        {/* SECTION 5 — COMPETITIVE POSITION: visual progression, existing moat intelligence only. */}
        <ReportSection title="Competitive Position" id="section-competitive-position">
          <ol role="list" className="grid grid-cols-1 gap-4 forge-sm:grid-cols-4">
            {[
              { label: "Today", item: report.moat_and_competitive_position.what_competitors_can_copy_today },
              { label: "10 Customers", item: report.moat_and_competitive_position.defensible_after_10_customers },
              { label: "100 Customers", item: report.moat_and_competitive_position.defensible_after_100_customers },
              { label: "1,000 Customers", item: report.moat_and_competitive_position.defensible_after_1000_customers },
            ].map((stage, i, arr) => (
              <li key={stage.label} className="relative flex h-full flex-col rounded-forge-lg border border-forge-text/[.08] bg-forge-surface-1 p-4">
                <p className="text-forge-1 font-medium uppercase tracking-[0.1em] text-forge-gold">{stage.label}</p>
                <p className="mt-2 text-forge-1 text-forge-desc">{highlightKeywords(stage.item.content)}</p>
                {i < arr.length - 1 && (
                  <span aria-hidden="true" className="absolute -right-3 top-1/2 hidden -translate-y-1/2 text-forge-text-tertiary forge-sm:block">→</span>
                )}
              </li>
            ))}
          </ol>
          <p className="mt-3 text-forge-1 text-forge-helper">{report.moat_and_competitive_position.what_they_cannot_copy.content}</p>
        </ReportSection>

        {/* SECTION 6 — NEXT 30 DAYS: week-by-week. */}
        {weeks.length > 0 && (
          <ReportSection title="Next 30 Days" id="section-next-30-days">
            <ol role="list" className="grid grid-cols-1 gap-4 forge-sm:grid-cols-4">
              {weeks.map((w) => (
                <li key={w.week} className="flex h-full flex-col rounded-forge-lg border border-forge-text/[.08] bg-forge-surface-1 p-4">
                  <p className="text-forge-1 font-medium uppercase tracking-[0.1em] text-forge-gold">Week {w.week}</p>
                  <p className="mt-2 text-forge-2 font-medium text-forge-heading">{highlightKeywords(w.focus)}</p>
                  <ul role="list" className="mt-2 space-y-1 text-forge-1 text-forge-desc">
                    {w.activities.map((a, i) => (
                      <li key={i}>{highlightKeywords(a)}</li>
                    ))}
                  </ul>
                </li>
              ))}
            </ol>
          </ReportSection>
        )}

        {/* SECTION 7 — MARKET STRATEGY. */}
        <ReportSection title="Market Strategy" id="section-market-strategy">
          <div className="grid grid-cols-1 gap-4 forge-sm:grid-cols-3">
            {report.market_insight.slice(0, 5).map((item, i) => (
              <details key={i} className="group flex h-full flex-col rounded-forge-lg border border-forge-text/[.08] bg-forge-surface-1 p-4">
                <summary className="flex cursor-pointer list-none items-start justify-between gap-2">
                  <p className="text-forge-1 font-medium uppercase tracking-[0.1em] text-forge-label">{marketLabels[i] ?? "Insight"}</p>
                  <span aria-hidden="true" className="shrink-0 text-forge-2 text-forge-text-tertiary transition-transform group-open:rotate-180">⌄</span>
                </summary>
                <div className="mt-3 border-t border-forge-text/[.08] pt-3">
                  <Claim item={item} />
                </div>
              </details>
            ))}
          </div>
        </ReportSection>

        {/* SECTION 8 — OPTIONAL DEEP DIVE: everything else. Collapsed by default; never
            interrupts the main dashboard above. Native <details> so it needs no extra state. */}
        <details id="section-appendix" className="scroll-mt-24 border-t border-forge-text/[.08] pt-8">
          <summary className="cursor-pointer text-forge-1 uppercase tracking-[0.15em] text-forge-text-secondary">
            Deep dive — evidence, methodology, and the full technical report
          </summary>
          <div className="mt-6">
            <AppendixContent appendix={report.appendix} />
          </div>
        </details>
      </div>

      <p className="mt-10 max-w-[62ch] text-forge-1 text-forge-text-secondary/80">{report.disclaimer}</p>
    </Scene>
  );
}

/** Everything the report used to show inline, kept intact for anyone who wants the underlying
 * depth — a technical reviewer, a judge checking rigor, a founder who wants the raw detail. */
function AppendixContent({ appendix }: { appendix: FounderReportAppendix }) {
  return (
    <div className="space-y-8">
      <ReportSection title="Problem">
        <Claim item={appendix.problem_analysis} />
      </ReportSection>
      <ReportSection title="Customer">
        <Claim item={appendix.customer_analysis} />
      </ReportSection>
      <ReportSection title="Business Model">
        <Claim item={appendix.business_model} />
      </ReportSection>
      <ReportSection title="Market Position">
        <Claim item={appendix.market_position} />
      </ReportSection>

      <ReportSection title="Pricing Strategy">
        <div className="space-y-3">
          <Claim item={appendix.pricing_strategy.recommendation} />
          <ClaimList items={appendix.pricing_strategy.rationale} />
        </div>
      </ReportSection>

      <ReportSection title="Go-To-Market Strategy">
        <div className="grid grid-cols-1 gap-6 forge-sm:grid-cols-2">
          <div>
            <p className="text-forge-2 font-medium text-forge-text">Who to approach first</p>
            <div className="mt-2"><Claim item={appendix.go_to_market_strategy.who_to_approach_first} /></div>
          </div>
          <div>
            <p className="text-forge-2 font-medium text-forge-text">Where to find them</p>
            <div className="mt-2"><Claim item={appendix.go_to_market_strategy.first_customers} /></div>
          </div>
          <div>
            <p className="text-forge-2 font-medium text-forge-text">Early adopter profile</p>
            <div className="mt-2"><Claim item={appendix.go_to_market_strategy.early_adopter_profile} /></div>
          </div>
          <div>
            <p className="text-forge-2 font-medium text-forge-text">Sales motion</p>
            <div className="mt-2"><Claim item={appendix.go_to_market_strategy.sales_motion} /></div>
          </div>
        </div>
        <div className="mt-6">
          <p className="text-forge-2 font-medium text-forge-text">Distribution channels</p>
          <div className="mt-3"><ClaimList items={appendix.go_to_market_strategy.distribution_channels} /></div>
        </div>
        <div className="mt-6">
          <p className="text-forge-2 font-medium text-forge-text">Validation roadmap</p>
          <div className="mt-3"><ClaimList items={appendix.go_to_market_strategy.validation_roadmap} /></div>
        </div>
        <div className="mt-6">
          <p className="text-forge-2 font-medium text-forge-text">Expansion roadmap</p>
          <div className="mt-3"><ClaimList items={appendix.go_to_market_strategy.expansion_roadmap} /></div>
        </div>
      </ReportSection>

      <ReportSection title="Competitive Landscape">
        <Claim item={appendix.competitive_landscape.summary} />
        <div className="mt-4">
          <p className="text-forge-2 font-medium text-forge-text">Likely alternatives customers use today</p>
          <div className="mt-3"><ClaimList items={appendix.competitive_landscape.likely_alternatives} /></div>
        </div>
        <div className="mt-6 grid grid-cols-1 gap-6 forge-sm:grid-cols-2">
          <div>
            <p className="text-forge-2 font-medium text-forge-text">Switching behavior</p>
            <div className="mt-2"><Claim item={appendix.competitive_landscape.switching_behavior} /></div>
          </div>
          <div>
            <p className="text-forge-2 font-medium text-forge-text">Switching friction</p>
            <div className="mt-2"><Claim item={appendix.competitive_landscape.switching_friction} /></div>
          </div>
        </div>
        <div className="mt-6">
          <p className="text-forge-2 font-medium text-forge-text">How to win</p>
          <div className="mt-2"><Claim item={appendix.competitive_landscape.how_to_win} /></div>
        </div>
        {appendix.competitive_landscape.similar_historical_ventures.length > 0 && (
          <div className="mt-6">
            <p className="text-forge-2 font-medium text-forge-text">Similar historical ventures</p>
            <div className="mt-3"><ClaimList items={appendix.competitive_landscape.similar_historical_ventures} /></div>
          </div>
        )}
      </ReportSection>

      <ReportSection title="Critical Blind Spots">
        <ul role="list" className="space-y-5">
          {appendix.critical_blind_spots.map((bs, i) => (
            <li key={i} className="space-y-1.5">
              <p className="text-forge-2 font-medium text-forge-text">{bs.title.content}</p>
              <Claim item={bs.detail} />
              <Claim item={bs.why_investors_care} />
            </li>
          ))}
        </ul>
      </ReportSection>

      <ReportSection title="Investor Questions">
        <ul role="list" className="space-y-4">
          {appendix.investor_questions.map((q, i) => (
            <li key={i} className="space-y-1">
              <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-text-secondary/70">{q.persona}</p>
              <Claim item={q.question} />
            </li>
          ))}
        </ul>
      </ReportSection>

      <ReportSection title="Founder Challenge Mode">
        <ul role="list" className="space-y-5">
          {appendix.founder_challenge_mode.map((c, i) => (
            <li key={i} className="space-y-1.5">
              <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-text-secondary/70">{c.objection_category.replace(/_/g, " ")}</p>
              <Claim item={c.objection} />
              <div className="pl-4 border-l border-forge-text/[.12]">
                <p className="text-forge-2 font-medium text-forge-text">How to overcome it</p>
                <div className="mt-1"><Claim item={c.how_to_overcome} /></div>
              </div>
            </li>
          ))}
        </ul>
      </ReportSection>

      <ReportSection title="Moat Intelligence">
        <ClaimList items={appendix.moat_intelligence} />
      </ReportSection>

      <ReportSection title="Feature Gap vs. Similar Ventures">
        <ClaimList items={appendix.feature_gap_vs_market} />
      </ReportSection>

      <ReportSection title="AI Feature Suggestions">
        <ClaimList items={appendix.ai_feature_suggestions} />
      </ReportSection>

      <div className="grid grid-cols-1 gap-8 forge-sm:grid-cols-2">
        <ReportSection title="Risk Assessment">
          <ClaimList items={appendix.risk_assessment} />
        </ReportSection>
        <ReportSection title="Opportunity Assessment">
          <ClaimList items={appendix.opportunity_assessment} />
        </ReportSection>
      </div>

      <div className="grid grid-cols-1 gap-8 forge-sm:grid-cols-2">
        <ReportSection title="Funding Readiness">
          <Claim item={appendix.funding_readiness} />
        </ReportSection>
        <ReportSection title="Historical Pattern Signal">
          <Claim item={appendix.historical_pattern_signal} />
        </ReportSection>
      </div>

      <ReportSection title="Funding Stage Ladder">
        <p className="text-forge-2 text-forge-text">
          Current stage: <span className="font-medium capitalize">{appendix.funding_stage_ladder.current_stage?.replace(/_/g, " ")}</span>
          {appendix.funding_stage_ladder.next_stage && (
            <> → <span className="font-medium capitalize">{appendix.funding_stage_ladder.next_stage.replace(/_/g, " ")}</span></>
          )}
        </p>
        <div className="mt-3 space-y-2">
          <Claim item={appendix.funding_stage_ladder.what_moves_you_forward} />
          <Claim item={appendix.funding_stage_ladder.basis} />
        </div>
      </ReportSection>

      <ReportSection title="Founder IQ Report">
        {appendix.founder_iq_report.dominant_thinking_pattern && (
          <div className="mb-5"><Claim item={appendix.founder_iq_report.dominant_thinking_pattern} /></div>
        )}
        <ul role="list" className="grid grid-cols-1 gap-5 forge-sm:grid-cols-2">
          {Object.entries(appendix.founder_iq_report.category_scores).map(([category, score]) => (
            <li key={category} className="space-y-1.5">
              <p className="text-forge-2 font-medium capitalize text-forge-text">{category}</p>
              <IqBar level={score.understanding_level} />
              <p className="text-forge-1 text-forge-text-secondary/80">{score.understanding_level}</p>
            </li>
          ))}
        </ul>
      </ReportSection>

      <ReportSection title="Pilot Roadmap">
        <div className="space-y-4">
          {appendix.pilot_roadmap.weeks.map((w) => (
            <div key={w.week}>
              <p className="text-forge-2 font-medium text-forge-text">Week {w.week}: {w.focus}</p>
              <ul role="list" className="mt-1 list-disc pl-5 text-forge-2 text-forge-text-secondary">
                {w.activities.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <div className="mt-6 grid grid-cols-1 gap-4 forge-sm:grid-cols-2">
          <div>
            <p className="text-forge-2 font-medium text-forge-text">Pilot customers</p>
            <div className="mt-1"><Claim item={appendix.pilot_roadmap.pilot_customers} /></div>
          </div>
          <div>
            <p className="text-forge-2 font-medium text-forge-text">Validation metrics</p>
            <div className="mt-1"><Claim item={appendix.pilot_roadmap.validation_metrics} /></div>
          </div>
          <div>
            <p className="text-forge-2 font-medium text-forge-text">Pivot conditions</p>
            <div className="mt-1"><Claim item={appendix.pilot_roadmap.pivot_conditions} /></div>
          </div>
          <div>
            <p className="text-forge-2 font-medium text-forge-text">Go / No-Go</p>
            <div className="mt-1"><Claim item={appendix.pilot_roadmap.go_no_go_decision} /></div>
          </div>
        </div>
      </ReportSection>

      <ReportSection title="Startup Benchmark — Compared to What?">
        <div className="grid grid-cols-1 gap-5 forge-sm:grid-cols-2">
          <div>
            <p className="text-forge-2 font-medium text-forge-text">Industry positioning</p>
            <div className="mt-1"><Claim item={appendix.startup_benchmark.industry_positioning} /></div>
          </div>
          <div>
            <p className="text-forge-2 font-medium text-forge-text">Pricing approach</p>
            <div className="mt-1"><Claim item={appendix.startup_benchmark.pricing_approach} /></div>
          </div>
          <div>
            <p className="text-forge-2 font-medium text-forge-text">Customer acquisition pattern</p>
            <div className="mt-1"><Claim item={appendix.startup_benchmark.customer_acquisition_pattern} /></div>
          </div>
          <div>
            <p className="text-forge-2 font-medium text-forge-text">Typical pilot strategy</p>
            <div className="mt-1"><Claim item={appendix.startup_benchmark.typical_pilot_strategy} /></div>
          </div>
          <div>
            <p className="text-forge-2 font-medium text-forge-text">Typical first customer</p>
            <div className="mt-1"><Claim item={appendix.startup_benchmark.typical_first_customer} /></div>
          </div>
          <div>
            <p className="text-forge-2 font-medium text-forge-text">Common mistakes</p>
            <div className="mt-1"><Claim item={appendix.startup_benchmark.common_mistakes} /></div>
          </div>
          <div>
            <p className="text-forge-2 font-medium text-forge-text">Growth path</p>
            <div className="mt-1"><Claim item={appendix.startup_benchmark.growth_path} /></div>
          </div>
        </div>
        {appendix.startup_benchmark.retrieved_ventures_used.length > 0 && (
          <div className="mt-6">
            <p className="text-forge-2 font-medium text-forge-text">Retrieved similar ventures used</p>
            <ul role="list" className="mt-2 space-y-1 text-forge-2 text-forge-text-secondary">
              {appendix.startup_benchmark.retrieved_ventures_used.map((v, i) => (
                <li key={i}>
                  {v.name} ({v.industry}, similarity {Number.isFinite(v.similarity) ? v.similarity.toFixed(2) : "0.00"})
                </li>
              ))}
            </ul>
          </div>
        )}
      </ReportSection>

      <ReportSection title="Investor Intelligence">
        <div>
          <p className="text-forge-2 font-medium text-forge-text">Why similar ventures succeed</p>
          <div className="mt-2"><ClaimList items={appendix.investor_intelligence.why_similar_ventures_succeed} /></div>
        </div>
        <div className="mt-6">
          <p className="text-forge-2 font-medium text-forge-text">Most important milestones</p>
          <div className="mt-2"><ClaimList items={appendix.investor_intelligence.most_important_milestones} /></div>
        </div>
      </ReportSection>

      <ReportSection title="Industry Context">
        <div>
          <p className="text-forge-2 font-medium text-forge-text">Typical customer</p>
          <div className="mt-1"><Claim item={appendix.industry_context.typical_customer} /></div>
        </div>
        <div className="mt-4">
          <p className="text-forge-2 font-medium text-forge-text">Buying process</p>
          <div className="mt-1"><Claim item={appendix.industry_context.buying_process} /></div>
        </div>
        <div className="mt-4">
          <p className="text-forge-2 font-medium text-forge-text">Sales cycle</p>
          <div className="mt-1"><Claim item={appendix.industry_context.sales_cycle} /></div>
        </div>
        <div className="mt-4">
          <p className="text-forge-2 font-medium text-forge-text">Common integrations</p>
          <div className="mt-2"><ClaimList items={appendix.industry_context.common_integrations} /></div>
        </div>
        <div className="mt-4">
          <p className="text-forge-2 font-medium text-forge-text">Expected KPIs</p>
          <div className="mt-2"><ClaimList items={appendix.industry_context.expected_kpis} /></div>
        </div>
        <div className="mt-4">
          <p className="text-forge-2 font-medium text-forge-text">Procurement difficulty</p>
          <div className="mt-1"><Claim item={appendix.industry_context.procurement_difficulty} /></div>
        </div>
        <div className="mt-4">
          <p className="text-forge-2 font-medium text-forge-text">Enterprise objections</p>
          <div className="mt-2"><ClaimList items={appendix.industry_context.enterprise_objections} /></div>
        </div>
        <div className="mt-4">
          <p className="text-forge-2 font-medium text-forge-text">SMB objections</p>
          <div className="mt-2"><ClaimList items={appendix.industry_context.smb_objections} /></div>
        </div>
        <div className="mt-4">
          <p className="text-forge-2 font-medium text-forge-text">Customer acquisition channels</p>
          <div className="mt-2"><ClaimList items={appendix.industry_context.customer_acquisition_channels} /></div>
        </div>
        <div className="mt-4">
          <p className="text-forge-2 font-medium text-forge-text">Retention strategy</p>
          <div className="mt-1"><Claim item={appendix.industry_context.retention_strategy} /></div>
        </div>
        <div className="mt-4">
          <p className="text-forge-2 font-medium text-forge-text">Expansion triggers</p>
          <div className="mt-2"><ClaimList items={appendix.industry_context.expansion_triggers} /></div>
        </div>
        <div className="mt-4">
          <p className="text-forge-2 font-medium text-forge-text">Enterprise readiness checklist</p>
          <div className="mt-2"><ClaimList items={appendix.industry_context.enterprise_readiness_checklist} /></div>
        </div>
        <div className="mt-4">
          <p className="text-forge-2 font-medium text-forge-text">Regulatory considerations</p>
          <div className="mt-1"><Claim item={appendix.industry_context.regulatory_considerations} /></div>
        </div>
        <div className="mt-4">
          <p className="text-forge-2 font-medium text-forge-text">Technical stack expectations</p>
          <div className="mt-1"><Claim item={appendix.industry_context.technical_stack_expectations} /></div>
        </div>
        <div className="mt-4">
          <p className="text-forge-2 font-medium text-forge-text">Typical differentiation</p>
          <div className="mt-1"><Claim item={appendix.industry_context.typical_differentiation} /></div>
        </div>
        <div className="mt-4">
          <p className="text-forge-2 font-medium text-forge-text">Common feature roadmap</p>
          <div className="mt-2"><ClaimList items={appendix.industry_context.common_feature_roadmap} /></div>
        </div>
      </ReportSection>

      <ReportSection title="Evidence Supporting Strengths">
        <ClaimList items={appendix.evidence_supporting_strengths} />
      </ReportSection>

      <ReportSection title="Final Mentor Verdict">
        <Claim item={appendix.final_mentor_verdict} />
      </ReportSection>

      <p className="text-forge-1 text-forge-text-secondary/80">{appendix.knowledge_transparency_note}</p>
    </div>
  );
}
