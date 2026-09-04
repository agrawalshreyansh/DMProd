import BreakdownBars from "@/components/BreakdownBars";
import DashboardPageHeader from "@/components/DashboardPageHeader";
import StatTile from "@/components/StatTile";
import { getToken } from "@/lib/session";
import { backendFetch, requireJson } from "@/lib/api";
import { TASK_TYPE_LABELS, type Stats } from "@/lib/types";

const DESTINATION_LABELS: Record<string, string> = {
  notion: "Notion",
  google_calendar: "Google Calendar",
};

export default async function StatsPage() {
  const token = await getToken();
  const res = await backendFetch("/api/v1/stats", {}, token);
  const stats = await requireJson<Stats>(res);

  return (
    <div className="flex flex-col gap-8">
      <DashboardPageHeader
        eyebrow="SIG.06"
        title="Stats"
        description="What's actually flowing through the pipeline."
      />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Total reels" value={stats.total_reels} accent />
        <StatTile label="This week" value={stats.reels_this_week} />
        <StatTile label="This month" value={stats.reels_this_month} />
        <StatTile
          label="Success rate"
          value={
            stats.total_reels === 0
              ? "—"
              : `${Math.round((stats.reels_succeeded / stats.total_reels) * 100)}%`
          }
        />
      </div>

      <div className="grid grid-cols-3 gap-3">
        <StatTile label="Succeeded" value={stats.reels_succeeded} accent />
        <StatTile label="Processing" value={stats.reels_processing} />
        <StatTile label="Failed" value={stats.reels_failed} />
      </div>

      <div className="flex flex-col gap-3 rounded-lg border border-border bg-background-elevated p-5">
        <h2 className="font-display text-sm font-semibold text-foreground">By task type</h2>
        <BreakdownBars items={stats.by_task_type} labels={TASK_TYPE_LABELS} />
      </div>

      <div className="flex flex-col gap-3 rounded-lg border border-border bg-background-elevated p-5">
        <h2 className="font-display text-sm font-semibold text-foreground">By destination</h2>
        <BreakdownBars items={stats.by_destination} labels={DESTINATION_LABELS} />
      </div>
    </div>
  );
}
