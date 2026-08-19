import type { ReactNode } from "react";

interface Props {
  eyebrow: string;
  summary: string;
  children: ReactNode;
}

/** Shared shell for Scene 6 (Bigger Picture) and Scene 7 (Deep Evidence) — both collapsed by
 * default per the Bible ("progressive disclosure only"), using the native `<details>` element so
 * expand/collapse is free, keyboard-accessible, and needs no motion tier of its own. */
export function CollapsedScene({ eyebrow, summary, children }: Props) {
  return (
    <section className="mx-auto w-full max-w-[860px] px-6 py-12 forge-sm:px-10">
      <details className="group">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-4 border-t border-forge-text/[.08] py-5">
          <span>
            <span className="block text-forge-1 uppercase tracking-[0.25em] text-forge-label">{eyebrow}</span>
            <span className="mt-1 block text-forge-3 font-semibold text-forge-heading [text-shadow:0_0_20px_rgba(139,92,246,0.18)]">{summary}</span>
          </span>
          <span aria-hidden="true" className="shrink-0 text-forge-text-secondary transition group-open:rotate-45">
            +
          </span>
        </summary>
        <div className="pb-6 pt-2">{children}</div>
      </details>
    </section>
  );
}
