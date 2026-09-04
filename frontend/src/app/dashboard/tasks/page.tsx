import DashboardPageHeader from "@/components/DashboardPageHeader";
import { getToken } from "@/lib/session";
import { backendFetch, requireJson } from "@/lib/api";
import TasksTable from "@/components/TasksTable";
import type { Task } from "@/lib/types";

export default async function TasksPage() {
  const token = await getToken();
  const res = await backendFetch("/api/v1/tasks", {}, token);
  const tasks = await requireJson<Task[]>(res);

  return (
    <div className="flex flex-col gap-4">
      <DashboardPageHeader eyebrow="SIG.05" title="Tasks" />

      {tasks.length === 0 ? (
        <p className="text-sm leading-relaxed text-foreground-muted">
          No tasks yet. Once a reel you&apos;ve shared finishes processing,
          the task Gemini extracts from it shows up here — no integration
          needed to track it.
        </p>
      ) : (
        <TasksTable tasks={tasks} />
      )}
    </div>
  );
}
