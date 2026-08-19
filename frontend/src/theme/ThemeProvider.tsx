import { useEffect, type ReactNode } from "react";

/** The product is intentionally dark-only — a single, premium cosmic theme, not a
 * light/dark toggle. This component's only remaining job is to make sure the
 * `color-scheme`/`data-theme` the rest of the app (and any OS chrome, like native form
 * control rendering) expects is set once, deterministically, regardless of the visitor's
 * OS preference. There is no stored preference and no toggle — removing that surface
 * entirely rather than leaving a dead "light" branch around. */
export function ThemeProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", "dark");
  }, []);

  return <>{children}</>;
}
