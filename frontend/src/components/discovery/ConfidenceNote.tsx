import { Chip } from "../../primitives";
import type { IndustryPreview } from "../../types/api";

interface Props {
  preview: IndustryPreview | null;
  loading: boolean;
  error: string | null;
}

// The classifier's raw labels ("b2b", "consumer") are lowercase internal class names, not
// display copy — the existing Analysis Result page renders them via a plain CSS `capitalize`
// (first-letter-per-word), which reads fine for most labels but turns "b2b"/"b2c" into "B2b"/
// "B2c". Fixed only for those two known acronym forms (not a general display-name dictionary —
// there's no full, certain label list to hand-author one from, since the trained artifact may be
// either the real or the bootstrap taxonomy, per tests/test_predictor.py's own docstring); every
// other label still falls back to the exact same capitalize-first-letter behavior already shipped
// on the Analysis Result page, so nothing here can drift out of sync with an unknown label.
const KNOWN_ACRONYMS: Record<string, string> = { b2b: "B2B", b2c: "B2C" };

export function formatIndustryLabel(label: string): string {
  const lower = label.toLowerCase();
  if (KNOWN_ACRONYMS[lower]) return KNOWN_ACRONYMS[lower];
  return label.replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Design System Bible §11/§13 — reuses the existing semantic Chip (confirmed/not-sure-yet)
 * rather than a fabricated progress bar or percentage. Every state here maps directly to a real
 * backend signal: `loading`/`error` are transport states, and the confirmed/not-sure-yet split is
 * exactly `IndustryPreview.is_uncertain` — never a synthesized confidence score. */
export function ConfidenceNote({ preview, loading, error }: Props) {
  // A real previous read stays visible while a newer one is in flight (e.g. the founder just
  // added a name) — "still confirmed" is more honest and less confusing than replacing an
  // already-real answer with "checking…" every time an unrelated field changes.
  if (loading && !preview) {
    return <p className="text-forge-2 text-forge-text-tertiary">Reading what you've written…</p>;
  }

  if (error && !preview) {
    return (
      <p role="status" className="text-forge-2 text-forge-text-tertiary">
        {error} You can still continue.
      </p>
    );
  }

  if (!preview || !preview.available) return null;

  const industry = preview.predicted_industry ? formatIndustryLabel(preview.predicted_industry) : null;

  if (preview.is_uncertain) {
    return (
      <Chip state="notSureYet" label={industry ? `Might be ${industry} — not fully sure yet` : "Not fully sure yet"} />
    );
  }

  return <Chip state="confirmed" label={`Looks like ${industry}`} />;
}
