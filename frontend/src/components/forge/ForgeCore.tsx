import emblem from "../../assets/ventureforge-emblem.webp";

const RADIUS = 92;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export type ForgeCoreState = "idle" | "running" | "done" | "error";

interface Props {
  state: ForgeCoreState;
  /** Real fraction (0-1) of orchestrator stages that have reported "ok" so far — never a
   * simulated timer. See ForgeSequence, which derives this from the actual workflow trace. */
  progress: number;
}

/** Violet energy at the start of a run, an electric-blue intelligence pulse through the middle of
 * the analysis, and gold ignition only once the run has actually completed — never gold before
 * real completion, since gold is reserved for genuine achievement per the brand's color hierarchy. */
function phaseColor(state: ForgeCoreState, progress: number): string {
  if (state === "error") return "#ff5a6b";
  if (state === "done") return "#ff9d1c";
  if (state === "idle") return "#7c2cff";
  return progress < 0.5 ? "#7c2cff" : "#168bff";
}

/**
 * The official VentureForgeAI emblem as the living reactor core of the Forge sequence. Two
 * counter-rotating orbit rings plus a progress ring surround the mark; all color and motion is
 * driven by real orchestrator state passed in as props — nothing here is a simulated countdown.
 */
export function ForgeCore({ state, progress }: Props) {
  const clamped = Math.max(0, Math.min(1, progress));
  // Idle is a resting decorative state (e.g. the Home screen, where nothing is actually running) —
  // it draws a full, static ring rather than any particular fake percentage.
  const offset = state === "idle" ? 0 : CIRCUMFERENCE * (1 - clamped);
  const color = phaseColor(state, clamped);
  const isDone = state === "done";

  return (
    <div className="relative flex h-64 w-64 items-center justify-center sm:h-72 sm:w-72">
      <div
        className={`absolute inset-0 rounded-full blur-2xl transition-colors duration-700 ${state === "idle" ? "animate-pulse-slow" : ""}`}
        style={{ backgroundColor: `${color}22` }}
        aria-hidden="true"
      />

      <svg
        width="256"
        height="256"
        viewBox="0 0 256 256"
        role="img"
        aria-label={
          state === "idle"
            ? "VentureForge AI emblem"
            : state === "error"
              ? "Venture forge sequence failed"
              : isDone
                ? "Venture blueprint forged"
                : `Venture forge sequence in progress, ${Math.round(clamped * 100)} percent complete`
        }
      >
        <circle
          cx="128"
          cy="128"
          r={112}
          fill="none"
          stroke="rgba(245,247,255,0.05)"
          strokeWidth="1"
          strokeDasharray="1 7"
          className={state === "running" || state === "idle" ? "origin-center animate-spin-slow" : ""}
        />
        <circle
          cx="128"
          cy="128"
          r={104}
          fill="none"
          stroke="rgba(245,247,255,0.04)"
          strokeWidth="1"
          strokeDasharray="3 5"
          className={state === "running" || state === "idle" ? "origin-center animate-spin-reverse-slow" : ""}
        />
        <circle cx="128" cy="128" r={RADIUS} fill="none" stroke="rgba(245,247,255,0.06)" strokeWidth="9" />
        <circle
          cx="128"
          cy="128"
          r={RADIUS}
          fill="none"
          stroke={color}
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={offset}
          transform="rotate(-90 128 128)"
          className="transition-[stroke-dashoffset,stroke] duration-700 ease-out"
          style={{ filter: `drop-shadow(0 0 14px ${color}90)` }}
        />
      </svg>

      <div className="absolute flex flex-col items-center">
        <img
          src={emblem}
          alt=""
          aria-hidden="true"
          className={`w-28 transition-[filter] duration-700 sm:w-32 ${isDone ? "animate-ignite" : ""}`}
          style={{ filter: `drop-shadow(0 0 ${isDone ? 30 : 16}px ${color}${isDone ? "cc" : "80"})` }}
        />
        {state !== "idle" && (
          <span className="mt-3 text-display text-xl text-ink-primary">{Math.round(clamped * 100)}%</span>
        )}
        <span className={`text-xs uppercase tracking-[0.2em] text-ink-muted ${state === "idle" ? "mt-3" : "mt-0.5"}`}>
          {state === "idle" ? "VentureForge Core" : state === "error" ? "Halted" : isDone ? "Forged" : "Forging"}
        </span>
      </div>
    </div>
  );
}
