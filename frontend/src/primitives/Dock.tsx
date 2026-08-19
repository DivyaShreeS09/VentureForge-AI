import { useState } from "react";
import { Link } from "react-router-dom";
import { AboutModelModal } from "../components/layout/AboutModelModal";
import { MagneticButton } from "../components/motion/MagneticButton";
import { useDockAction } from "./DockActions";

const ICON_CLASS =
  "relative flex h-11 w-11 items-center justify-center rounded-full text-forge-2 text-forge-text-secondary " +
  "transition-colors hover:text-forge-text focus-visible:outline focus-visible:outline-2 " +
  "focus-visible:outline-offset-2 focus-visible:outline-forge-accent-2";

/** The one persistent floating action dock — replaces the old single "?" `GlobalCorner` button.
 * Bottom-left, glass shell (reusing `GlassCard`'s blur/border tokens directly rather than
 * wrapping `GlassCard` itself, since a `motion.div` inside another interferes with the dock's own
 * layout), purple edge glow, every icon the same size, each with the same magnetic-lean hover
 * `MagneticButton.tsx` already established elsewhere (not a new interaction mechanism). Contents:
 * "?" (About modal), History (a real, visible link — was `sr-only` before), and — only when the
 * Reveal page has registered one via `useRegisterDockAction` — Export PDF. No Settings entry:
 * confirmed no such route exists in this app.
 *
 * `bottom-24` / `forge-sm:bottom-4` reuses the exact safe-area breakpoint the previous
 * `GlobalCorner` fix established for the mobile Idea/Evidence "Back" button overlap — re-verified
 * live at 390px that this still holds with up to 3 icons instead of 1.
 *
 * `<AboutModelModal>` is deliberately rendered as a *sibling* of the dock's own div, not a child
 * of it: the dock has `backdrop-blur-md` (a `backdrop-filter`), and per spec any element with a
 * `filter`/`backdrop-filter` becomes a new containing block for `position: fixed` descendants.
 * Nesting the modal's own full-viewport `fixed inset-0` overlay inside the dock collapsed that
 * overlay down to the dock's own ~100px pill instead of the viewport — confirmed live via
 * `getBoundingClientRect`. Rendering it alongside the dock (both direct children of the same
 * fragment) keeps the overlay anchored to the real viewport. */
export function Dock() {
  const [aboutOpen, setAboutOpen] = useState(false);
  const dockAction = useDockAction();

  return (
    <>
      <div className="fixed bottom-24 left-4 z-40 flex items-center gap-1 rounded-full border border-forge-surface-border bg-forge-surface-1/70 p-1.5 shadow-glow-forge-accent-2 backdrop-blur-md forge-sm:bottom-4">
        <MagneticButton onClick={() => setAboutOpen(true)} aria-label="About the model and documentation" className={ICON_CLASS}>
          {/* An SVG glyph, not a raw "?" character — a font's question-mark glyph has its own visual
              weight/bearing that rarely sits dead-center inside a perfectly circular button; a
              drawn path centers exactly regardless of typeface. */}
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.75" aria-hidden="true">
            <circle cx="12" cy="12" r="9" />
            <path d="M9.5 9.5a2.5 2.5 0 1 1 3.5 2.3c-.7.35-1 .75-1 1.7" strokeLinecap="round" strokeLinejoin="round" />
            <circle cx="12" cy="17" r="0.9" fill="currentColor" stroke="none" />
          </svg>
        </MagneticButton>

        <Link to="/history" aria-label="Your venture history" className={ICON_CLASS}>
          <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true">
            <path d="M3 12a9 9 0 1 0 3-6.7M3 4v5h5" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M12 8v4l3 2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </Link>

        {dockAction && (
          <MagneticButton onClick={dockAction.onClick} aria-label={dockAction.label} className={ICON_CLASS}>
            {dockAction.icon}
          </MagneticButton>
        )}
      </div>
      <AboutModelModal open={aboutOpen} onClose={() => setAboutOpen(false)} />
    </>
  );
}
