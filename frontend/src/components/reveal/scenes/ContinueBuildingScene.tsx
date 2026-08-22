import { useState } from "react";
import { Link } from "react-router-dom";
import type { Analysis } from "../../../types/api";
import { Button } from "../../../primitives";
import { Scene } from "../Scene";

/** Final operational scene. */
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
      const { generateAnalysisPdf } = await import(
        "../../../utils/generatePdf"
      );

      await generateAnalysisPdf(
        analysis,
        startupName,
      );
    } finally {
      setExporting(false);
    }
  }

  const nextTitle = "What's next?";

  const reanalyzeText = reanalyzing
    ? "Re-analyzing"
    : "Re-analyze";

  const exportText = exporting
    ? "Preparing PDF"
    : "Export PDF";

  const venturesText = "Your ventures";
  const anotherVentureText = "Start another venture";

  return (
    <Scene eyebrow="Continue Building">
      <div className="flex items-start gap-3">
        <h2 className="max-w-[26ch] flex-1 text-balance font-forge-serif text-forge-5 font-semibold leading-[1.25] text-forge-text">
          {nextTitle}
        </h2>

        
      </div>

      <div className="mt-8 flex flex-wrap gap-3">
        <div className="flex items-center gap-2">
          <Button
            variant="primary"
            onClick={onReanalyze}
            disabled={reanalyzing}
          >
            {reanalyzing
              ? "Re-analyzingâ€¦"
              : "Re-analyze"}
          </Button>

          
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            onClick={handleExport}
            disabled={exporting}
          >
            {exporting
              ? "Preparing PDFâ€¦"
              : "Export PDF"}
          </Button>

          
        </div>

        <div className="flex items-center gap-2">
          <Link to="/history">
            <Button variant="secondary">
              Your ventures
            </Button>
          </Link>

          
        </div>

        <div className="flex items-center gap-2">
          <Link to="/">
            <Button variant="ghost">
              Start another venture
            </Button>
          </Link>

          
        </div>
      </div>
    </Scene>
  );
}


