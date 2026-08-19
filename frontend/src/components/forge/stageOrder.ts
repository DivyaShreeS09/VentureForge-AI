/** Founder-facing stage vocabulary for Act IV (The Forging) — must exactly match
 * backend/app/agents/stage_labels.py's STAGE_ORDER by name (a shared vocabulary of plain-language
 * labels, not shared logic: the backend alone decides which real orchestrator node maps to which
 * label and writes the authoritative `current_stage` string onto the Analysis row; this file only
 * needs to know the fixed order those strings appear in, so it can render "done / current /
 * upcoming" from a single real field without knowing any raw node id). */
export const STAGE_ORDER: string[] = [
  "Reading Your Idea",
  "Understanding Your Industry",
  "Scoring Your Readiness",
  "Comparing Historical Patterns",
  "Modeling Your Revenue",
  "Studying Your Market",
  "Mapping Your Growth Strategy",
  "Checking Your Evidence",
  "Preparing Your Mentor Report",
];

export interface StageStatus {
  label: string;
  state: "done" | "current" | "upcoming";
}

/** Derives each stage's real status from the two real signals available: `currentStage` (the
 * backend's own last-completed-node label) and whether the run has already reached a terminal
 * status. Never infers anything about a stage the backend hasn't actually reported reaching. */
export function deriveStageStatuses(currentStage: string | null, isTerminal: boolean): StageStatus[] {
  const currentIndex = currentStage ? STAGE_ORDER.indexOf(currentStage) : -1;
  return STAGE_ORDER.map((label, index) => {
    if (isTerminal && index <= currentIndex) return { label, state: "done" as const };
    if (index < currentIndex) return { label, state: "done" as const };
    if (index === currentIndex) return { label, state: "current" as const };
    return { label, state: "upcoming" as const };
  });
}
