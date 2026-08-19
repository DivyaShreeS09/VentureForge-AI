/**
 * Cosmic Command-Center design tokens — the single typed source for every non-Tailwind
 * consumer (e.g. Canvas-rendered elements that can't read Tailwind utility classes).
 * Tailwind's `forge-*` color/shadow keys (tailwind.config.js) resolve through the
 * matching `--forge-*` CSS custom properties (src/index.css), not literal hex — these
 * three sources (this file, the CSS variables, and Tailwind's config) must all match by
 * hand; there is no build step that derives one from the others. The product is
 * intentionally dark-only (one premium cosmic theme, no light variant), so there is
 * exactly one color set below.
 */

export const forgeSpacing = {
  1: 4,
  2: 8,
  3: 12,
  4: 16,
  5: 24,
  6: 32,
  7: 48,
  8: 64,
  9: 96,
} as const;

export const forgeRadius = {
  sm: 6,
  md: 12,
  lg: 20,
} as const;

export const forgeTypeScale = [13, 15, 17, 20, 26, 34, 48, 64, 88] as const;

// Design System Bible §3 — exactly one elevated shadow level, used only by the
// command capsule and dialogs. `elevation-0` (everything else) is simply no shadow.
export const forgeElevation1 = "0 12px 40px -12px rgba(14, 13, 12, 0.45)" as const;

export const forgeColorDark = {
  canvas: "#07060D",
  surface1: "#120B24",
  surface2: "#1B1333",
  surfaceBorder: "rgba(139, 92, 246, 0.22)",
  accent: "#FFB020",
  accentSecondary: "#FF7A1A",
  accentPressed: "#E6672F",
  accentTint16: "rgba(255, 176, 32, 0.16)",
  accent2: "#8B5CF6",
  accent2Tint: "#B39DFF",
  accent2Deep: "#6D28D9",
  accent3: "#63E6E8",
  magentaDecorative: "#E0299B",
  magentaTint: "#FF7AC6",
  text: "#F8F9FC",
  textSecondary: "rgba(248, 249, 252, 0.72)",
  textTertiary: "rgba(248, 249, 252, 0.48)",
  textDisabled: "rgba(248, 249, 252, 0.24)",
  confirmed: "#6FA287",
  notSureYet: "#C9A24A",
  risk: "#E0637A",
  info: "#5B9DFF",
} as const;

export type ForgeSemanticState = "confirmed" | "notSureYet" | "risk";
