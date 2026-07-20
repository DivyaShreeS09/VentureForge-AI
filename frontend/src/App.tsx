import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AmbientBackground } from "./components/layout/AmbientBackground";
import { AppShell } from "./components/layout/AppShell";
import { SystemStatusGate } from "./components/status/SystemStatusOverlay";
import { NewAnalysisProvider } from "./context/NewAnalysisContext";
import { HomePage } from "./pages/HomePage";

// Route-level code splitting: HomePage (the landing page every visitor hits first) stays in the
// main bundle; every other page — especially AnalysisResultPage, which pulls in all 9 Founder
// Decision Studio section components — loads only once the founder actually navigates there.
const IdeaSubmissionPage = lazy(() => import("./pages/IdeaSubmissionPage").then((m) => ({ default: m.IdeaSubmissionPage })));
const EvidenceCollectionPage = lazy(() => import("./pages/EvidenceCollectionPage").then((m) => ({ default: m.EvidenceCollectionPage })));
const AnalysisStatusPage = lazy(() => import("./pages/AnalysisStatusPage").then((m) => ({ default: m.AnalysisStatusPage })));
const AnalysisResultPage = lazy(() => import("./pages/AnalysisResultPage").then((m) => ({ default: m.AnalysisResultPage })));
const HistoryPage = lazy(() => import("./pages/HistoryPage").then((m) => ({ default: m.HistoryPage })));

function App() {
  return (
    <BrowserRouter>
      <AmbientBackground />
      <SystemStatusGate>
        <NewAnalysisProvider>
          <AppShell>
            <Suspense fallback={null}>
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/new/idea" element={<IdeaSubmissionPage />} />
                <Route path="/new/evidence" element={<EvidenceCollectionPage />} />
                <Route path="/startups/:startupId/status" element={<AnalysisStatusPage />} />
                <Route path="/analyses/:analysisId" element={<AnalysisResultPage />} />
                <Route path="/history" element={<HistoryPage />} />
              </Routes>
            </Suspense>
          </AppShell>
        </NewAnalysisProvider>
      </SystemStatusGate>
    </BrowserRouter>
  );
}

export default App;
