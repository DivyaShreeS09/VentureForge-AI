import type { ReactNode } from "react";
import { Wordmark } from "../brand/Wordmark";

/** Minimal top strip used on the Forge sequence page. The Results page uses its own richer
 * CommandBar instead (identity + startup meta + actions) — this one stays deliberately quiet so it
 * doesn't compete with the Forge Core, the visual centerpiece of that screen. */
export function TopBar({ right }: { right?: ReactNode }) {
  return (
    <header className="flex items-center justify-between px-6 py-5 sm:px-10">
      <Wordmark />
      {right}
    </header>
  );
}
