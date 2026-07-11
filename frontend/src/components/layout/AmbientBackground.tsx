import { ParticleField } from "./ParticleField";

/** Fixed, decorative-only ambient layer: a few slow-drifting glow orbs plus a sparse, unconnected
 * particle field behind all content — the app should feel quietly alive everywhere, while the
 * denser *connected* particle network (see VentureIntroPanel) stays reserved for the hero zone.
 *
 * Purely visual — carries no state and reacts to nothing. `aria-hidden` and `pointer-events-none`
 * keep it invisible to assistive tech and unable to intercept clicks. The global
 * `prefers-reduced-motion` rule in index.css freezes the drift/pulse animations for users who
 * request it; ParticleField itself also checks that media query directly for its own canvas loop.
 */
export function AmbientBackground() {
  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="absolute -left-32 -top-32 h-[36rem] w-[36rem] animate-drift rounded-full bg-signal-600/10 blur-[120px]" />
      <div className="absolute -right-24 top-1/3 h-[28rem] w-[28rem] animate-drift rounded-full bg-current-500/10 blur-[110px] [animation-delay:-3s]" />
      <div className="absolute bottom-[-10rem] left-1/3 h-[24rem] w-[24rem] animate-pulse-slow rounded-full bg-gold-500/5 blur-[100px]" />
      <ParticleField />
    </div>
  );
}
