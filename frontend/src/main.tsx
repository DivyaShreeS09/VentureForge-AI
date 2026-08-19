import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
<<<<<<< HEAD

// Design System Bible §5 — the three type families, self-hosted (no font-CDN request,
// no flash of an unstyled fallback tied to network latency). Only the weights actually
// used anywhere in the product are imported: Fraunces 600 (the Threshold headline, the
// one display-serif moment this sprint), Hanken Grotesk 400/500 (body copy / button and
// label emphasis — the Bible's reference candidate, "General Sans", isn't published on
// npm/Fontsource; Hanken Grotesk is the closest available humanist grotesk with real
// lowercase character while staying legible at 13px), and JetBrains Mono 500 (tabular
// numerals — not used by any Sprint 3 screen, but reserved now so the type system is
// complete for the numeric scenes later sprints add).
=======
import "./index.css";
import { LanguageProvider } from "./context/LanguageContext";

// Design System Bible §5 — the three type families, self-hosted (no font-CDN request,
// no flash of an unstyled fallback tied to network latency).
>>>>>>> master
import "@fontsource/fraunces/600.css";
import "@fontsource/hanken-grotesk/400.css";
import "@fontsource/hanken-grotesk/500.css";
import "@fontsource/jetbrains-mono/500.css";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
<<<<<<< HEAD
    <App />
=======
    <LanguageProvider>
      <App />
    </LanguageProvider>
>>>>>>> master
  </React.StrictMode>,
);
