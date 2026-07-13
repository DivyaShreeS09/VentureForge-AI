import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AmbientBackground } from "./components/layout/AmbientBackground";
import { AppShell } from "./components/layout/AppShell";
import { SystemStatusGate } from "./components/status/SystemStatusOverlay";
import { NewAnalysisProvider } from "./context/NewAnalysisContext";
import { AnalysisResultPage } from "./pages/AnalysisResultPage";
import { AnalysisStatusPage } from "./pages/AnalysisStatusPage";
import { EvidenceCollectionPage } from "./pages/EvidenceCollectionPage";
import { HistoryPage } from "./pages/HistoryPage";
import { HomePage } from "./pages/HomePage";
import { IdeaSubmissionPage } from "./pages/IdeaSubmissionPage";

function App() {
  return (
    <BrowserRouter>
      <AmbientBackground />
      <SystemStatusGate>
        <NewAnalysisProvider>
          <AppShell>
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/new/idea" element={<IdeaSubmissionPage />} />
              <Route path="/new/evidence" element={<EvidenceCollectionPage />} />
              <Route path="/startups/:startupId/status" element={<AnalysisStatusPage />} />
              <Route path="/analyses/:analysisId" element={<AnalysisResultPage />} />
              <Route path="/history" element={<HistoryPage />} />
            </Routes>
          </AppShell>
        </NewAnalysisProvider>
      </SystemStatusGate>
    </BrowserRouter>
  );
}

export default App;
