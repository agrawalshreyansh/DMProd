import { getToken } from "@/lib/session";
import { backendFetch, requireJson } from "@/lib/api";
import TaskRoutingForm from "@/components/TaskRoutingForm";

type RoutingResponse = { task_type_routing: Record<string, string | null> };

export default async function PreferencesPage() {
  const token = await getToken();
  const res = await backendFetch("/api/v1/preferences", {}, token);
  const { task_type_routing } = await requireJson<RoutingResponse>(res);

  return (
    <div className="flex max-w-lg flex-col gap-4">
      <h1 className="font-display text-xl font-semibold">Preferences</h1>
      <p className="text-sm leading-relaxed text-foreground-muted">
        Choose which task types get pushed to Notion automatically once a
        reel finishes processing. Unchecked types stay in the dashboard only.
      </p>
      <TaskRoutingForm initialRouting={task_type_routing} />
    </div>
  );
}
