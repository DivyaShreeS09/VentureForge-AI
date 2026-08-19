import { Component, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

/** P0 fix — this codebase had NO error boundary anywhere. Confirmed via a real, instrumented
 * reproduction: a data-shape mismatch (a stale backend process serving an older
 * `founder_report` shape than the frontend expected) threw inside `FounderReportScene` with no
 * boundary to catch it, and React's default behavior — unmounting the entire tree — left the
 * founder staring at a permanently blank page with no way to recover, not even a refresh prompt.
 * This is the structural fix for THAT class of bug: whatever throws during render, in this
 * component or any future one, the founder always sees a real message and a way forward instead
 * of silence. It does not replace fixing the actual cause of any given crash — it's the backstop
 * for when one still gets through. */
export class RootErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: { componentStack: string }) {
    // eslint-disable-next-line no-console
    console.error("VentureForge AI crashed while rendering:", error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <main className="flex min-h-[100dvh] w-full flex-col items-center justify-center gap-4 bg-forge-canvas px-6 text-center font-forge-sans">
          <p className="font-forge-serif text-forge-5 font-medium text-forge-text">Something went wrong on this screen.</p>
          <p className="max-w-md text-forge-2 text-forge-text-secondary">
            Your analysis itself is safe — this is just a display error. Reloading the page will get you back to it.
          </p>
          <button
            onClick={() => window.location.reload()}
            className="mt-2 rounded-forge-md border border-forge-text/[.16] px-4 py-2 text-forge-2 font-medium text-forge-text transition-colors hover:border-forge-accent/50"
          >
            Reload
          </button>
        </main>
      );
    }
    return this.props.children;
  }
}
