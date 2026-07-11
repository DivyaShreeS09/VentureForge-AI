import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AmbientBackground } from "./components/layout/AmbientBackground";
import { SystemStatusGate } from "./components/status/SystemStatusOverlay";
import { AnalysisResultPage } from "./pages/AnalysisResultPage";
import { AnalysisStatusPage } from "./pages/AnalysisStatusPage";
import { HomePage } from "./pages/HomePage";

function App() {
  return (
    <BrowserRouter>
      <AmbientBackground />
      <SystemStatusGate>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/startups/:startupId/status" element={<AnalysisStatusPage />} />
          <Route path="/analyses/:analysisId" element={<AnalysisResultPage />} />
        </Routes>
      </SystemStatusGate>
    </BrowserRouter>
  );
}

export default App;
