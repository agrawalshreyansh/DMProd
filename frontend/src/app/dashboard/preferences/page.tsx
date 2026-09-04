import DashboardPageHeader from "@/components/DashboardPageHeader";
import { getToken } from "@/lib/session";
import { backendFetch, requireJson } from "@/lib/api";
import TaskRoutingForm from "@/components/TaskRoutingForm";
import CalendarSchedulingForm, { type CalendarScheduling } from "@/components/CalendarSchedulingForm";

type PreferencesResponse = {
  task_type_routing: Record<string, string | null>;
  calendar_scheduling: CalendarScheduling;
};

export default async function PreferencesPage() {
  const token = await getToken();
  const res = await backendFetch("/api/v1/preferences", {}, token);
  const { task_type_routing, calendar_scheduling } = await requireJson<PreferencesResponse>(res);

  return (
    <div className="flex max-w-lg flex-col gap-6">
      <DashboardPageHeader
        eyebrow="SIG.03"
        title="Preferences"
        description="Choose which task types get pushed automatically once a reel finishes processing. Unrouted types stay in the dashboard only."
      />
      <TaskRoutingForm initialRouting={task_type_routing} />
      <CalendarSchedulingForm initial={calendar_scheduling} />
    </div>
  );
}
