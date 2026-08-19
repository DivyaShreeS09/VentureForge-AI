import { useEffect, useState } from "react";
import type { Analysis } from "../../types/api";
import { correctIndustry, getTaxonomy } from "../../services/api";

const TAXONOMY_FETCH_FALLBACK_DOMAINS = ["Enterprise AI", "General Consumer App"];

function useTaxonomy() {
  const [domains, setDomains] = useState<string[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    getTaxonomy()
      .then((res) => {
        if (cancelled) return;
        setDomains(res.domains.map((d) => d.id));
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Could not load the positioning taxonomy.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { domains, loading, error };
}

/** Lets a founder correct `venture_positioning.primary_domain` from the controlled taxonomy —
 * moved unchanged from the old AnalysisResult.tsx, restyled with forge tokens only. Real
 * functionality (not presentation), so it's kept — see Sprint 7 audit: KEEP. */
export function PositioningCorrection({
  analysisId,
  currentPrimaryDomain,
  onCorrected,
}: {
  analysisId: string;
  currentPrimaryDomain: string;
  onCorrected: (updated: Analysis) => void;
}) {
  const [selected, setSelected] = useState(currentPrimaryDomain);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { domains, loading: taxonomyLoading, error: taxonomyError } = useTaxonomy();

  async function handleSubmit() {
    if (selected === currentPrimaryDomain) return;
    setSubmitting(true);
    setError(null);
    try {
      const updated = await correctIndustry(analysisId, { primary_domain: selected });
      onCorrected(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not apply this correction.");
    } finally {
      setSubmitting(false);
    }
  }

  if (taxonomyLoading) {
    return <p className="mt-4 text-forge-1 text-forge-text-secondary">Loading available positioning domains…</p>;
  }

  const domainOptions = domains ?? TAXONOMY_FETCH_FALLBACK_DOMAINS;

  return (
    <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-forge-text/[.08] pt-4">
      <label className="text-forge-1 text-forge-text-secondary" htmlFor="positioning-correction-select">
        Not the right industry?
      </label>
      <select
        id="positioning-correction-select"
        value={selected}
        onChange={(e) => setSelected(e.target.value)}
        className="rounded-forge-sm border border-forge-text/[.16] bg-transparent px-2 py-1 text-forge-2 text-forge-text"
      >
        {domainOptions.map((domain) => (
          <option key={domain} value={domain}>
            {domain}
          </option>
        ))}
      </select>
      <button
        type="button"
        onClick={handleSubmit}
        disabled={submitting || selected === currentPrimaryDomain}
        className="rounded-forge-sm border border-forge-accent/50 px-3 py-1 text-forge-1 font-medium text-forge-accent transition hover:bg-forge-accent/10 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {submitting ? "Applying…" : "Correct industry"}
      </button>
      {taxonomyError && (
        <p role="alert" className="w-full text-forge-1 text-forge-notsure">
          Could not load the full taxonomy from the server ({taxonomyError}) — showing a minimal fallback list only.
        </p>
      )}
      {error && (
        <p role="alert" className="w-full text-forge-1 text-forge-risk">
          {error}
        </p>
      )}
    </div>
  );
}
