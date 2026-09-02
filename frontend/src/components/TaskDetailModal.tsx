"use client";

import { useEffect } from "react";
import TaskStatusSelect from "@/components/TaskStatusSelect";
import { TASK_TYPE_LABELS, type Task } from "@/lib/types";
import { safeHref } from "@/lib/safeHref";

export default function TaskDetailModal({
  task,
  onClose,
}: {
  task: Task;
  onClose: () => void;
}) {
  const linkHref = safeHref(task.details.link);
  const reelHref = safeHref(task.reel_url);

  useEffect(() => {
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);

    return () => {
      document.body.style.overflow = originalOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [onClose]);

  return (
    <div
      role="presentation"
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-6 pt-16 sm:pt-24"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="task-detail-title"
        onClick={(e) => e.stopPropagation()}
        className="flex w-full max-w-xl flex-col gap-5 rounded-lg border border-border bg-background-elevated p-6 shadow-xl"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <span className="font-mono text-xs uppercase tracking-widest text-foreground-muted">
              {TASK_TYPE_LABELS[task.task_type] ?? task.task_type}
            </span>
            <h2 id="task-detail-title" className="font-display text-lg font-semibold text-foreground">
              {task.title}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="shrink-0 rounded-md px-2 py-1 text-foreground-muted transition hover:bg-background-elevated-2 hover:text-foreground"
          >
            ✕
          </button>
        </div>

        <div className="flex flex-col gap-4 text-sm">
          {task.details.description && (
            <p className="leading-relaxed text-foreground">{task.details.description}</p>
          )}

          {task.details.key_points.length > 0 && (
            <ul className="flex list-disc flex-col gap-1 pl-5 text-foreground">
              {task.details.key_points.map((point, i) => (
                <li key={i}>{point}</li>
              ))}
            </ul>
          )}

          <dl className="flex flex-col gap-2 text-xs">
            {task.details.location && (
              <div className="flex gap-2">
                <dt className="w-20 shrink-0 text-foreground-muted">Location</dt>
                <dd className="text-foreground">{task.details.location}</dd>
              </div>
            )}
            {task.details.link && (
              <div className="flex gap-2">
                <dt className="w-20 shrink-0 text-foreground-muted">Link</dt>
                <dd className="truncate">
                  {linkHref ? (
                    <a
                      href={linkHref}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent-signal underline underline-offset-2"
                    >
                      {task.details.link}
                    </a>
                  ) : (
                    task.details.link
                  )}
                </dd>
              </div>
            )}
            {task.due_date && (
              <div className="flex gap-2">
                <dt className="w-20 shrink-0 text-foreground-muted">Due</dt>
                <dd suppressHydrationWarning className="text-foreground">
                  {new Date(task.due_date).toLocaleDateString()}
                </dd>
              </div>
            )}
            {(task.reel_url || task.reel_caption) && (
              <div className="flex gap-2">
                <dt className="w-20 shrink-0 text-foreground-muted">Reel</dt>
                <dd className="truncate">
                  {reelHref ? (
                    <a
                      href={reelHref}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-accent-signal underline underline-offset-2"
                    >
                      {task.reel_caption || "View reel"}
                    </a>
                  ) : (
                    task.reel_caption
                  )}
                </dd>
              </div>
            )}
            <div className="flex gap-2">
              <dt className="w-20 shrink-0 text-foreground-muted">Created</dt>
              <dd suppressHydrationWarning className="text-foreground">
                {new Date(task.created_at).toLocaleString()}
              </dd>
            </div>
          </dl>
        </div>

        <div className="flex items-center gap-2 border-t border-border pt-4">
          <span className="text-xs uppercase tracking-widest text-foreground-muted">Status</span>
          <TaskStatusSelect taskId={task.id} initialStatus={task.status} />
        </div>
      </div>
    </div>
  );
}
