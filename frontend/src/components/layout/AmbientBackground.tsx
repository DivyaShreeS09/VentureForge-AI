import reportBackground from "../../assets/report-background.jpg";
import { StarField } from "./StarField";

/** The one cosmic backdrop for every screen except the Threshold (which paints its own full-bleed
 * `landing-background.jpg` hero directly, see ThresholdPage.tsx). Mounted once, globally, by
 * RootLayout — `report-background.jpg` behind a readability overlay strong enough for sustained
 * dense reading (Reveal, the questionnaire, History), plus the same drifting/twinkling `StarField`
 * used on the Threshold, so the whole app reads as one continuous space rather than a hero page
 * bolted onto plain dashboard screens.
 *
 * Purely visual — carries no state and reacts to nothing. `aria-hidden` and `pointer-events-none`
 * keep it invisible to assistive tech and unable to intercept clicks. */
export function AmbientBackground() {
  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      {/* `bg-fixed` so the artwork reads as one continuous backdrop rather than repeating/
          scrolling per-section as a page scrolls — confirmed live that `position:fixed` keeps it
          visible in the viewport at every scroll depth, not just at the top. */}
      <div
        className="absolute inset-0 bg-fixed bg-cover bg-center opacity-70 blur-[1px]"
        style={{ backgroundImage: `url(${reportBackground})` }}
      />
      {/* The readability layer: sustained dense reading can never fight the artwork for contrast,
          so this overlay is deliberately heavy, plus a vignette that darkens the edges most, where
          floating chrome (dock, command capsule) tends to sit. */}
      <div className="absolute inset-0 bg-forge-canvas/60" />
      <div className="absolute inset-0 [background:radial-gradient(ellipse_110%_80%_at_50%_35%,transparent_0%,rgba(7,6,13,0.75)_65%,rgba(7,6,13,0.96)_100%)]" />
      <StarField density="quiet" />
    </div>
  );
}
