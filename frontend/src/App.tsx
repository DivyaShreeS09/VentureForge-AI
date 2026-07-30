import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes, useLocation } from "react-router-dom";
import { RootLayout } from "./app/RootLayout";
import { BareLayout } from "./app/BareLayout";
import { DiscoveryLayout } from "./app/DiscoveryLayout";
import { RouteLoadingFallback } from "./app/RouteLoadingFallback";
import { RootErrorBoundary } from "./app/RootErrorBoundary";
import { SceneTransition } from "./motion/SceneTransition";
import { useTransitionTier } from "./motion/act";
import { ThresholdPage } from "./pages/ThresholdPage";

// Route-level code splitting: ThresholdPage (the landing page every visitor hits first) stays in
// the main bundle; every other page — especially AnalysisResultPage, which pulls in all 8 Reveal
// scene components — loads only once the founder actually navigates there.
const IdeaSubmissionPage = lazy(() => import("./pages/IdeaSubmissionPage").then((m) => ({ default: m.IdeaSubmissionPage })));
const EvidenceCollectionPage = lazy(() => import("./pages/EvidenceCollectionPage").then((m) => ({ default: m.EvidenceCollectionPage })));
const AnalysisStatusPage = lazy(() => import("./pages/AnalysisStatusPage").then((m) => ({ default: m.AnalysisStatusPage })));
const AnalysisResultPage = lazy(() => import("./pages/AnalysisResultPage").then((m) => ({ default: m.AnalysisResultPage })));
const HistoryPage = lazy(() => import("./pages/HistoryPage").then((m) => ({ default: m.HistoryPage })));

// Sprint 2 — application shell and navigation foundation. Each route is wrapped in
// the layout matching its Act's nav philosophy (Design System Bible §2): no chrome
// for Act I (Threshold) and Act III during Forging (BareLayout, shared — see its own
// header comment for why one component covers both); the progress filament +
// confirm-before-exit wordmark for Act II (Discovery); the Command Capsule for Acts
// IV-V (Reveal). No page's own content changes this sprint — only what wraps it.
//
// The one SceneTransition instance lives here, above every layout and wrapping
// <Routes> itself (rather than one per layout) — see SceneTransition's header comment
// for why that's required for the exit animation to actually run across a layout
// boundary. useTransitionTier compares the previous and next route's Act to pick
// `scene` vs `threshold` per Design System Bible §8.
function AppRoutes() {
  const location = useLocation();
  const tier = useTransitionTier(location.pathname);

  return (
    <Suspense fallback={<RouteLoadingFallback />}>
      <SceneTransition transitionKey={location.pathname} tier={tier}>
        <Routes location={location}>
          <Route
            path="/"
            element={
              <BareLayout>
                <ThresholdPage />
              </BareLayout>
            }
          />
          <Route
            path="/new/idea"
            element={
              <DiscoveryLayout>
                <IdeaSubmissionPage />
              </DiscoveryLayout>
            }
          />
          <Route
            path="/new/evidence"
            element={
              <DiscoveryLayout>
                <EvidenceCollectionPage />
              </DiscoveryLayout>
            }
          />
          <Route
            path="/startups/:startupId/status"
            element={
              <BareLayout>
                <AnalysisStatusPage />
              </BareLayout>
            }
          />
          <Route
            path="/analyses/:analysisId"
            element={
              <BareLayout>
                <AnalysisResultPage />
              </BareLayout>
            }
          />
          <Route
            path="/history"
            element={
              <BareLayout>
                <HistoryPage />
              </BareLayout>
            }
          />
        </Routes>
      </SceneTransition>
    </Suspense>
  );
}

function App() {
  return (
    <RootErrorBoundary>
      <BrowserRouter>
        <RootLayout>
          <AppRoutes />
        </RootLayout>
      </BrowserRouter>
    </RootErrorBoundary>
  );
}

export default App;
