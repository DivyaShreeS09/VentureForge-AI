import { motion } from "framer-motion";
import { GlassCard } from "../../primitives/GlassCard";
import type {
  MentorInterpretation,
  Student3RankedAction,
} from "../../types/api";
import { buildRoadmapBuckets } from "../../utils/founderDecision";
import { useMotionTier } from "../../motion/transitions";
import { highlightKeywords } from "../../utils/highlightKeywords";
interface Mission {
  id: string;
  title: string;
  why?: string;
  difficulty?: string;
  timeline?: string;
  definitionOfDone?: string;
}

function buildMissions(
  mentor: MentorInterpretation,
  rankedActions: Student3RankedAction[],
): Mission[] {
  if (mentor.founder_report) {
    return mentor.founder_report.founder_strategy
      .slice(0, 3)
      .map((m) => ({
        id: `insight-mission-${m.priority}`,
        title: m.action.content,
        why: m.reason.content,
        difficulty: m.difficulty,
        timeline: m.estimated_duration,
        definitionOfDone: m.definition_of_done.content,
      }));
  }

  const { firstWeek, firstMonth } = buildRoadmapBuckets(
    mentor,
    rankedActions,
  );

  return [...firstWeek, ...firstMonth]
    .slice(0, 3)
    .map((task, i) => ({
      id: `mission-fallback-${i}`,
      title: task.task,
      why: task.outcome,
      difficulty: task.effort,
    }));
}


function Row({
  label,
  value,
}: {
  label: string;
  value?: string;
}) {
  if (!value?.trim()) return null;

  return (
    <div className="border-t border-forge-text/[.08] pt-3 first:border-t-0 first:pt-0">
      <div className="flex items-center gap-2">
        <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-helper">
          {label}
        </p>

        
      </div>

      <div className="mt-1 flex items-start gap-2">
        <p className="flex-1 text-forge-2 text-forge-desc">
          {highlightKeywords(value)}
        </p>

        
      </div>
    </div>
  );
}

/**
 * Section 3 of 5 â€” answers:
 * "What should I do next?"
 *
 * Mission content remains completely dynamic.
 * The speaker reads whatever mission text the analysis actually returns.
 */
export function MissionControl({
  mentor,
  rankedActions,
}: {
  mentor: MentorInterpretation;
  rankedActions: Student3RankedAction[];
}) {
  const missions = buildMissions(mentor, rankedActions);
  const stagger = useMotionTier("scene");

  const sectionTitle = "Mission Control";
  const sectionQuestion = "Three missions. Nothing else.";

  return (
    <section
      id="section-mission-control"
      className="mx-auto w-full max-w-[1100px] px-6 py-16 forge-sm:px-10"
    >
      <div className="flex items-center gap-2">
        <p className="text-forge-1 uppercase tracking-[0.2em] text-forge-label">
          {sectionTitle}
        </p>

        
      </div>

      <div className="mt-3 flex items-start gap-3">
        <h2 className="flex-1 max-w-[26ch] text-balance font-forge-serif text-forge-5 font-bold leading-[1.25] text-forge-heading [text-shadow:0_0_24px_rgba(139,92,246,0.2)]">
          {sectionQuestion}
        </h2>

        
      </div>

      <motion.div
        initial="hidden"
        animate="show"
        variants={{
          hidden: {},
          show: {
            transition: {
              staggerChildren: 0.08,
            },
          },
        }}
        className="mt-8 grid grid-cols-1 gap-4 forge-sm:grid-cols-3"
      >
        {missions.map((mission, i) => {
          const missionHeading = `Mission ${i + 1}`;

          return (
            <motion.div
              key={mission.id}
              id={mission.id}
              variants={{
                hidden: { opacity: 0, y: 10 },
                show: {
                  opacity: 1,
                  y: 0,
                  transition: stagger,
                },
              }}
              className="scroll-mt-24"
            >
              <GlassCard
                interactive
                glow="accent-2"
                className="h-full p-5"
              >
                <div className="flex items-center gap-2">
                  <p className="text-forge-1 font-medium uppercase tracking-[0.1em] text-forge-label">
                    {missionHeading}
                  </p>

                  
                </div>

                <div className="mt-2 flex items-start gap-2">
                  <p className="flex-1 text-forge-3 font-medium text-forge-heading">
                    {highlightKeywords(mission.title)}
                  </p>

                  
                </div>

                <div className="mt-4 space-y-3">
                  <Row
                    label="Why"
                    value={mission.why}
                  />

                  <Row
                    label="Difficulty"
                    value={mission.difficulty}
                  />

                  <Row
                    label="Timeline"
                    value={mission.timeline}
                  />

                  <Row
                    label="Definition of done"
                    value={mission.definitionOfDone}
                  />
                </div>
              </GlassCard>
            </motion.div>
          );
        })}
      </motion.div>
    </section>
  );
}


