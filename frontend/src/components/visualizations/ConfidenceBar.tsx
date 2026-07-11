/** A single labeled confidence bar — used for the primary industry alternatives list. The percent
 * is always rendered as text next to the bar, never conveyed by width/color alone. */
export function ConfidenceBar({ label, confidence }: { label: string; confidence: number }) {
  return (
    <li className="flex items-center gap-3">
      <span className="w-28 shrink-0 truncate text-sm capitalize text-ink-secondary">{label}</span>
      <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
        <span
          className="block h-full rounded-full bg-gradient-to-r from-current-500 to-signal-500 transition-[width] duration-700"
          style={{ width: `${confidence * 100}%` }}
        />
      </span>
      <span className="w-12 shrink-0 text-right text-xs text-ink-muted">{(confidence * 100).toFixed(0)}%</span>
    </li>
  );
}
