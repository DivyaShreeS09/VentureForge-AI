import { useState } from "react";
import { NavLink } from "react-router-dom";
import { Wordmark } from "../brand/Wordmark";
import { AboutModelModal } from "./AboutModelModal";
import { SidebarStatusWidget } from "./SidebarStatusWidget";

const REPO_URL = "https://github.com/DivyaShreeS09/VentureForge-AI#readme";

function NavIcon({ path }: { path: string }) {
  return (
    <svg viewBox="0 0 24 24" className="h-4.5 w-4.5" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden="true">
      <path d={path} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const ICONS = {
  new: "M12 4v16m8-8H4",
  history: "M3 12a9 9 0 1 0 3-6.7M3 5v5h5",
  info: "M12 16v-4m0-4h.01M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z",
  docs: "M7 4h10a1 1 0 0 1 1 1v15l-6-3-6 3V5a1 1 0 0 1 1-1Z",
};

const navItemClasses = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium transition ${
    isActive
      ? "border border-signal-500/30 bg-signal-500/10 text-ink-primary shadow-glow"
      : "text-ink-secondary hover:bg-white/5 hover:text-ink-primary"
  }`;

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
 * which would otherwise eat most of a 390px viewport. */
export function Sidebar({ mobileOpen = false, onNavigate }: Props) {
  const [aboutOpen, setAboutOpen] = useState(false);

  return (
    <aside
      className={`fixed inset-y-0 left-0 z-40 flex h-full w-64 shrink-0 flex-col gap-6 border-r border-white/10 bg-void-950/95 p-5 pt-16 backdrop-blur-sm transition-transform duration-300 lg:static lg:translate-x-0 lg:bg-void-950/60 lg:pt-5 ${
        mobileOpen ? "translate-x-0" : "-translate-x-full"
      }`}
      onClick={onNavigate}
    >
      <div>
        <Wordmark />
        <p className="mt-2 pl-0.5 text-[11px] leading-snug text-ink-muted">
          Forge ideas. Build impact. Shape futures.
        </p>
      </div>

      <nav className="flex flex-1 flex-col gap-1.5">
        <NavLink to="/" end className={navItemClasses}>
          <NavIcon path={ICONS.new} />
          New Analysis
        </NavLink>
        <NavLink to="/history" className={navItemClasses}>
          <NavIcon path={ICONS.history} />
          History
        </NavLink>
        <button
          type="button"
          onClick={() => setAboutOpen(true)}
          className="flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-left text-sm font-medium text-ink-secondary transition hover:bg-white/5 hover:text-ink-primary"
        >
          <NavIcon path={ICONS.info} />
          About Model
        </button>
        <a
          href={REPO_URL}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-medium text-ink-secondary transition hover:bg-white/5 hover:text-ink-primary"
        >
          <NavIcon path={ICONS.docs} />
          Documentation
        </a>
      </nav>

      <SidebarStatusWidget />
      <AboutModelModal open={aboutOpen} onClose={() => setAboutOpen(false)} />
    </aside>
  );
}
