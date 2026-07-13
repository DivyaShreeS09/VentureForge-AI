import { AnimatePresence, motion } from "framer-motion";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { clearHistory, deleteHistoryEntry, exportHistoryAsJson, listHistory, type HistoryEntry } from "../services/localHistory";

const LEVEL_STYLES: Record<string, string> = {
  ready: "border-gold-500/30 bg-gold-500/10 text-gold-300",
  developing: "border-signal-500/30 bg-signal-500/10 text-signal-300",
  early_stage: "border-white/15 bg-white/5 text-ink-muted",
};

const LEVEL_LABEL: Record<string, string> = {
  ready: "Investor Ready",
  developing: "Building Momentum",
  early_stage: "Idea Formation",
};

type SortKey = "newest" | "oldest" | "score";

/** Purely a client-side convenience view over this browser's local analysis history — no
 * authentication, no server-side history endpoint (see services/localHistory.ts). */
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
    <div className="mx-auto max-w-6xl px-6 py-14 sm:px-10">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.25em] text-signal-400">Analysis History</p>
          <h1 className="mt-2 text-display text-3xl">Track your progress</h1>
          <p className="mt-1 text-xs text-ink-muted">Analyses are saved locally in your anonymous workspace.</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={handleExport}
            disabled={entries.length === 0}
            className="rounded-lg border border-white/15 px-4 py-2 text-sm font-medium text-ink-secondary transition hover:border-signal-400/50 hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Export report
          </button>
          <button
            onClick={handleClearAll}
            disabled={entries.length === 0}
            className="rounded-lg border border-danger-500/30 px-4 py-2 text-sm font-medium text-danger-400 transition hover:bg-danger-500/10 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Clear all history
          </button>
        </div>
      </div>

      <div className="mt-8 flex flex-wrap items-center gap-3">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search analyses…"
          className="rounded-lg border border-white/10 bg-white/[0.04] px-4 py-2 text-sm text-ink-primary placeholder:text-ink-muted focus:border-signal-400/60 focus:outline-none focus:ring-2 focus:ring-signal-500/25"
        />
        <select
          value={industryFilter}
          onChange={(e) => setIndustryFilter(e.target.value)}
          className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-sm text-ink-secondary focus:border-signal-400/60 focus:outline-none focus:ring-2 focus:ring-signal-500/25"
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
          className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2 text-sm text-ink-secondary focus:border-signal-400/60 focus:outline-none focus:ring-2 focus:ring-signal-500/25"
        >
          <option value="newest">Newest First</option>
          <option value="oldest">Oldest First</option>
          <option value="score">Highest Score</option>
        </select>
      </div>

      <div className="mt-6 space-y-3">
        {filtered.length === 0 && (
          <div className="panel p-10 text-center text-sm text-ink-muted">
            {entries.length === 0
              ? "No analyses yet — start a new venture analysis to see it here."
              : "No analyses match your search or filters."}
          </div>
        )}
        <AnimatePresence initial={false}>
          {filtered.map((e, i) => (
            <motion.div
              key={e.analysisId}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, x: -12 }}
              transition={{ duration: 0.25, delay: Math.min(i * 0.03, 0.3) }}
              className="panel hover-lift flex flex-wrap items-center justify-between gap-4 p-4"
            >
              <div className="flex min-w-0 items-center gap-4">
                <div>
                  <p className="text-sm font-medium text-ink-primary">{e.name}</p>
                  <p className="mt-0.5 text-xs text-ink-muted">
                    {e.industry ?? "Unclassified"} · {new Date(e.createdAt).toLocaleString()}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <span className={`rounded-full border px-3 py-1 text-xs font-medium ${LEVEL_STYLES[e.level] ?? LEVEL_STYLES.early_stage}`}>
                  {LEVEL_LABEL[e.level] ?? e.level}
                </span>
                <span className="text-display text-lg text-ink-primary">
                  {e.score ?? "—"}
                  <span className="text-xs text-ink-muted">/100</span>
                </span>
                <Link
                  to={`/analyses/${e.analysisId}`}
                  className="rounded-lg border border-white/15 px-3 py-1.5 text-xs font-medium text-ink-secondary transition hover:border-signal-400/50 hover:bg-white/5"
                >
                  View
                </Link>
                <button
                  onClick={() => handleDelete(e.analysisId)}
                  aria-label={`Delete history entry for ${e.name}`}
                  className="rounded-lg border border-white/10 px-2.5 py-1.5 text-xs text-ink-muted transition hover:border-danger-500/40 hover:text-danger-400"
                >
                  ✕
                </button>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}
