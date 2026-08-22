export default function DashboardOverviewPage() {
  return (
    <div className="flex flex-col gap-2">
      <h1 className="font-display text-xl font-semibold">Overview</h1>
      <p className="max-w-md text-sm leading-relaxed text-foreground-muted">
        Welcome. Connect your Instagram account and set your Gemini API key
        in Settings to get started once later phases land.
      </p>
    </div>
  );
}
