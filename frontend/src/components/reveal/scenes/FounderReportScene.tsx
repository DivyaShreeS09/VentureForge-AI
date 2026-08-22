import { motion } from "framer-motion";
import { useMotionTier } from "../../../motion/transitions";
import type {
  FounderReport,
  FounderReportAppendix,
  TaggedText,
} from "../../../types/api";
import { Scene } from "../Scene";
import { FounderReportTag } from "../FounderReportTag";
import { highlightKeywords } from "../../../utils/highlightKeywords";
/* =========================================================
   Speaker button
   ========================================================= */


/* =========================================================
   Reusable AI claim
   ========================================================= */

function Claim({
  item,
}: {
  item: TaggedText | null | undefined;
}) {
  if (!item) return null;

  return (
    <div className="flex flex-col gap-1 forge-sm:flex-row forge-sm:items-start forge-sm:justify-between forge-sm:gap-4">
      <div className="flex min-w-0 flex-1 items-start gap-2">
        <p className="flex-1 text-forge-2 text-forge-desc">
          {highlightKeywords(item.content)}
        </p>

        
      </div>

      <FounderReportTag category={item.category} />
    </div>
  );
}

function ClaimList({
  items,
}: {
  items: TaggedText[];
}) {
  if (!items || items.length === 0) return null;

  return (
    <ul role="list" className="space-y-3">
      {items.map((item, index) => (
        <li key={index}>
          <Claim item={item} />
        </li>
      ))}
    </ul>
  );
}

/* =========================================================
   Report section
   ========================================================= */

function ReportSection({
  title,
  id,
  children,
}: {
  title: string;
  id?: string;
  children: React.ReactNode;
}) {
  return (
    <section
      id={id}
      className="scroll-mt-24 border-t border-forge-text/[.08] pt-8"
    >
      <div className="flex items-center gap-2">
        <p className="text-forge-1 uppercase tracking-[0.15em] text-forge-label">
          {title}
        </p>

        
      </div>

      <div className="mt-4">{children}</div>
    </section>
  );
}

/* =========================================================
   Navigation
   ========================================================= */

export const FOUNDER_REPORT_NAV_SECTIONS = [
  {
    id: "section-discoveries",
    label: "What We Discovered",
  },
  {
    id: "section-competitive-position",
    label: "Competitive Position",
  },
  {
    id: "section-next-30-days",
    label: "Next 30 Days",
  },
  {
    id: "section-market-strategy",
    label: "Market Strategy",
  },
  {
    id: "section-appendix",
    label: "Deep Dive",
  },
];

/* =========================================================
   Founder IQ
   ========================================================= */

const IQ_LEVEL_FILL: Record<string, number> = {
  "strong understanding": 4,
  "developing understanding": 2,
  "early-stage understanding": 1,
  "acknowledged gap â€” honestly flagged, not unknown to you": 2,
  "knowledge gap â€” not yet thought through": 1,
  "not assessed": 0,
};

function IqBar({
  level,
}: {
  level: string;
}) {
  const fill = IQ_LEVEL_FILL[level] ?? 1;

  return (
    <div
      className="flex gap-1"
      aria-label={`Understanding level: ${level}`}
    >
      {[0, 1, 2, 3].map((index) => (
        <span
          key={index}
          aria-hidden="true"
          className={`h-1.5 w-8 rounded-full ${
            index < fill
              ? "bg-forge-accent"
              : "bg-forge-text/[.12]"
          }`}
        />
      ))}
    </div>
  );
}

/* =========================================================
   Discovery cards
   ========================================================= */

type Discovery = {
  key: string;
  kind: "advantage" | "problem";
  dimension: string;
  headline: string;
  detail: React.ReactNode;
};

function buildDiscoveries(
  report: FounderReport,
): Discovery[] {
  const advantages: Discovery[] =
    report.three_biggest_advantages.map((a) => ({
      key: `a-${a.dimension}`,
      kind: "advantage",
      dimension: a.dimension,
      headline: a.advantage.content,
      detail: (
        <div className="space-y-3">
          <Claim item={a.evidence} />
          <Claim item={a.why_it_matters} />
          <Claim item={a.business_value} />

          <div className="rounded-forge-md bg-forge-accent/[.08] p-4">
            <div className="flex items-center gap-2">
              <p className="text-forge-2 font-medium text-forge-cyan">
                How to leverage it
              </p>

              
            </div>

            <div className="mt-1">
              <Claim item={a.how_to_leverage} />
            </div>
          </div>
        </div>
      ),
    }));

  const problems: Discovery[] =
    report.three_biggest_problems.map((p) => ({
      key: `p-${p.dimension}`,
      kind: "problem",
      dimension: p.dimension,
      headline: p.problem.content,
      detail: (
        <div className="space-y-3">
          <Claim item={p.evidence} />
          <Claim item={p.why_it_matters} />
          <Claim item={p.business_consequence} />

          <div className="rounded-forge-md bg-forge-accent/[.08] p-4">
            <div className="flex items-center gap-2">
              <p className="text-forge-2 font-medium text-forge-cyan">
                Do this next
              </p>

              
            </div>

            <div className="mt-1">
              <Claim item={p.recommended_fix} />
            </div>
          </div>
        </div>
      ),
    }));

  const combined: Discovery[] = [];

  let advantageIndex = 0;
  let problemIndex = 0;

  while (
    combined.length < 5 &&
    (advantageIndex < advantages.length ||
      problemIndex < problems.length)
  ) {
    if (advantageIndex < advantages.length) {
      combined.push(advantages[advantageIndex]);
      advantageIndex += 1;
    }

    if (
      combined.length < 5 &&
      problemIndex < problems.length
    ) {
      combined.push(problems[problemIndex]);
      problemIndex += 1;
    }
  }

  return combined;
}

/* =========================================================
   Appendix
   ========================================================= */

function AppendixContent({
  appendix,
}: {
  appendix: FounderReportAppendix;
}) {
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
          <Claim
            item={appendix.pricing_strategy.recommendation}
          />
          <ClaimList
            items={appendix.pricing_strategy.rationale}
          />
        </div>
      </ReportSection>

      <ReportSection title="Go-To-Market Strategy">
        <div className="grid grid-cols-1 gap-6 forge-sm:grid-cols-2">
          <div>
            <p className="text-forge-2 font-medium text-forge-text">
              Who to approach first
            </p>

            <div className="mt-2">
              <Claim
                item={
                  appendix.go_to_market_strategy
                    .who_to_approach_first
                }
              />
            </div>
          </div>

          <div>
            <p className="text-forge-2 font-medium text-forge-text">
              Where to find them
            </p>

            <div className="mt-2">
              <Claim
                item={
                  appendix.go_to_market_strategy
                    .first_customers
                }
              />
            </div>
          </div>

          <div>
            <p className="text-forge-2 font-medium text-forge-text">
              Early adopter profile
            </p>

            <div className="mt-2">
              <Claim
                item={
                  appendix.go_to_market_strategy
                    .early_adopter_profile
                }
              />
            </div>
          </div>

          <div>
            <p className="text-forge-2 font-medium text-forge-text">
              Sales motion
            </p>

            <div className="mt-2">
              <Claim
                item={
                  appendix.go_to_market_strategy
                    .sales_motion
                }
              />
            </div>
          </div>
        </div>

        <div className="mt-6">
          <p className="text-forge-2 font-medium text-forge-text">
            Distribution channels
          </p>

          <div className="mt-3">
            <ClaimList
              items={
                appendix.go_to_market_strategy
                  .distribution_channels
              }
            />
          </div>
        </div>

        <div className="mt-6">
          <p className="text-forge-2 font-medium text-forge-text">
            Validation roadmap
          </p>

          <div className="mt-3">
            <ClaimList
              items={
                appendix.go_to_market_strategy
                  .validation_roadmap
              }
            />
          </div>
        </div>

        <div className="mt-6">
          <p className="text-forge-2 font-medium text-forge-text">
            Expansion roadmap
          </p>

          <div className="mt-3">
            <ClaimList
              items={
                appendix.go_to_market_strategy
                  .expansion_roadmap
              }
            />
          </div>
        </div>
      </ReportSection>

      <ReportSection title="Competitive Landscape">
        <Claim
          item={appendix.competitive_landscape.summary}
        />

        <div className="mt-4">
          <p className="text-forge-2 font-medium text-forge-text">
            Likely alternatives customers use today
          </p>

          <div className="mt-3">
            <ClaimList
              items={
                appendix.competitive_landscape
                  .likely_alternatives
              }
            />
          </div>
        </div>

        <div className="mt-6 grid grid-cols-1 gap-6 forge-sm:grid-cols-2">
          <div>
            <p className="text-forge-2 font-medium text-forge-text">
              Switching behavior
            </p>

            <div className="mt-2">
              <Claim
                item={
                  appendix.competitive_landscape
                    .switching_behavior
                }
              />
            </div>
          </div>

          <div>
            <p className="text-forge-2 font-medium text-forge-text">
              Switching friction
            </p>

            <div className="mt-2">
              <Claim
                item={
                  appendix.competitive_landscape
                    .switching_friction
                }
              />
            </div>
          </div>
        </div>

        <div className="mt-6">
          <p className="text-forge-2 font-medium text-forge-text">
            How to win
          </p>

          <div className="mt-2">
            <Claim
              item={
                appendix.competitive_landscape
                  .how_to_win
              }
            />
          </div>
        </div>

        {appendix.competitive_landscape
          .similar_historical_ventures.length > 0 && (
          <div className="mt-6">
            <p className="text-forge-2 font-medium text-forge-text">
              Similar historical ventures
            </p>

            <div className="mt-3">
              <ClaimList
                items={
                  appendix.competitive_landscape
                    .similar_historical_ventures
                }
              />
            </div>
          </div>
        )}
      </ReportSection>

      <ReportSection title="Critical Blind Spots">
        <ul role="list" className="space-y-5">
          {appendix.critical_blind_spots.map(
            (blindSpot, index) => (
              <li key={index} className="space-y-2">
                <div className="flex items-start gap-2">
                  <p className="flex-1 text-forge-2 font-medium text-forge-text">
                    {blindSpot.title.content}
                  </p>

                  
                </div>

                <Claim item={blindSpot.detail} />

                <Claim
                  item={blindSpot.why_investors_care}
                />
              </li>
            ),
          )}
        </ul>
      </ReportSection>

      <ReportSection title="Investor Questions">
        <ul role="list" className="space-y-4">
          {appendix.investor_questions.map(
            (question, index) => (
              <li key={index} className="space-y-1">
                <div className="flex items-center gap-2">
                  <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-text-secondary/70">
                    {question.persona}
                  </p>

                  
                </div>

                <Claim item={question.question} />
              </li>
            ),
          )}
        </ul>
      </ReportSection>

      <ReportSection title="Founder Challenge Mode">
        <ul role="list" className="space-y-5">
          {appendix.founder_challenge_mode.map(
            (challenge, index) => (
              <li key={index} className="space-y-2">
                <div className="flex items-center gap-2">
                  <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-text-secondary/70">
                    {challenge.objection_category.replace(
                      /_/g,
                      " ",
                    )}
                  </p>

                  
                </div>

                <Claim item={challenge.objection} />

                <div className="border-l border-forge-text/[.12] pl-4">
                  <div className="flex items-center gap-2">
                    <p className="text-forge-2 font-medium text-forge-text">
                      How to overcome it
                    </p>

                    
                  </div>

                  <div className="mt-1">
                    <Claim
                      item={challenge.how_to_overcome}
                    />
                  </div>
                </div>
              </li>
            ),
          )}
        </ul>
      </ReportSection>

      <ReportSection title="Moat Intelligence">
        <ClaimList items={appendix.moat_intelligence} />
      </ReportSection>

      <ReportSection title="Feature Gap vs. Similar Ventures">
        <ClaimList
          items={appendix.feature_gap_vs_market}
        />
      </ReportSection>

      <ReportSection title="AI Feature Suggestions">
        <ClaimList
          items={appendix.ai_feature_suggestions}
        />
      </ReportSection>

      <div className="grid grid-cols-1 gap-8 forge-sm:grid-cols-2">
        <ReportSection title="Risk Assessment">
          <ClaimList items={appendix.risk_assessment} />
        </ReportSection>

        <ReportSection title="Opportunity Assessment">
          <ClaimList
            items={appendix.opportunity_assessment}
          />
        </ReportSection>
      </div>

      <div className="grid grid-cols-1 gap-8 forge-sm:grid-cols-2">
        <ReportSection title="Funding Readiness">
          <Claim item={appendix.funding_readiness} />
        </ReportSection>

        <ReportSection title="Historical Pattern Signal">
          <Claim
            item={
              appendix.historical_pattern_signal
            }
          />
        </ReportSection>
      </div>

      <ReportSection title="Funding Stage Ladder">
        <div className="flex items-start gap-2">
          <p className="flex-1 text-forge-2 text-forge-text">
            Current stage:{" "}
            <span className="font-medium capitalize">
              {appendix.funding_stage_ladder.current_stage?.replace(
                /_/g,
                " ",
              )}
            </span>

            {appendix.funding_stage_ladder.next_stage && (
              <>
                {" "}
                â†’
                <span className="font-medium capitalize">
                  {" "}
                  {appendix.funding_stage_ladder.next_stage.replace(
                    /_/g,
                    " ",
                  )}
                </span>
              </>
            )}
          </p>

          
        </div>

        <div className="mt-3 space-y-2">
          <Claim
            item={
              appendix.funding_stage_ladder
                .what_moves_you_forward
            }
          />

          <Claim
            item={appendix.funding_stage_ladder.basis}
          />
        </div>
      </ReportSection>

      <ReportSection title="Founder IQ Report">
        {appendix.founder_iq_report
          .dominant_thinking_pattern && (
          <div className="mb-5">
            <Claim
              item={
                appendix.founder_iq_report
                  .dominant_thinking_pattern
              }
            />
          </div>
        )}

        <ul
          role="list"
          className="grid grid-cols-1 gap-5 forge-sm:grid-cols-2"
        >
          {Object.entries(
            appendix.founder_iq_report.category_scores,
          ).map(([category, score]) => (
            <li key={category} className="space-y-2">
              <p className="text-forge-2 font-medium capitalize text-forge-text">
                {category}
              </p>

              <IqBar
                level={score.understanding_level}
              />

              <div className="flex items-center gap-2">
                <p className="text-forge-1 text-forge-text-secondary/80">
                  {score.understanding_level}
                </p>

                
              </div>
            </li>
          ))}
        </ul>
      </ReportSection>

      <ReportSection title="Pilot Roadmap">
        <div className="space-y-4">
          {appendix.pilot_roadmap.weeks.map((week) => (
            <div key={week.week}>
              <div className="flex items-center gap-2">
                <p className="text-forge-2 font-medium text-forge-text">
                  Week {week.week}: {week.focus}
                </p>

                
              </div>

              <ul
                role="list"
                className="mt-1 list-disc pl-5 text-forge-2 text-forge-text-secondary"
              >
                {week.activities.map(
                  (activity, index) => (
                    <li key={index}>
                      <div className="flex items-start gap-2">
                        <span className="flex-1">
                          {activity}
                        </span>

                        
                      </div>
                    </li>
                  ),
                )}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-6 grid grid-cols-1 gap-4 forge-sm:grid-cols-2">
          <div>
            <p className="text-forge-2 font-medium text-forge-text">
              Pilot customers
            </p>

            <Claim
              item={
                appendix.pilot_roadmap.pilot_customers
              }
            />
          </div>

          <div>
            <p className="text-forge-2 font-medium text-forge-text">
              Validation metrics
            </p>

            <Claim
              item={
                appendix.pilot_roadmap.validation_metrics
              }
            />
          </div>

          <div>
            <p className="text-forge-2 font-medium text-forge-text">
              Pivot conditions
            </p>

            <Claim
              item={
                appendix.pilot_roadmap.pivot_conditions
              }
            />
          </div>

          <div>
            <p className="text-forge-2 font-medium text-forge-text">
              Go / No-Go
            </p>

            <Claim
              item={
                appendix.pilot_roadmap.go_no_go_decision
              }
            />
          </div>
        </div>
      </ReportSection>

      <ReportSection title="Startup Benchmark â€” Compared to What?">
        <div className="grid grid-cols-1 gap-5 forge-sm:grid-cols-2">
          <div>
            <p className="text-forge-2 font-medium text-forge-text">
              Industry positioning
            </p>

            <Claim
              item={
                appendix.startup_benchmark
                  .industry_positioning
              }
            />
          </div>

          <div>
            <p className="text-forge-2 font-medium text-forge-text">
              Pricing approach
            </p>

            <Claim
              item={
                appendix.startup_benchmark
                  .pricing_approach
              }
            />
          </div>

          <div>
            <p className="text-forge-2 font-medium text-forge-text">
              Customer acquisition pattern
            </p>

            <Claim
              item={
                appendix.startup_benchmark
                  .customer_acquisition_pattern
              }
            />
          </div>

          <div>
            <p className="text-forge-2 font-medium text-forge-text">
              Typical pilot strategy
            </p>

            <Claim
              item={
                appendix.startup_benchmark
                  .typical_pilot_strategy
              }
            />
          </div>

          <div>
            <p className="text-forge-2 font-medium text-forge-text">
              Typical first customer
            </p>

            <Claim
              item={
                appendix.startup_benchmark
                  .typical_first_customer
              }
            />
          </div>

          <div>
            <p className="text-forge-2 font-medium text-forge-text">
              Common mistakes
            </p>

            <Claim
              item={
                appendix.startup_benchmark
                  .common_mistakes
              }
            />
          </div>

          <div>
            <p className="text-forge-2 font-medium text-forge-text">
              Growth path
            </p>

            <Claim
              item={
                appendix.startup_benchmark.growth_path
              }
            />
          </div>
        </div>

        {appendix.startup_benchmark
          .retrieved_ventures_used.length > 0 && (
          <div className="mt-6">
            <p className="text-forge-2 font-medium text-forge-text">
              Retrieved similar ventures used
            </p>

            <ul
              role="list"
              className="mt-2 space-y-1 text-forge-2 text-forge-text-secondary"
            >
              {appendix.startup_benchmark.retrieved_ventures_used.map(
                (venture, index) => (
                  <li key={index}>
                    <div className="flex items-start gap-2">
                      <span className="flex-1">
                        {venture.name} (
                        {venture.industry},{" "}
                        similarity{" "}
                        {Number.isFinite(
                          venture.similarity,
                        )
                          ? venture.similarity.toFixed(2)
                          : "0.00"}
                        )
                      </span>

                      
                    </div>
                  </li>
                ),
              )}
            </ul>
          </div>
        )}
      </ReportSection>

      <ReportSection title="Investor Intelligence">
        <div>
          <p className="text-forge-2 font-medium text-forge-text">
            Why similar ventures succeed
          </p>

          <div className="mt-2">
            <ClaimList
              items={
                appendix.investor_intelligence
                  .why_similar_ventures_succeed
              }
            />
          </div>
        </div>

        <div className="mt-6">
          <p className="text-forge-2 font-medium text-forge-text">
            Most important milestones
          </p>

          <div className="mt-2">
            <ClaimList
              items={
                appendix.investor_intelligence
                  .most_important_milestones
              }
            />
          </div>
        </div>
      </ReportSection>

      <ReportSection title="Industry Context">
        <div className="space-y-4">
          <Claim
            item={
              appendix.industry_context
                .typical_customer
            }
          />

          <Claim
            item={
              appendix.industry_context
                .buying_process
            }
          />

          <Claim
            item={
              appendix.industry_context.sales_cycle
            }
          />

          <ClaimList
            items={
              appendix.industry_context
                .common_integrations
            }
          />

          <ClaimList
            items={
              appendix.industry_context.expected_kpis
            }
          />

          <Claim
            item={
              appendix.industry_context
                .procurement_difficulty
            }
          />

          <ClaimList
            items={
              appendix.industry_context
                .enterprise_objections
            }
          />

          <ClaimList
            items={
              appendix.industry_context
                .smb_objections
            }
          />

          <ClaimList
            items={
              appendix.industry_context
                .customer_acquisition_channels
            }
          />

          <Claim
            item={
              appendix.industry_context
                .retention_strategy
            }
          />

          <ClaimList
            items={
              appendix.industry_context.expansion_triggers
            }
          />

          <ClaimList
            items={
              appendix.industry_context
                .enterprise_readiness_checklist
            }
          />

          <Claim
            item={
              appendix.industry_context
                .regulatory_considerations
            }
          />

          <Claim
            item={
              appendix.industry_context
                .technical_stack_expectations
            }
          />

          <Claim
            item={
              appendix.industry_context
                .typical_differentiation
            }
          />

          <ClaimList
            items={
              appendix.industry_context
                .common_feature_roadmap
            }
          />
        </div>
      </ReportSection>

      <ReportSection title="Evidence Supporting Strengths">
        <ClaimList
          items={appendix.evidence_supporting_strengths}
        />
      </ReportSection>

      <ReportSection title="Final Mentor Verdict">
        <Claim
          item={appendix.final_mentor_verdict}
        />
      </ReportSection>

      <div className="flex items-start gap-2">
        <p className="flex-1 text-forge-1 text-forge-text-secondary/80">
          {appendix.knowledge_transparency_note}
        </p>

        
      </div>
    </div>
  );
}

/* =========================================================
   MAIN FOUNDER REPORT
   ========================================================= */

export function FounderReportScene({
  report,
}: {
  report: FounderReport;
}) {
  const sceneTransition = useMotionTier("scene");

  const discoveries = buildDiscoveries(report);

  const weeks =
    report.appendix?.pilot_roadmap?.weeks ?? [];

  const marketLabels = [
    "Pricing",
    "Go-To-Market",
    "First Customer",
    "Competitive Edge",
    "Feature Priority",
  ];

  return (
    <Scene eyebrow="The Founder Report">
      <div className="space-y-16">
        {/* =================================================
            WHAT WE DISCOVERED
            ================================================= */}
        <ReportSection
          title="What We Discovered"
          id="section-discoveries"
        >
          <ul
            role="list"
            className="grid grid-cols-1 gap-4 forge-sm:grid-cols-2"
          >
            {discoveries.map((discovery, index) => (
              <motion.li
                key={discovery.key}
                initial={{
                  opacity: 0,
                  y: 8,
                }}
                whileInView={{
                  opacity: 1,
                  y: 0,
                }}
                viewport={{
                  once: true,
                  margin: "-40px",
                }}
                transition={{
                  ...sceneTransition,
                  delay: Math.min(
                    index * 0.05,
                    0.2,
                  ),
                }}
                className={`h-full ${
                  index === 0
                    ? "forge-sm:col-span-2"
                    : ""
                }`}
              >
                <details className="group flex h-full flex-col rounded-forge-lg border border-forge-text/[.08] bg-forge-surface-1 p-5">
                  <summary className="flex cursor-pointer list-none items-start justify-between gap-4">
                    <div className="flex min-w-0 flex-1 items-start gap-2">
                      <p className="flex-1 text-forge-2 font-medium text-forge-heading">
                        <span
                          aria-hidden="true"
                          className={
                            discovery.kind ===
                            "advantage"
                              ? "text-forge-emerald"
                              : "text-forge-rose"
                          }
                        >
                          {discovery.kind ===
                          "advantage"
                            ? "âœ“ "
                            : "âš  "}
                        </span>

                        {highlightKeywords(
                          discovery.headline,
                        )}
                      </p>

                      
                    </div>

                    <span
                      aria-hidden="true"
                      className="shrink-0 text-forge-2 text-forge-text-tertiary transition-transform group-open:rotate-180"
                    >
                      âŒ„
                    </span>
                  </summary>

                  <div className="mt-4 space-y-3 border-t border-forge-text/[.08] pt-4">
                    {discovery.detail}
                  </div>
                </details>
              </motion.li>
            ))}
          </ul>
        </ReportSection>

        {/* =================================================
            COMPETITIVE POSITION
            ================================================= */}
        <ReportSection
          title="Competitive Position"
          id="section-competitive-position"
        >
          <ol
            role="list"
            className="grid grid-cols-1 gap-4 forge-sm:grid-cols-4"
          >
            {[
              {
                label: "Today",
                item:
                  report.moat_and_competitive_position
                    .what_competitors_can_copy_today,
              },
              {
                label: "10 Customers",
                item:
                  report.moat_and_competitive_position
                    .defensible_after_10_customers,
              },
              {
                label: "100 Customers",
                item:
                  report.moat_and_competitive_position
                    .defensible_after_100_customers,
              },
              {
                label: "1,000 Customers",
                item:
                  report.moat_and_competitive_position
                    .defensible_after_1000_customers,
              },
            ].map((stage) => (
              <li
                key={stage.label}
                className="relative flex h-full flex-col rounded-forge-lg border border-forge-text/[.08] bg-forge-surface-1 p-4"
              >
                <div className="flex items-center gap-2">
                  <p className="text-forge-1 font-medium uppercase tracking-[0.1em] text-forge-gold">
                    {stage.label}
                  </p>

                  
                </div>

                <div className="mt-2">
                  <Claim item={stage.item} />
                </div>
              </li>
            ))}
          </ol>

          <div className="mt-3">
            <Claim
              item={
                report.moat_and_competitive_position
                  .what_they_cannot_copy
              }
            />
          </div>
        </ReportSection>

        {/* =================================================
            NEXT 30 DAYS
            ================================================= */}
        {weeks.length > 0 && (
          <ReportSection
            title="Next 30 Days"
            id="section-next-30-days"
          >
            <ol
              role="list"
              className="grid grid-cols-1 gap-4 forge-sm:grid-cols-4"
            >
              {weeks.map((week) => (
                <li
                  key={week.week}
                  className="flex h-full flex-col rounded-forge-lg border border-forge-text/[.08] bg-forge-surface-1 p-4"
                >
                  <div className="flex items-center gap-2">
                    <p className="text-forge-1 font-medium uppercase tracking-[0.1em] text-forge-gold">
                      Week {week.week}
                    </p>

                    
                  </div>

                  <div className="mt-2 flex items-start gap-2">
                    <p className="flex-1 text-forge-2 font-medium text-forge-heading">
                      {highlightKeywords(week.focus)}
                    </p>

                    
                  </div>

                  <ul
                    role="list"
                    className="mt-2 space-y-1 text-forge-1 text-forge-desc"
                  >
                    {week.activities.map(
                      (activity, index) => (
                        <li key={index}>
                          <div className="flex items-start gap-2">
                            <span className="flex-1">
                              {highlightKeywords(
                                activity,
                              )}
                            </span>

                            
                          </div>
                        </li>
                      ),
                    )}
                  </ul>
                </li>
              ))}
            </ol>
          </ReportSection>
        )}

        {/* =================================================
            MARKET STRATEGY
            ================================================= */}
        {report.market_insight?.length > 0 && (
          <ReportSection
            title="Market Strategy"
            id="section-market-strategy"
          >
            <div className="grid grid-cols-1 gap-4 forge-sm:grid-cols-3">
              {report.market_insight
                .slice(0, 5)
                .map((item, index) => (
                  <details
                    key={index}
                    className="group flex h-full flex-col rounded-forge-lg border border-forge-text/[.08] bg-forge-surface-1 p-4"
                  >
                    <summary className="flex cursor-pointer list-none items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <p className="text-forge-1 font-medium uppercase tracking-[0.1em] text-forge-label">
                          {marketLabels[index] ??
                            "Insight"}
                        </p>

                        
                      </div>

                      <span
                        aria-hidden="true"
                        className="shrink-0 text-forge-2 text-forge-text-tertiary transition-transform group-open:rotate-180"
                      >
                        âŒ„
                      </span>
                    </summary>

                    <div className="mt-3 border-t border-forge-text/[.08] pt-3">
                      <Claim item={item} />
                    </div>
                  </details>
                ))}
            </div>
          </ReportSection>
        )}

        {/* =================================================
            DEEP DIVE
            ================================================= */}
        <details
          id="section-appendix"
          className="scroll-mt-24 border-t border-forge-text/[.08] pt-8"
        >
          <summary className="flex cursor-pointer items-center gap-2 text-forge-1 uppercase tracking-[0.15em] text-forge-text-secondary">
            <span>
              Deep dive â€” evidence, methodology, and the full technical report
            </span>

            
          </summary>

          <div className="mt-6">
            <AppendixContent
              appendix={report.appendix}
            />
          </div>
        </details>
      </div>

      {report.disclaimer && (
        <div className="mt-10 flex items-start gap-2">
          <p className="flex-1 max-w-[62ch] text-forge-1 text-forge-text-secondary/80">
            {report.disclaimer}
          </p>

          
        </div>
      )}
    </Scene>
  );
}


