import type { MentorInterpretation, Student3RankedAction } from "../../../types/api";
import { buildRoadmapBuckets } from "../../../utils/founderDecision";
import { Scene } from "../Scene";

/** Scene 5 — The First 30 Days. A founder leaves knowing exactly what to do tomorrow: specific,
 * ordered, actionable — not a generic checklist. Combines the existing First-Week/First-Month
 * buckets (buildRoadmapBuckets, unchanged logic) into one ordered list; the 90-day view lives in
 * the Bigger Picture scene instead, since only the near-term plan needs to be immediate. */
export function FirstThirtyDaysScene({
  mentor,
  rankedActions,
}: {
  mentor: MentorInterpretation;
  rankedActions: Student3RankedAction[];
}) {
  const { firstWeek, firstMonth } = buildRoadmapBuckets(mentor, rankedActions);
  const tasks = [...firstWeek, ...firstMonth];

  return (
    <Scene eyebrow="The First 30 Days">
      <h2 className="max-w-[26ch] text-balance font-forge-serif text-forge-5 font-semibold leading-[1.25] text-forge-text">
        Here's exactly what to do next.
      </h2>

      {/* eslint-disable-next-line jsx-a11y/no-redundant-roles */}
      <ol role="list" className="mt-8 space-y-6">
        {tasks.map((task, idx) => (
          // eslint-disable-next-line jsx-a11y/no-redundant-roles
          <li key={`${task.task}-${idx}`} role="listitem" className="border-t border-forge-text/[.08] pt-5">
            <div className="flex items-baseline gap-3">
              <span className="font-forge-mono text-forge-1 text-forge-text-secondary">{String(idx + 1).padStart(2, "0")}</span>
              <p className="text-forge-3 text-forge-text">{task.task}</p>
            </div>
            <p className="mt-1.5 pl-8 text-forge-2 text-forge-text-secondary">{task.outcome}</p>
            <p className="mt-1 pl-8 text-forge-1 text-forge-text-secondary">{task.effort}</p>
          </li>
        ))}
      </ol>
    </Scene>
  );
}
