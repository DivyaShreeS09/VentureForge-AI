/** P0 fix — the Reveal route's chunk (Reveal.tsx + all 8 scene components) can take multiple
 * seconds to fetch on a real network the first time a founder's analysis completes and this app
 * auto-navigates there (confirmed via a throttled-network Playwright repro: the content area went
 * fully blank for 1.7s+ while `App.tsx`'s `<Suspense fallback={null}>` rendered nothing). This
 * component is deliberately NOT lazy-loaded and has zero dependencies beyond React/Tailwind so it
 * is always present in the main bundle and paints instantly, regardless of how slow the next
 * route's own chunk is to arrive. `bg-forge-canvas` matches every real page's own background —
 * critical because the global `<body>` background (src/index.css) is an unmigrated legacy dark/
 * gradient look; without an opaque, matching fallback here, that legacy background would flash
 * through for the same duration instead of a true blank, which reads as even more broken. */
export function RouteLoadingFallback() {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex min-h-[100dvh] w-full items-center justify-center bg-forge-canvas font-forge-sans"
    >
      <div className="flex items-center gap-3">
        <span className="h-2 w-2 animate-pulse rounded-full bg-forge-accent" aria-hidden="true" />
        <span className="text-forge-2 text-forge-text-secondary">Loading…</span>
      </div>
    </div>
  );
}
