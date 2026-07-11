import type { ReactNode } from "react";

/** The right-side venture input workspace on the entry screen. Deliberately styled as a control
 * surface (header strip + status dot + luminous border) rather than a plain centered form card. */
export function VentureEntryPanel({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-full items-center justify-center px-6 py-16 sm:px-10 lg:px-12 xl:px-16">
      <div className="panel panel-glow w-full max-w-xl p-6 sm:p-10">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-signal-400 shadow-glow-sm" aria-hidden="true" />
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-ink-muted">
            Venture Entry Console
          </p>
        </div>
        <h2 className="mt-3 text-display text-2xl">Describe the venture.</h2>
        <p className="mt-2 text-sm text-ink-muted">
          Every field below feeds a real backend workflow — nothing here is precomputed.
        </p>
        <div className="mt-8">{children}</div>
      </div>
    </div>
  );
}
