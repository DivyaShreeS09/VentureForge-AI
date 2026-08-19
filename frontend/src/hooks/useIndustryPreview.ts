import { useEffect, useRef, useState } from "react";
import { previewIndustry } from "../services/api";
import type { IndustryPreview } from "../types/api";

// Product Bible screenplay ("INT. THE OPENING LINE"): "Two seconds after they stop typing, a
// small word crystallizes in the far periphery" — the live preview call fires this long after
// the founder stops typing, never on every keystroke, so it never competes with typing for
// re-renders and never spams the backend.
const DEBOUNCE_MS = 2000;

// Matches app.agents.nodes.MIN_DESCRIPTION_LENGTH / the backend's own gate — calling before this
// would only ever get back `available: false`, so it's skipped client-side entirely.
const MIN_DESCRIPTION_LENGTH = 10;

interface IndustryPreviewState {
  preview: IndustryPreview | null;
  loading: boolean;
  /** Only set for a genuine transport/backend failure — the honest "available: false" response
   * (untrained classifier, too little text) is not an error and never lands here. */
  error: string | null;
}

/** Live, debounced Discovery preview (Product Bible Act II, "The Opening Line"/"Who It's For").
 * Never fabricates a result: while waiting it reports `loading`, and if the backend genuinely
 * can't be reached it reports `error` — the caller decides how to render both, but neither state
 * ever synthesizes a fake industry/confidence value. */
export function useIndustryPreview(name: string, description: string): IndustryPreviewState {
  const [state, setState] = useState<IndustryPreviewState>({ preview: null, loading: false, error: null });
  const requestId = useRef(0);

  useEffect(() => {
    const trimmed = description.trim();
    if (trimmed.length < MIN_DESCRIPTION_LENGTH) {
      requestId.current += 1; // invalidate any in-flight call
      setState({ preview: null, loading: false, error: null });
      return;
    }

    const thisRequest = ++requestId.current;
    setState((prev) => ({ ...prev, loading: true, error: null }));

    const timer = window.setTimeout(async () => {
      try {
        const preview = await previewIndustry(name, trimmed);
        if (requestId.current === thisRequest) setState({ preview, loading: false, error: null });
      } catch {
        if (requestId.current === thisRequest) {
          setState({
            preview: null,
            loading: false,
            error: "Couldn't reach the server to check this yet.",
          });
        }
      }
    }, DEBOUNCE_MS);

    return () => window.clearTimeout(timer);
  }, [name, description]);

  return state;
}
