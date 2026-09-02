"use client";

import { useState } from "react";
import TaskStatusSelect from "@/components/TaskStatusSelect";
import TaskDetailModal from "@/components/TaskDetailModal";
import { TASK_TYPE_LABELS, type Task } from "@/lib/types";
import { safeHref } from "@/lib/safeHref";

export default function TasksTable({ tasks }: { tasks: Task[] }) {
  const [openTask, setOpenTask] = useState<Task | null>(null);

  return (
    <>
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-left text-sm">
          <thead className="bg-background-elevated text-xs uppercase tracking-widest text-foreground-muted">
            <tr>
              <th className="px-4 py-3 font-medium">Task</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium">Reel</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Created</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((task) => {
              const reelHref = safeHref(task.reel_url);
              return (
              <tr
                key={task.id}
                onClick={() => setOpenTask(task)}
                className="cursor-pointer border-t border-border transition hover:bg-background-elevated-2"
              >
                <td className="max-w-xs px-4 py-3">
                  <p className="font-medium text-foreground">{task.title}</p>
                  {task.details.description && (
                    <p className="mt-0.5 truncate text-xs text-foreground-muted">
                      {task.details.description}
                    </p>
                  )}
                </td>
                <td className="px-4 py-3 text-foreground-muted">
                  {TASK_TYPE_LABELS[task.task_type] ?? task.task_type}
                </td>
                <td className="max-w-[12rem] truncate px-4 py-3">
                  {reelHref ? (
                    <a
                      href={reelHref}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="text-accent-signal underline underline-offset-2"
                    >
                      {task.reel_caption || "View reel"}
                    </a>
                  ) : (
                    <span className="text-foreground-muted">{task.reel_caption || "—"}</span>
                  )}
                </td>
                <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                  <TaskStatusSelect taskId={task.id} initialStatus={task.status} />
                </td>
                <td
                  suppressHydrationWarning
                  className="whitespace-nowrap px-4 py-3 font-mono text-xs text-foreground-muted"
                >
                  {new Date(task.created_at).toLocaleString()}
                </td>
              </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {openTask && <TaskDetailModal task={openTask} onClose={() => setOpenTask(null)} />}
    </>
  );
}
