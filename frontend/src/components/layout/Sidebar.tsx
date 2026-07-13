import { useState } from "react";
import { NavLink } from "react-router-dom";
import { Wordmark } from "../brand/Wordmark";
import { AboutModelModal } from "./AboutModelModal";
import { SidebarStatusWidget } from "./SidebarStatusWidget";

const REPO_URL = "https://github.com/DivyaShreeS09/VentureForge-AI#readme";

function NavIcon({ path }: { path: string }) {
  return (
    <span className="relative flex h-5 w-5 shrink-0 items-center justify-center">
      <span
        className="absolute inset-0 scale-50 rounded-full bg-signal-500/0 opacity-0 blur-md transition-all duration-300 group-hover:scale-150 group-hover:bg-signal-500/40 group-hover:opacity-100"
        aria-hidden="true"
      />
      <svg
        viewBox="0 0 24 24"
        className="relative h-4.5 w-4.5 transition-transform duration-300 group-hover:rotate-12"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        aria-hidden="true"
      >
        <path d={path} strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    </span>
  );
}

const ICONS = {
  new: "M12 4v16m8-8H4",
  history: "M3 12a9 9 0 1 0 3-6.7M3 5v5h5",
  info: "M12 16v-4m0-4h.01M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
  docs: "M7 4h10a1 1 0 0 1 1 1v15l-6-3-6 3V5a1 1 0 0 1 1-1Z",
};

const navItemClasses = ({ isActive }: { isActive: boolean }) =>
  `group flex items-center gap-3.5 rounded-xl px-4 py-3 text-[15px] font-medium tracking-wide transition-all duration-300 hover:-translate-y-0.5 ${
    isActive
      ? "border border-signal-500/30 bg-signal-500/10 text-ink-primary shadow-glow"
      : "text-ink-secondary hover:bg-signal-500/[0.07] hover:text-ink-primary"
  }`;

const secondaryItemClasses =
  "group flex items-center gap-3.5 rounded-xl px-4 py-3 text-left text-[15px] font-medium tracking-wide text-ink-secondary " +
  "transition-all duration-300 hover:-translate-y-0.5 hover:bg-signal-500/[0.07] hover:text-ink-primary";

interface Props {
  /** Mobile-only: whether the off-canvas drawer is open. Ignored at the `lg` breakpoint and
   * above, where the sidebar is always visible and static (see AppShell). */
  mobileOpen?: boolean;
  onNavigate?: () => void;
}

/** Persistent left navigation shell, present on every page — matches the reference's panel 01.
 * "About Model" and "Documentation" surface real information (live model metadata, the actual
 * repo README) rather than fabricated pages, per the "no invented pages/features" constraint.
 * Below `lg`, this becomes an off-canvas drawer (see AppShell) rather than a fixed 256px column,
 * which would otherwise eat most of a 390px viewport.
 *
 * At `lg` and above this is `sticky` + `h-screen` rather than relying on flex stretch (`h-full`):
 * the row container's height is driven by page content, which on some routes exceeds one
 * viewport, so a percentage height on this item resolves against an indeterminate parent height
 * and silently collapses to its own content size instead of the full viewport. `h-screen` sidesteps
 * that entirely — it's a real diagnosed bug fix, not a style preference. */
export function Sidebar({ mobileOpen = false, onNavigate }: Props) {
  const [aboutOpen, setAboutOpen] = useState(false);

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-40 flex h-full w-72 shrink-0 flex-col gap-8 border-r border-white/10 bg-void-950/95 p-6 pt-16 backdrop-blur-sm transition-transform duration-300 lg:sticky lg:top-0 lg:h-screen lg:w-[clamp(270px,20vw,292px)] lg:translate-x-0 lg:bg-void-950/60 lg:pt-6 ${
        mobileOpen ? "translate-x-0" : "-translate-x-full"
      }`}
      onClick={onNavigate}
    >
      <div>
        <Wordmark />
        <p className="mt-2.5 pl-0.5 text-xs leading-relaxed tracking-wide text-ink-muted">
          Forge ideas. Build impact. Shape futures.
        </p>
      </div>

      <nav className="flex flex-1 flex-col gap-2">
        <NavLink to="/" end className={navItemClasses}>
          <NavIcon path={ICONS.new} />
          New Analysis
        </NavLink>
        <NavLink to="/history" className={navItemClasses}>
          <NavIcon path={ICONS.history} />
          History
        </NavLink>
        <button type="button" onClick={() => setAboutOpen(true)} className={secondaryItemClasses}>
          <NavIcon path={ICONS.info} />
          About Model
        </button>
        <a href={REPO_URL} target="_blank" rel="noreferrer" className={secondaryItemClasses}>
          <NavIcon path={ICONS.docs} />
          Documentation
        </a>
      </nav>

      <SidebarStatusWidget />
      <AboutModelModal open={aboutOpen} onClose={() => setAboutOpen(false)} />
    </aside>
  );
}
