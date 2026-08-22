export default function ComingSoon({ title }: { title: string }) {
  return (
    <div className="flex flex-col gap-2">
      <h1 className="font-display text-xl font-semibold">{title}</h1>
      <p className="font-mono text-xs uppercase tracking-widest text-foreground-muted">
        Coming soon
      </p>
    </div>
  );
}
