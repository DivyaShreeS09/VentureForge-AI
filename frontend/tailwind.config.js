/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      screens: {
        // Design System Bible §10 / Implementation Master Plan §8 breakpoints,
        // namespaced (`forge-*`) rather than overriding Tailwind's default `sm/md/
        // lg/xl` — redefining those keys directly would silently reflow every
        // still-untouched existing page's responsive layout (Sidebar/AppShell used
        // the default `lg: 1024px` split, and studio result sections use `sm`/`md`
        // throughout). New (`forge-*`-styled) components opt into these explicitly;
        // nothing existing is affected.
        "forge-sm": "768px",
        "forge-md": "1024px",
        "forge-lg": "1440px",
        "forge-xl": "1920px",
      },
      colors: {
        // Official brand palette, derived directly from the finalized VentureForgeAI logo.
        // Background black / deep surface / elevated surface.
        void: {
          950: "#030308",
          900: "#090910",
          800: "#11111a",
          700: "#181823",
          600: "#212132",
        },
        // Royal violet — intelligence and creation. Primary accent.
        signal: {
          300: "#c9a8ff",
          400: "#a445ff",
          500: "#7c2cff",
          600: "#5b1fbf",
          700: "#3f0d8a",
        },
        // Electric blue / cyan — analytics and precision. Secondary accent.
        current: {
          300: "#7ddcff",
          400: "#20c7ff",
          500: "#168bff",
          600: "#0f63c2",
        },
        // Molten gold — achievement, impact, readiness. Reserved for high-value moments only.
        gold: {
          300: "#ffe29b",
          400: "#ffd166",
          500: "#ff9d1c",
          600: "#8a4a00",
        },
        // Kept as an alias so existing "readiness-*" usages (the funding gauge) keep working.
        readiness: {
          400: "#ffd166",
          500: "#ff9d1c",
        },
        success: {
          400: "#4fdda3",
          500: "#23d18b",
        },
        warning: {
          400: "#f7c56a",
          500: "#f5b942",
        },
        danger: {
          400: "#ff7c89",
          500: "#ff5a6b",
        },
        // Text scale — primary white / secondary / muted, per the official brand system.
        ink: {
          primary: "#f5f7ff",
          secondary: "#aeb5c8",
          muted: "#70788d",
        },

        // ---------------------------------------------------------------------------
        // Design System Bible §3–§6 palette (namespaced `forge-*`). Added alongside the
        // block above rather than replacing it — existing pages (Sidebar, AppShell,
        // AnalysisResult, etc.) still consume `void`/`signal`/`current`/`gold`/`ink`
        // until each is migrated per the Implementation Master Plan's sprint sequence.
        //
        // Every value below resolves through a CSS custom property (src/index.css),
        // not a literal hex — Tailwind normally bakes utility classes to literal
        // color values at build time, which would make `data-theme="light"` a no-op
        // for anything styled with `bg-forge-canvas` etc. Routing through `var(...)`
        // is what makes the same utility class actually theme-reactive (Sprint 2:
        // Theme integration). The CSS variables themselves (both dark default and the
        // `[data-theme="light"]` override) live in src/index.css and must match
        // src/tokens/forge.ts's raw values exactly (kept in sync by hand).
        // ---------------------------------------------------------------------------
        "forge-canvas": "var(--forge-canvas)",
        "forge-surface-1": "var(--forge-surface-1)",
        "forge-surface-2": "var(--forge-surface-2)",
        "forge-surface-border": "var(--forge-surface-border)",
        "forge-accent": {
          DEFAULT: "var(--forge-accent)",
          secondary: "var(--forge-accent-secondary)",
          pressed: "var(--forge-accent-pressed)",
        },
        // Electric Purple — the structural/glass/glow accent (borders, ambient background,
        // ForgeCore glow). `-tint` is the AA-text-safe version; `-deep` (Royal Violet) is
        // decorative/gradient-only — it fails AA contrast as text, confirmed via the
        // relative-luminance formula (2.84:1 on canvas).
        "forge-accent-2": {
          DEFAULT: "var(--forge-accent-2)",
          tint: "var(--forge-accent-2-tint)",
          deep: "var(--forge-accent-2-deep)",
        },
        // Soft Cyan — rare tertiary highlight only.
        "forge-accent-3": "var(--forge-accent-3)",
        // Neon Magenta — ambient/particle decoration only, never UI text/semantic color.
        "forge-magenta": {
          decorative: "var(--forge-magenta-decorative)",
          tint: "var(--forge-magenta-tint)",
        },
        "forge-text": {
          DEFAULT: "var(--forge-text)",
          secondary: "var(--forge-text-secondary)",
          tertiary: "var(--forge-text-tertiary)",
          disabled: "var(--forge-text-disabled)",
        },
        "forge-confirmed": "var(--forge-confirmed)",
        "forge-notsure": "var(--forge-notsure)",
        "forge-risk": "var(--forge-risk)",
        "forge-info": "var(--forge-info)",
        "forge-heading": "var(--forge-heading)",
        "forge-label": "var(--forge-label)",
        "forge-gold": "var(--forge-gold)",
        "forge-emerald": "var(--forge-emerald)",
        "forge-rose": "var(--forge-rose)",
        "forge-cyan": "var(--forge-cyan)",
        "forge-desc": "var(--forge-desc)",
        "forge-helper": "var(--forge-helper)",
      },
      borderRadius: {
        // Design System Bible §3 — exactly three values, nothing else is ever used on
        // new (`forge-*`-styled) components.
        "forge-sm": "6px",
        "forge-md": "12px",
        "forge-lg": "20px",
      },
      fontSize: {
        // Design System Bible §5 — the nine-step type scale, used exclusively by new
        // components; existing pages keep their current ad hoc sizing until migrated.
        "forge-1": "13px",
        "forge-2": "15px",
        "forge-3": "17px",
        "forge-4": "20px",
        "forge-5": "26px",
        "forge-6": "34px",
        "forge-7": "48px",
        "forge-8": "64px",
        "forge-9": "88px",
      },
      fontFamily: {
        // Design System Bible §5 — the frozen three-family type system, namespaced
        // `forge-*` so it doesn't collide with the legacy `display`/`body` stacks below
        // (still read by unmigrated pages). `forge-serif` (Fraunces) is used exclusively
        // for the one sentence per screen meant to be felt; `forge-sans` (Hanken
        // Grotesk, standing in for the unpublished "General Sans" reference) is every
        // functional surface; `forge-mono` (JetBrains Mono) is reserved strictly for
        // scanned/compared numerals — never prose.
        "forge-serif": ["Fraunces", "ui-serif", "Georgia", "serif"],
        "forge-sans": ["'Hanken Grotesk'", "-apple-system", "'Segoe UI'", "sans-serif"],
        "forge-mono": ["'JetBrains Mono'", "ui-monospace", "SFMono-Regular", "monospace"],
        // A confident, large-scale grotesk-style system stack — no network font fetch, no
        // decorative serif. Weight and tracking carry the "premium" feel, not a novelty typeface.
        display: [
          "'Segoe UI'",
          "-apple-system",
          "ui-sans-serif",
          "Inter",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        body: [
          "-apple-system",
          "'Segoe UI'",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
      boxShadow: {
        glow: "0 0 60px -12px rgba(124, 44, 255, 0.5)",
        "glow-sm": "0 0 24px -8px rgba(124, 44, 255, 0.45)",
        "glow-blue": "0 0 60px -14px rgba(22, 139, 255, 0.45)",
        "glow-gold": "0 0 50px -12px rgba(255, 157, 28, 0.45)",
        // Cosmic glow family — used sparingly (GlassCard's `glow` prop, ForgeCore, the
        // Threshold CTA) per the Rule of Subtraction, never as a default on every surface.
        "glow-forge-accent": "0 0 60px -14px rgba(255, 176, 32, 0.55)",
        "glow-forge-accent-2": "0 0 60px -14px rgba(139, 92, 246, 0.5)",
        "glow-forge-accent-3": "0 0 50px -14px rgba(99, 230, 232, 0.4)",
        // Exactly one elevated shadow level (`elevation-1`), reserved for the command
        // capsule and dialogs only; nothing else reaches a second elevation level or uses
        // a raw Tailwind shadow utility.
        "forge-1": "var(--forge-elevation-1)",
      },
      transitionDuration: {
        400: "400ms",
        600: "600ms",
        900: "900ms",
      },
      keyframes: {
        "pulse-slow": {
          "0%, 100%": { opacity: "0.5" },
          "50%": { opacity: "1" },
        },
        drift: {
          "0%": { transform: "translate(0, 0)" },
          "50%": { transform: "translate(6px, -8px)" },
          "100%": { transform: "translate(0, 0)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-10px)" },
        },
        breathe: {
          "0%, 100%": { filter: "drop-shadow(0 0 18px rgba(139,92,246,0.35)) drop-shadow(0 0 10px rgba(255,176,32,0.2))" },
          "50%": { filter: "drop-shadow(0 0 34px rgba(139,92,246,0.55)) drop-shadow(0 0 18px rgba(255,176,32,0.35))" },
        },
        orbit: {
          from: { transform: "rotate(0deg) translateX(var(--orbit-radius)) rotate(0deg)" },
          to: { transform: "rotate(360deg) translateX(var(--orbit-radius)) rotate(-360deg)" },
        },
        "cta-breathe": {
          "0%, 100%": { boxShadow: "0 0 30px -8px rgba(255,176,32,0.55)" },
          "50%": { boxShadow: "0 0 46px -6px rgba(139,92,246,0.5)" },
        },
        "border-spin": {
          to: { backgroundPosition: "200% center" },
        },
        "gradient-slow": {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
        // Extremely slow ambient background motion — starfield/nebula, never used for any
        // UI element a founder needs to track.
        "nebula-drift": {
          "0%, 100%": { transform: "translate(0, 0) scale(1)", opacity: "0.55" },
          "50%": { transform: "translate(3%, -2%) scale(1.05)", opacity: "0.75" },
        },
      },
      animation: {
        "pulse-slow": "pulse-slow 3.5s ease-in-out infinite",
        drift: "drift 8s ease-in-out infinite",
        float: "float 6s ease-in-out infinite",
        breathe: "breathe 4s ease-in-out infinite",
        orbit: "orbit linear infinite",
        "cta-breathe": "cta-breathe 3.2s ease-in-out infinite",
        "border-spin": "border-spin 3s linear infinite",
        "gradient-slow": "gradient-slow 8s ease-in-out infinite",
        "nebula-drift": "nebula-drift 22s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
