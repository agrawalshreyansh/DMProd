export default function DashboardPageHeader({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description?: string;
}) {
  return (
    <div className="flex flex-col gap-2">
      <span className="font-mono text-xs font-medium uppercase tracking-[0.2em] text-accent-signal">
        {eyebrow}
      </span>
      <h1 className="font-display text-2xl font-semibold tracking-tight text-foreground">{title}</h1>
      {description && (
        <p className="max-w-lg text-sm leading-relaxed text-foreground-muted">{description}</p>
      )}
    </div>
  );
}
