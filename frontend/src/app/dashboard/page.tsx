import Link from "next/link";
import DashboardPageHeader from "@/components/DashboardPageHeader";
import StatTile from "@/components/StatTile";
import SignalStrip from "@/components/SignalStrip";
import { getToken } from "@/lib/session";
import { backendFetch, requireJson } from "@/lib/api";
import type { Stats } from "@/lib/types";

export default async function DashboardOverviewPage() {
  const token = await getToken();
  const res = await backendFetch("/api/v1/stats", {}, token);
  const stats = await requireJson<Stats>(res);

  return (
    <div className="flex flex-col gap-8">
      <DashboardPageHeader
        eyebrow="SIG.00"
        title="Overview"
        description="Connect your Instagram account and set your Gemini API key in Settings, then share a reel to see it show up here."
      />

      <SignalStrip />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatTile label="Total reels" value={stats.total_reels} accent />
        <StatTile label="This week" value={stats.reels_this_week} />
        <StatTile label="Processing" value={stats.reels_processing} />
        <StatTile label="Failed" value={stats.reels_failed} />
      </div>

      <div className="flex flex-wrap gap-3">
        <Link
          href="/dashboard/history"
          className="rounded-md border border-border bg-background-elevated px-4 py-2 text-sm text-foreground transition hover:bg-background-elevated-2"
        >
          View history →
        </Link>
        <Link
          href="/dashboard/tasks"
          className="rounded-md border border-border bg-background-elevated px-4 py-2 text-sm text-foreground transition hover:bg-background-elevated-2"
        >
          View tasks →
        </Link>
        <Link
          href="/dashboard/stats"
          className="rounded-md border border-border bg-background-elevated px-4 py-2 text-sm text-foreground transition hover:bg-background-elevated-2"
        >
          Full stats →
        </Link>
      </div>
    </div>
  );
}
