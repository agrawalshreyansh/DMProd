"use client";

import { useState, type ChangeEvent } from "react";
import { useRouter } from "next/navigation";

const STATUSES = [
  { value: "not_started", label: "Not started" },
  { value: "in_progress", label: "In progress" },
  { value: "completed", label: "Completed" },
] as const;

export default function TaskStatusSelect({
  taskId,
  initialStatus,
}: {
  taskId: string;
  initialStatus: string;
}) {
  const router = useRouter();
  const [status, setStatus] = useState(initialStatus);
  const [saving, setSaving] = useState(false);

  async function onChange(e: ChangeEvent<HTMLSelectElement>) {
    const next = e.target.value;
    const previous = status;
    setStatus(next);
    setSaving(true);

    const res = await fetch(`/api/tasks/${taskId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: next }),
    });

    setSaving(false);

    if (!res.ok) {
      setStatus(previous);
      return;
    }

    router.refresh();
  }

  return (
    <select
      value={status}
      onChange={onChange}
      disabled={saving}
      className="rounded-md border border-border bg-background px-2 py-1 text-sm text-foreground outline-none focus:border-accent-signal focus:ring-1 focus:ring-accent-signal disabled:opacity-50"
    >
      {STATUSES.map((s) => (
        <option key={s.value} value={s.value}>
          {s.label}
        </option>
      ))}
    </select>
  );
}
