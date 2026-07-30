import type { ReactNode } from "react";
import { useLocation } from "react-router-dom";
import { AmbientBackground } from "../components/layout/AmbientBackground";
import { SystemStatusGate } from "../components/status/SystemStatusOverlay";
import { NewAnalysisProvider } from "../context/NewAnalysisContext";
import { ThemeProvider } from "../theme/ThemeProvider";
import { CommandCapsule, CommandCapsuleProvider } from "../primitives/CommandCapsule";
import { DockActionsProvider } from "../primitives/DockActions";
import { Dock } from "../primitives/Dock";

/** Replaces AppShell: no persistent sidebar, no per-route chrome duplicated everywhere.
 * Composes the app-wide concerns that genuinely are global (theme, the health-check
 * gate, the autosaved draft context, the one global command surface, the ambient cosmic
 * backdrop) and nothing else — per-Act navigation (progress filament, command capsule
 * docking) is each Act's own layout's responsibility, not this one's.
 *
 * The cosmic `<AmbientBackground />` (report-background.jpg + drifting stars) is global and the
 * same everywhere — every screen except the Threshold, which paints its own full-bleed
 * `landing-background.jpg` hero directly (see ThresholdPage.tsx) and doesn't need this layer at
 * all. The app should read as one continuous space, not a hero page bolted onto separate plain
 * dashboard screens.
 *
 * The floating `<Dock />` is global except on the Threshold itself: that page now has its own
 * top-right History/About/Get Started nav (matching the reference artwork's chrome), so a
 * second History/About affordance floating bottom-left would just be a duplicate control. */
export function RootLayout({ children }: { children: ReactNode }) {
  const location = useLocation();
  const isThreshold = location.pathname === "/";

  return (
    <ThemeProvider>
      <SystemStatusGate>
        <NewAnalysisProvider>
          <CommandCapsuleProvider>
            <DockActionsProvider>
              {!isThreshold && <AmbientBackground />}
              <a
                href="#forge-main"
                className="fixed left-4 top-4 z-50 -translate-y-16 rounded-forge-sm bg-forge-accent px-4 py-2 text-[#0B0710] focus:translate-y-0"
              >
                Skip to content
              </a>
              <div id="forge-main">{children}</div>
              <CommandCapsule />
              {!isThreshold && <Dock />}
            </DockActionsProvider>
          </CommandCapsuleProvider>
        </NewAnalysisProvider>
      </SystemStatusGate>
    </ThemeProvider>
  );
}
