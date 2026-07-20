import type { MentorInterpretation, Student3RankedAction } from "../../../types/api";
import type { RoadmapTask } from "../../../utils/founderDecision";
import { buildRoadmapBuckets } from "../../../utils/founderDecision";
import { Section } from "../Section";

function TaskCard({ task }: { task: RoadmapTask }) {
  return (
    <li className="rounded-xl border border-white/10 bg-white/[0.02] p-4">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-ink-primary">{task.task}</p>
        <span className="shrink-0 rounded-full border border-white/10 bg-white/[0.03] px-2 py-0.5 text-[10px] uppercase tracking-[0.08em] text-ink-muted">
          Priority {task.priority}
        </span>
      </div>
      <dl className="mt-2 space-y-1 text-xs text-ink-secondary">
        <div>
          <dt className="inline text-ink-muted">Estimated effort: </dt>
          <dd className="inline">{task.effort}</dd>
        </div>
        <div>
          <dt className="inline text-ink-muted">Expected outcome: </dt>
          <dd className="inline">{task.outcome}</dd>
        </div>
        <div>
          <dt className="inline text-ink-muted">Dependencies: </dt>
          <dd className="inline">{task.dependencies}</dd>
        </div>
      </dl>
    </li>
  );
}

function TaskColumn({ heading, tasks }: { heading: string; tasks: RoadmapTask[] }) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-[0.1em] text-ink-muted">{heading}</h3>
      {tasks.length > 0 ? (
        <ul className="mt-2 space-y-2.5">
          {tasks.map((task, idx) => (
            <TaskCard key={`${task.task}-${idx}`} task={task} />
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-xs text-ink-muted">Nothing scheduled for this window yet.</p>
      )}
    </div>
  );
}

/** Section 4 — 90-Day Founder Roadmap: the existing validation_plan + roadmap_30_60_90 (both
 * already computed deterministically) regrouped into First Week / First Month / Next 90 Days,
 * each task carrying priority, estimated effort, expected outcome, and dependencies. */
export function RoadmapSection({ mentor, rankedActions = [] }: { mentor: MentorInterpretation; rankedActions?: Student3RankedAction[] }) {
  const { firstWeek, firstMonth, next90Days } = buildRoadmapBuckets(mentor, rankedActions);

  return (
    <Section id="roadmap" title="90-Day Founder Roadmap">
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <TaskColumn heading="First Week" tasks={firstWeek} />
        <TaskColumn heading="First Month" tasks={firstMonth} />
        <TaskColumn heading="Next 90 Days" tasks={next90Days} />
      </div>
    </Section>
  );
}
