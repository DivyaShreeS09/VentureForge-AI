import { motion } from "framer-motion";
import { GlassCard } from "../../primitives/GlassCard";
import type { MentorInterpretation, Student3RankedAction } from "../../types/api";
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

function buildMissions(mentor: MentorInterpretation, rankedActions: Student3RankedAction[]): Mission[] {
  if (mentor.founder_report) {
    return mentor.founder_report.founder_strategy.slice(0, 3).map((m) => ({
      id: `insight-mission-${m.priority}`,
      title: m.action.content,
      why: m.reason.content,
      difficulty: m.difficulty,
      timeline: m.estimated_duration,
      definitionOfDone: m.definition_of_done.content,
    }));
  }
  // No founder_report — fall back to the same real First-Week/First-Month buckets
  // `FirstThirtyDaysScene` used to render as a flat list. Only fields that genuinely exist on a
  // `RoadmapTask` are shown (no difficulty/timeline fabricated when the source doesn't carry one).
  const { firstWeek, firstMonth } = buildRoadmapBuckets(mentor, rankedActions);
  return [...firstWeek, ...firstMonth].slice(0, 3).map((task, i) => ({
    id: `mission-fallback-${i}`,
    title: task.task,
    why: task.outcome,
    difficulty: task.effort,
  }));
}

function Row({ label, value }: { label: string; value?: string }) {
  if (!value) return null;
  return (
    <div className="border-t border-forge-text/[.08] pt-3 first:border-t-0 first:pt-0">
      <p className="text-forge-1 uppercase tracking-[0.1em] text-forge-helper">{label}</p>
      <p className="mt-1 text-forge-2 text-forge-desc">{highlightKeywords(value)}</p>
    </div>
  );
}

/** Section 3 of 5 — answers exactly one question: "What should I do next?" Exactly three
 * missions, never a backlog — each one why / difficulty / timeline / definition of done, nothing
 * more. Sourced from `founder_report.founder_strategy` when present (the richest real source),
 * falling back to the same validation-plan buckets the old `FirstThirtyDaysScene` used — never a
 * fabricated task. */
export function MissionControl({
  mentor,
  rankedActions,
}: {
  mentor: MentorInterpretation;
  rankedActions: Student3RankedAction[];
}) {
  const missions = buildMissions(mentor, rankedActions);
  const stagger = useMotionTier("scene");

  return (
    <section id="section-mission-control" className="mx-auto w-full max-w-[1100px] px-6 py-16 forge-sm:px-10">
      <p className="text-forge-1 uppercase tracking-[0.2em] text-forge-label">Mission Control</p>
      <h2 className="mt-3 max-w-[26ch] text-balance font-forge-serif text-forge-5 font-bold leading-[1.25] text-forge-heading [text-shadow:0_0_24px_rgba(139,92,246,0.2)]">
        Three missions. Nothing else.
      </h2>

      <motion.div
        initial="hidden"
        animate="show"
        variants={{ hidden: {}, show: { transition: { staggerChildren: 0.08 } } }}
        className="mt-8 grid grid-cols-1 gap-4 forge-sm:grid-cols-3"
      >
        {missions.map((mission, i) => (
          <motion.div
            key={mission.id}
            id={mission.id}
            variants={{ hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0, transition: stagger } }}
            className="scroll-mt-24"
          >
            <GlassCard interactive glow="accent-2" className="h-full p-5">
              <p className="text-forge-1 font-medium uppercase tracking-[0.1em] text-forge-label">Mission {i + 1}</p>
              <p className="mt-2 text-forge-3 font-medium text-forge-heading">{highlightKeywords(mission.title)}</p>
              <div className="mt-4 space-y-3">
                <Row label="Why" value={mission.why} />
                <Row label="Difficulty" value={mission.difficulty} />
                <Row label="Timeline" value={mission.timeline} />
                <Row label="Definition of done" value={mission.definitionOfDone} />
              </div>
            </GlassCard>
          </motion.div>
        ))}
      </motion.div>
    </section>
  );
}
