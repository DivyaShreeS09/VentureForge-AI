import { AnimatePresence } from "framer-motion";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "../primitives/Button";
import { Chip } from "../primitives/Chip";
import { TextField } from "../primitives/TextField";
import { GlassCard } from "../primitives/GlassCard";
import type { ForgeSemanticState } from "../tokens/forge";
import { clearHistory, deleteHistoryEntry, exportHistoryAsJson, listHistory, type HistoryEntry } from "../services/localHistory";

const LEVEL_STATE: Record<string, ForgeSemanticState> = {
  ready: "confirmed",
  developing: "notSureYet",
  early_stage: "notSureYet",
};

const LEVEL_LABEL: Record<string, string> = {
  ready: "Investor Ready",
  developing: "Building Momentum",
  early_stage: "Idea Formation",
};

type SortKey = "newest" | "oldest" | "score";

const selectClasses =
  "rounded-forge-md border border-forge-text/[.12] bg-forge-surface-1 px-3 py-2 text-forge-2 " +
  "text-forge-text-secondary focus:border-forge-accent focus:outline-none transition-colors";

/** Purely a client-side convenience view over this browser's local analysis history — no
 * authentication, no server-side history endpoint (see services/localHistory.ts).
 *
 * Rewritten onto the forge design tokens (Design System Bible) — this page previously used a
 * leftover pre-rebrand color system (signal, ink, gold, danger utility colors, translucent white
 * borders on an implicit dark-purple gradient) that never matched the cream/charcoal/copper
 * palette every other page already uses, making this the one screen that visually looked like a
 * different, generic product. */
export function HistoryPage() {
  const [entries, setEntries] = useState<HistoryEntry[]>(() => listHistory());
  const [query, setQuery] = useState("");
  const [industryFilter, setIndustryFilter] = useState("all");
  const [sort, setSort] = useState<SortKey>("newest");

  const industries = useMemo(
    () => Array.from(new Set(entries.map((e) => e.industry).filter((v): v is string => !!v))),
    [entries],
  );

  const filtered = useMemo(() => {
    let list = entries.filter((e) => e.name.toLowerCase().includes(query.trim().toLowerCase()));
    if (industryFilter !== "all") list = list.filter((e) => e.industry === industryFilter);
    if (sort === "oldest") list = [...list].sort((a, b) => new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime());
    if (sort === "score") list = [...list].sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
    return list;
  }, [entries, query, industryFilter, sort]);

  function handleDelete(id: string) {
    deleteHistoryEntry(id);
    setEntries(listHistory());
  }

  function handleClearAll() {
    clearHistory();
    setEntries([]);
  }

  function handleExport() {
    const blob = new Blob([exportHistoryAsJson()], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "ventureforge-history.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <main className="min-h-[100dvh] w-full px-6 py-14 font-forge-sans forge-sm:px-10">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-forge-1 font-medium uppercase tracking-[0.25em] text-forge-text-tertiary">Analysis History</p>
            <h1 className="mt-2 font-forge-serif text-forge-6 font-medium text-forge-text">Track your progress</h1>
            <p className="mt-1 text-forge-1 text-forge-text-tertiary">Analyses are saved locally in your anonymous workspace.</p>
          </div>
          <div className="flex gap-3">
            <Button variant="secondary" onClick={handleExport} disabled={entries.length === 0}>
              Export report
            </Button>
            <Button
              variant="ghost"
              onClick={handleClearAll}
              disabled={entries.length === 0}
              className="text-forge-risk hover:text-forge-risk"
            >
              Clear all history
            </Button>
          </div>
        </div>

        <div className="mt-8 flex flex-wrap items-center gap-3">
          <div className="min-w-[220px] max-w-xs rounded-forge-md border border-forge-text/[.12] bg-forge-surface-1 px-4">
            <TextField value={query} onChange={setQuery} placeholder="Search analyses…" aria-label="Search analyses" />
          </div>
          <select
            value={industryFilter}
            onChange={(e) => setIndustryFilter(e.target.value)}
            aria-label="Filter by industry"
            className={selectClasses}
          >
            <option value="all">All Industries</option>
            {industries.map((i) => (
              <option key={i} value={i}>
                {i}
              </option>
            ))}
          </select>
          <select
            value={sort}
            onChange={(e) => setSort(e.target.value as SortKey)}
            aria-label="Sort order"
            className={selectClasses}
          >
            <option value="newest">Newest First</option>
            <option value="oldest">Oldest First</option>
            <option value="score">Highest Score</option>
          </select>
        </div>

        <div className="mt-6 space-y-3">
          {filtered.length === 0 && (
            <GlassCard className="p-10 text-center text-forge-2 text-forge-text-tertiary">
              {entries.length === 0
                ? "No analyses yet — start a new venture analysis to see it here."
                : "No analyses match your search or filters."}
            </GlassCard>
          )}
          <AnimatePresence initial={false}>
            {filtered.map((e, i) => (
              <GlassCard
                key={e.analysisId}
                interactive
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -12 }}
                transition={{ duration: 0.25, delay: Math.min(i * 0.03, 0.3) }}
                className="flex flex-wrap items-center justify-between gap-4 p-4"
              >
                <div className="min-w-0">
                  <p className="text-forge-2 font-medium text-forge-text">{e.name}</p>
                  <p className="mt-0.5 text-forge-1 text-forge-text-tertiary">
                    {e.industry ?? "Unclassified"} · {new Date(e.createdAt).toLocaleString()}
                  </p>
                </div>
                <div className="flex items-center gap-4">
                  <Chip state={LEVEL_STATE[e.level] ?? "notSureYet"} label={LEVEL_LABEL[e.level] ?? e.level} />
                  <span className="font-forge-serif text-forge-4 text-forge-text">
                    {e.score ?? "—"}
                    <span className="text-forge-1 text-forge-text-tertiary">/100</span>
                  </span>
                  <Link
                    to={`/analyses/${e.analysisId}`}
                    className="rounded-forge-md border border-forge-text/[.16] px-3 py-1.5 text-forge-1 font-medium text-forge-text-secondary transition-colors hover:border-forge-accent-2/50 hover:text-forge-text"
                  >
                    View
                  </Link>
                  <button
                    onClick={() => handleDelete(e.analysisId)}
                    aria-label={`Delete history entry for ${e.name}`}
                    className="rounded-forge-md border border-forge-text/[.12] px-2.5 py-1.5 text-forge-1 text-forge-text-tertiary transition-colors hover:border-forge-risk/40 hover:text-forge-risk"
                  >
                    ✕
                  </button>
                </div>
              </GlassCard>
            ))}
          </AnimatePresence>
        </div>
      </div>
    </main>
  );
}
