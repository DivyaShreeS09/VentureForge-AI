import type { ReactNode } from "react";

const SOURCE_LABEL: Record<string, string> = {
  input: "User Input",
  model: "ML Prediction",
  deterministic: "Deterministic Assessment",
  judge: "Judge Synthesis",
  ai: "Optional AI Narrative",
};

export type DataSource = keyof typeof SOURCE_LABEL;

interface Props {
  id: string;
  title: string;
  /** Every results section must disclose where its content actually comes from — a plain,
   * reusable wrapper is what lets every section carry this consistently. */
  source?: DataSource;
  children: ReactNode;
}

export function Section({ id, title, source, children }: Props) {
  return (
    <section aria-labelledby={`${id}-heading`} className="panel p-6 sm:p-8">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 id={`${id}-heading`} className="text-display text-xl text-ink-primary">
          {title}
        </h2>
        {source && (
          <span className="rounded-full border border-white/10 bg-white/[0.03] px-2.5 py-0.5 text-[11px] uppercase tracking-[0.1em] text-ink-muted">
            {SOURCE_LABEL[source]}
          </span>
        )}
      </div>
      <div className="mt-5">{children}</div>
    </section>
  );
}
