export default function StatTile({
  label,
  value,
  accent = false,
}: {
  label: string;
  value: string | number;
  accent?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1.5 rounded-lg border border-border bg-background-elevated p-4">
      <span className="font-mono text-xs uppercase tracking-widest text-foreground-muted">{label}</span>
      <span
        className={`font-display text-3xl font-semibold tabular-nums ${
          accent ? "text-accent-signal" : "text-foreground"
        }`}
      >
        {value}
      </span>
    </div>
  );
}
