/** The small "Autosaved locally" line shown at the bottom of every Discovery Act page — was
 * duplicated verbatim in `IdeaSubmissionPage.tsx` and `EvidenceCollectionPage.tsx`; extracted here
 * so the two copies can't drift out of sync. */
export function AutosavedIndicator() {
  return (
    <p className="mt-6 flex items-center gap-1.5 text-forge-1 text-forge-text-tertiary">
      <span aria-hidden="true" className="h-1.5 w-1.5 rounded-full bg-forge-confirmed" />
      Autosaved locally
    </p>
  );
}
