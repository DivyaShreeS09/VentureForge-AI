import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { useMotionTier } from "../motion/transitions";

export interface CommandCapsuleSection {
  id: string;
  label: string;
}

// The Command Capsule is the sole persistent nav object, reachable globally via
// ⌘K/Ctrl+K. There must be exactly one instance mounted for the whole app (one keyboard
// listener, one overlay) — rendered once, in RootLayout. `useRegisterCommandSections`
// lets any page register real in-page anchors into this shared context so the palette
// can offer to jump to them and the docked pill can track "you are here" — the Founder
// Report scene (FounderReportScene.tsx) registers its own subsections this way for
// guided in-page jumping.
const SectionsContext = createContext<{
  sections: CommandCapsuleSection[];
  setSections: (sections: CommandCapsuleSection[]) => void;
} | null>(null);

export function CommandCapsuleProvider({ children }: { children: ReactNode }) {
  const [sections, setSections] = useState<CommandCapsuleSection[]>([]);
  const value = useMemo(() => ({ sections, setSections }), [sections]);
  return <SectionsContext.Provider value={value}>{children}</SectionsContext.Provider>;
}

/** Called by a page that wants the docked capsule to show its real, in-view sections.
 * Registers on mount, clears on unmount — so navigating away automatically un-docks the
 * capsule everywhere else. The docked pill itself only ever appears once one of these
 * sections has actually scrolled into view (see the IntersectionObserver in
 * `CommandCapsule` below) — registering early (e.g. on initial mount, before the founder
 * has scrolled anywhere near the section) must never make the pill appear early too. */
export function useRegisterCommandSections(sections: CommandCapsuleSection[]) {
  const ctx = useContext(SectionsContext);
  if (!ctx) throw new Error("useRegisterCommandSections must be used within CommandCapsuleProvider");
  const { setSections } = ctx;
  const key = sections.map((s) => s.id).join("|");

  useEffect(() => {
    setSections(sections);
    return () => setSections([]);
    // `sections` is intentionally represented by `key` here — the caller passes a new
    // array identity on every render, but the registration only needs to change when
    // the actual set of section ids changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, setSections]);
}

interface Command {
  id: string;
  label: string;
  onSelect: () => void;
}

// Justification for a new primitive (Build Contract §1.11): no existing component
// provides jump-navigation or a global command list. Rendered exactly once, in
// RootLayout — see CommandCapsuleProvider's header comment for why.
export function CommandCapsule() {
  const ctx = useContext(SectionsContext);
  if (!ctx) throw new Error("CommandCapsule must be used within CommandCapsuleProvider");
  const { sections } = ctx;

  const navigate = useNavigate();
  const [expanded, setExpanded] = useState(false);
  const [highlighted, setHighlighted] = useState(0);
  const [currentSectionId, setCurrentSectionId] = useState<string | null>(null);
  // The IntersectionObserver below reports a section as "in view" for its *entire* height, not
  // just its heading — so a tall first section (e.g. the Reveal's Command Center, which spans
  // well past one viewport) counts as "in view" from the very first paint, before the founder has
  // scrolled at all. Confirmed live: that made this fixed, bottom-center pill sit directly on top
  // of that section's own body text at scroll position zero. Gating on a real scroll distance as
  // well — not just the observer — guarantees the pill only ever appears once the page has
  // actually moved, when there's a genuine "you are here" to report.
  const [hasScrolled, setHasScrolled] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);
  const transition = useMotionTier("scene");

  const jumpTo = useCallback((id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const commands = useMemo<Command[]>(
    () => [
      ...sections.map((s) => ({ id: s.id, label: s.label, onSelect: () => jumpTo(s.id) })),
      { id: "cmd-new", label: "Start a new analysis", onSelect: () => navigate("/") },
      { id: "cmd-history", label: "Open a previous venture", onSelect: () => navigate("/history") },
    ],
    [sections, jumpTo, navigate],
  );

  // Tracks which real section is currently in view, so the docked pill always shows a
  // true "you are here" — never a static or fabricated label. Deliberately does NOT
  // default to `sections[0]` on registration: a page (the Reveal) can register its
  // sections the moment it mounts, long before the founder has scrolled anywhere near
  // them — defaulting to "in view" made this fixed, bottom-center pill appear
  // immediately and sit on top of unrelated, much-earlier content (confirmed via a real
  // screenshot: it overlapped the Verdict scene's headline). The pill now only ever
  // appears once the IntersectionObserver has genuinely confirmed a registered section
  // is on screen.
  useEffect(() => {
    if (sections.length === 0) {
      setCurrentSectionId(null);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]) setCurrentSectionId(visible[0].target.id);
      },
      { rootMargin: "-20% 0px -70% 0px" },
    );
    for (const section of sections) {
      const el = document.getElementById(section.id);
      if (el) observer.observe(el);
    }
    return () => {
      observer.disconnect();
      setCurrentSectionId(null);
    };
  }, [sections]);

  useEffect(() => {
    function onScroll() {
      setHasScrolled(window.scrollY > 80);
    }
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setExpanded((v) => !v);
        setHighlighted(0);
      } else if (e.key === "Escape" && expanded) {
        setExpanded(false);
      }
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [expanded]);

  function onListKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlighted((i) => Math.min(i + 1, commands.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlighted((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      commands[highlighted]?.onSelect();
      setExpanded(false);
    }
  }

  const currentLabel = sections.find((s) => s.id === currentSectionId)?.label;

  return (
    <>
      {currentSectionId && !expanded && hasScrolled && (
        <button
          type="button"
          onClick={() => {
            setExpanded(true);
            setHighlighted(0);
          }}
          className="fixed bottom-6 left-1/2 z-40 -translate-x-1/2 rounded-forge-md border border-forge-text/[.16] bg-forge-surface-2 px-4 py-2 text-forge-2 text-forge-text shadow-forge-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-forge-accent"
        >
          {currentLabel ?? "Jump to…"}
        </button>
      )}

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={transition}
            className="fixed inset-0 z-50 flex items-start justify-center bg-forge-canvas/[.48] pt-32"
            onClick={() => setExpanded(false)}
          >
            <motion.div
              ref={listRef}
              role="listbox"
              aria-label="Jump to a section"
              tabIndex={-1}
              // A command palette must capture keyboard input the instant it opens, or
              // arrow/Enter navigation silently does nothing — this is the one
              // documented, deliberate exception to the no-autofocus rule.
              // eslint-disable-next-line jsx-a11y/no-autofocus
              autoFocus
              onKeyDown={onListKeyDown}
              onClick={(e) => e.stopPropagation()}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.98 }}
              transition={transition}
              className="w-full max-w-md rounded-forge-lg border border-forge-text/[.16] bg-forge-surface-2 p-2 shadow-forge-1"
            >
              {commands.map((command, i) => (
                <div
                  key={command.id}
                  role="option"
                  aria-selected={i === highlighted}
                  // Not part of the tab order (tabIndex={-1}) — this is a composite
                  // listbox where the container (above) owns keyboard focus and moves
                  // `highlighted` via arrow keys/Enter; each option's own onKeyDown
                  // exists only to satisfy the same activation via a direct Enter/Space
                  // press if focus is ever moved here programmatically, and to keep
                  // click and keyboard activation logic in exactly one place.
                  tabIndex={-1}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      command.onSelect();
                      setExpanded(false);
                    }
                  }}
                  onMouseEnter={() => setHighlighted(i)}
                  onClick={() => {
                    command.onSelect();
                    setExpanded(false);
                  }}
                  className={`cursor-pointer rounded-forge-sm px-3 py-2 text-forge-3 ${
                    i === highlighted ? "bg-forge-accent/[.16] text-forge-text" : "text-forge-text-secondary"
                  }`}
                >
                  {command.label}
                </div>
              ))}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
