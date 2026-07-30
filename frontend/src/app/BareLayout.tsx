import type { ReactNode } from "react";

// Design System Bible §2 nav philosophy — Act I (Threshold) and Act III during
// Forging both specify "no navigation at all." Rather than create two components with
// identical bodies (Build Contract §1.11: no duplicate just to have a differently-
// named file per Act), both routes share this one bare layout. Route transitions are
// handled once, above every layout — see SceneTransition's header comment for why a
// per-layout AnimatePresence can't work — so this component renders no chrome at all.
export function BareLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
