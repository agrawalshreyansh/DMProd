export default function BreakdownBars({
  items,
  labels,
}: {
  items: { label: string; count: number }[];
  labels?: Record<string, string>;
}) {
  if (items.length === 0) {
    return <p className="text-sm text-foreground-muted">No data yet.</p>;
  }

  const max = Math.max(...items.map((item) => item.count));

  return (
    <div className="flex flex-col gap-3">
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-3">
          <span className="w-36 shrink-0 truncate text-xs text-foreground-muted">
            {labels?.[item.label] ?? item.label}
          </span>
          <div className="h-2 flex-1 overflow-hidden rounded-full bg-background-elevated-2">
            <div
              className="h-full rounded-full bg-accent-signal"
              style={{ width: `${(item.count / max) * 100}%` }}
            />
          </div>
          <span className="w-6 shrink-0 text-right font-mono text-xs text-foreground-muted">
            {item.count}
          </span>
        </div>
      ))}
    </div>
  );
}
