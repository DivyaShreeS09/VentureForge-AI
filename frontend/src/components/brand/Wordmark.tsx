import { Link } from "react-router-dom";
import emblem from "../../assets/ventureforge-emblem.webp";
import lockup from "../../assets/ventureforge-lockup.webp";

interface Props {
  /** "hero" is the large entrance mark on the venture-entry screen (the official emblem+wordmark
   * lockup image); "compact" is the small top-bar mark used everywhere else (emblem image + a
   * CSS text wordmark, since the source lockup's metallic type is illegible shrunk to nav size).
   * Two sizes, not a prop-driven pile of one-off variants. */
  size?: "hero" | "compact";
  className?: string;
  /** Only the entrance screen plays the reveal/ignite animation — repeating it on every route
   * change would turn a meaningful moment into a tic. */
  animate?: boolean;
}

/** The one place the official VentureForgeAI logo asset is rendered — every screen uses the same
 * source image so the product reads as one system, not several disconnected pages. */
export function Wordmark({ size = "compact", className = "", animate = false }: Props) {
  if (size === "hero") {
    return (
      <Link to="/" className={`inline-block ${className}`}>
        <img
          src={lockup}
          alt="VentureForge AI"
          className={`w-full max-w-[270px] drop-shadow-[0_0_50px_rgba(124,44,255,0.35)] sm:max-w-[300px] ${
            animate ? "animate-reveal" : ""
          }`}
        />
      </Link>
    );
  }

  return (
    <Link to="/" className={`inline-flex items-center gap-2.5 ${className}`}>
      <img src={emblem} alt="" aria-hidden="true" className="h-8 w-auto drop-shadow-[0_0_10px_rgba(124,44,255,0.4)]" />
      <span className="text-display text-lg text-ink-primary">
        Venture<span className="text-gold-400">Forge</span> <span className="text-ink-secondary">AI</span>
      </span>
    </Link>
  );
}
