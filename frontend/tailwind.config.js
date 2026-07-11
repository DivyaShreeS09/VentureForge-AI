/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
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
      },
      fontFamily: {
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
      },
      transitionDuration: {
        400: "400ms",
        600: "600ms",
        900: "900ms",
      },
      backgroundImage: {
        "grid-fine": "linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px)",
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
        "spin-slow": {
          to: { transform: "rotate(360deg)" },
        },
        "spin-reverse-slow": {
          from: { transform: "rotate(360deg)" },
          to: { transform: "rotate(0deg)" },
        },
        reveal: {
          "0%": { opacity: "0", transform: "translateY(14px) scale(0.98)" },
          "100%": { opacity: "1", transform: "translateY(0) scale(1)" },
        },
        ignite: {
          "0%": { filter: "drop-shadow(0 0 0px rgba(255,157,28,0))" },
          "60%": { filter: "drop-shadow(0 0 42px rgba(255,157,28,0.85))" },
          "100%": { filter: "drop-shadow(0 0 26px rgba(255,157,28,0.55))" },
        },
        sweep: {
          "0%": { backgroundPosition: "-150% 0" },
          "100%": { backgroundPosition: "250% 0" },
        },
      },
      animation: {
        "pulse-slow": "pulse-slow 3.5s ease-in-out infinite",
        drift: "drift 8s ease-in-out infinite",
        "spin-slow": "spin-slow 14s linear infinite",
        "spin-reverse-slow": "spin-reverse-slow 20s linear infinite",
        reveal: "reveal 700ms cubic-bezier(0.16, 1, 0.3, 1) both",
        ignite: "ignite 900ms ease-out both",
      },
    },
  },
  plugins: [],
};
