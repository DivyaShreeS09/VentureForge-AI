import { useState } from "react";
import { Link } from "react-router-dom";
import type { Analysis } from "../../../types/api";
import { Button } from "../../../primitives";
import { Scene } from "../Scene";

/** Scene 8 — Continue Building. Everything operational: re-analyze, export, history, start
 * another venture. Replaces the old sticky CommandBar — moved from persistent chrome into its own
 * final scene, so nothing operational competes with the narrative above it. Export now generates
 * a real presentation-quality PDF (see `utils/generatePdf.ts`) instead of a raw JSON download —
 * dynamically imported on click rather than statically, so `pdf-lib` (a genuinely large library)
 * never loads for the ~99% of Reveal-page visits that don't click Export. */
export function ContinueBuildingScene({
  analysis,
  onReanalyze,
  reanalyzing,
  startupName = null,
}: {
  analysis: Analysis;
  onReanalyze: () => void;
  reanalyzing: boolean;
  startupName?: string | null;
}) {
  const [exporting, setExporting] = useState(false);

  async function handleExport() {
    setExporting(true);
    try {
      const { generateAnalysisPdf } = await import("../../../utils/generatePdf");
      await generateAnalysisPdf(analysis, startupName);
    } finally {
      setExporting(false);
    }
  }

  return (
    <Scene eyebrow="Continue Building">
      <h2 className="max-w-[26ch] text-balance font-forge-serif text-forge-5 font-semibold leading-[1.25] text-forge-text">
        What's next?
      </h2>
      <div className="mt-8 flex flex-wrap gap-3">
        <Button variant="primary" onClick={onReanalyze} disabled={reanalyzing}>
          {reanalyzing ? "Re-analyzing…" : "Re-analyze"}
        </Button>
        <Button variant="secondary" onClick={handleExport} disabled={exporting}>
          {exporting ? "Preparing PDF…" : "Export PDF"}
        </Button>
        <Link to="/history">
          <Button variant="secondary">Your ventures</Button>
        </Link>
        <Link to="/">
          <Button variant="ghost">Start another venture</Button>
        </Link>
      </div>
    </Scene>
  );
}
