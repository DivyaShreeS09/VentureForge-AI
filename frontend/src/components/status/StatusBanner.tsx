export function LoadingBanner({ message }: { message: string }) {
  return (
    <p role="status" className="flex items-center gap-3 text-sm text-ink-muted">
      <span className="h-2 w-2 animate-pulse rounded-full bg-signal-400" aria-hidden="true" />
      {message}
    </p>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <p role="alert" className="rounded-xl border border-danger-500/30 bg-danger-500/10 p-4 text-sm text-danger-400">
      {message}
    </p>
  );
}
