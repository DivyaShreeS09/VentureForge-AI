import { Link } from "react-router-dom";

interface Props {
  /** "hero" is the large entrance mark on the venture-entry screen; "compact" is the small
   * top-bar mark used everywhere else. Two sizes, not a prop-driven pile of one-off variants. */
  size?: "hero" | "compact";
  className?: string;
  /** Design System Bible §2 — in the Discovery Act, clicking the wordmark must open a
   * confirm-before-exit dialog rather than navigate immediately (autosaved draft, but
   * still a deliberate "leave for now?" moment). When provided, this intercepts the
   * click (`preventDefault`) instead of the default immediate `Link to="/"` — every
   * other usage is unaffected. */
  onClick?: (e: React.MouseEvent) => void;
}

/** The one place the VentureForge identity mark is set — every screen renders the same
 * typographic lockup so the product reads as one system, not several disconnected pages.
 *
 * Stays deliberately typographic, not an illustrated glyph — a faceted multi-hue "VF" emblem was
 * tried previously and read as a generated game/crypto mark, exactly the "hackathon AI" signal a
 * first impression can't afford. Confident typography *is* the mark: "Venture" in a metallic
 * silver sheen, "Forge" in the amber-to-orange energy gradient, at hero size only — the compact
 * top-bar mark stays flat-color for legibility/perf.
 *
 * The Threshold's headline ("Is this idea worth building?"), not this mark, remains the one
 * visual focal point of that screen (Hero Moment Requirement) — this mark gets a premium, very
 * subtle breathing glow rather than growing to compete with it.
 *
 * "Forge" reads in the electric-purple brand accent (`forge-accent-2`) rather than amber/orange —
 * purple is the brand identity per the logo; orange/gold stays reserved for CTAs, warnings, and
 * energy moments (the small dot below keeps a single gold accent touch, not the whole word). */
export function Wordmark({ size = "compact", className = "", onClick }: Props) {
  function handleClick(e: React.MouseEvent) {
    if (onClick) {
      e.preventDefault();
      onClick(e);
    }
  }

  const isHero = size === "hero";

  return (
    <Link
      to="/"
      onClick={handleClick}
      className={`group inline-flex items-baseline gap-[0.07em] whitespace-nowrap font-forge-sans font-semibold leading-none tracking-tight ${
        isHero
          ? "animate-breathe text-forge-4 forge-sm:text-forge-5"
          : "text-forge-2 text-forge-text"
      } ${className}`}
    >
      <span className={isHero ? "bg-gradient-to-b from-white via-forge-text to-forge-text-secondary bg-clip-text text-transparent" : "text-forge-text"}>
        Venture
      </span>
      <span
        className={`relative mr-[0.22em] ${
          isHero
            ? "bg-gradient-to-r from-forge-accent-2-tint to-forge-accent-2 bg-clip-text text-transparent"
            : "text-forge-accent-2"
        }`}
      >
        Forge
        <span
          aria-hidden="true"
          className="absolute -right-[0.2em] bottom-[0.14em] h-[0.11em] w-[0.11em] rounded-full bg-forge-accent transition-transform duration-300 group-hover:scale-125"
        />
      </span>
      <span className="font-medium text-forge-text-tertiary">AI</span>
    </Link>
  );
}
