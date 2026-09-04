import DashboardPageHeader from "@/components/DashboardPageHeader";
import HistoryTable from "@/components/HistoryTable";
import { getToken } from "@/lib/session";
import { backendFetch, requireJson } from "@/lib/api";
import { OUTCOME_LABELS, TASK_TYPE_LABELS, type Reel } from "@/lib/types";

const SELECT_CLASS =
  "rounded-md border border-border bg-background px-2 py-1.5 text-sm text-foreground";
const LABEL_CLASS = "flex flex-col gap-1";
const LEGEND_CLASS = "font-mono text-[10px] uppercase tracking-widest text-foreground-muted";

export default async function HistoryPage({
  searchParams,
}: {
  searchParams: Promise<{
    task_type?: string;
    status?: string;
    date_from?: string;
    date_to?: string;
  }>;
}) {
  const { task_type, status, date_from, date_to } = await searchParams;
  const token = await getToken();

  const params = new URLSearchParams();
  if (task_type) params.set("task_type", task_type);
  if (status) params.set("status", status);
  if (date_from) params.set("date_from", date_from);
  if (date_to) params.set("date_to", date_to);
  const query = params.toString();

  const res = await backendFetch(`/api/v1/reels${query ? `?${query}` : ""}`, {}, token);
  const reels = await requireJson<Reel[]>(res);
  const hasFilters = Boolean(task_type || status || date_from || date_to);

  return (
    <div className="flex flex-col gap-6">
      <DashboardPageHeader
        eyebrow="SIG.04"
        title="History"
        description="Every reel you've shared, what it turned into, and where it landed."
      />

      <form className="flex flex-wrap items-end gap-3 rounded-lg border border-border bg-background-elevated p-4">
        <label className={LABEL_CLASS}>
          <span className={LEGEND_CLASS}>Task type</span>
          <select name="task_type" defaultValue={task_type ?? ""} className={SELECT_CLASS}>
            <option value="">All</option>
            {Object.entries(TASK_TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className={LABEL_CLASS}>
          <span className={LEGEND_CLASS}>Status</span>
          <select name="status" defaultValue={status ?? ""} className={SELECT_CLASS}>
            <option value="">All</option>
            {Object.entries(OUTCOME_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label className={LABEL_CLASS}>
          <span className={LEGEND_CLASS}>From</span>
          <input type="date" name="date_from" defaultValue={date_from ?? ""} className={SELECT_CLASS} />
        </label>
        <label className={LABEL_CLASS}>
          <span className={LEGEND_CLASS}>To</span>
          <input type="date" name="date_to" defaultValue={date_to ?? ""} className={SELECT_CLASS} />
        </label>
        <button
          type="submit"
          className="rounded-md bg-accent-signal px-4 py-1.5 text-sm font-medium text-background transition hover:brightness-110"
        >
          Filter
        </button>
        {hasFilters && (
          <a
            href="/dashboard/history"
            className="text-xs text-foreground-muted underline underline-offset-2"
          >
            Clear
          </a>
        )}
      </form>

      {reels.length === 0 ? (
        <p className="text-sm leading-relaxed text-foreground-muted">
          {hasFilters ? (
            "No reels match these filters."
          ) : (
            <>
              No reels yet. Connect your Instagram account in{" "}
              <span className="text-foreground">Instagram Account</span>, then DM the bot a reel —
              it&apos;ll show up here.
            </>
          )}
        </p>
      ) : (
        <HistoryTable reels={reels} />
      )}
    </div>
  );
}
