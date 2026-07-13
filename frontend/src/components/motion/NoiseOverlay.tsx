/** A near-imperceptible film-grain texture over the hero — breaks up flat gradient banding
 * without reading as "static," since it's a single low-opacity SVG turbulence layer, not an
 * animated overlay. Reserved for the Home hero, not applied globally. */
export function NoiseOverlay() {
  return (
    <svg
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 h-full w-full opacity-[0.025] mix-blend-overlay"
    >
      <filter id="vf-noise">
        <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" stitchTiles="stitch" />
      </filter>
      <rect width="100%" height="100%" filter="url(#vf-noise)" />
    </svg>
  );
}
