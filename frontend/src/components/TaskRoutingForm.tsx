"use client";

import { useState, type ChangeEvent } from "react";
import { useRouter } from "next/navigation";
import { TASK_TYPE_LABELS } from "@/lib/types";

const TASK_TYPES = Object.keys(TASK_TYPE_LABELS);

const ROUTE_OPTIONS = [
  { value: "", label: "Don't push" },
  { value: "notion", label: "Notion" },
  { value: "google_calendar", label: "Google Calendar" },
] as const;

export default function TaskRoutingForm({
  initialRouting,
}: {
  initialRouting: Record<string, string | null>;
}) {
  const router = useRouter();
  const [routing, setRouting] = useState(initialRouting);
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onChange(taskType: string, e: ChangeEvent<HTMLSelectElement>) {
    const value = e.target.value || null;
    const previous = routing;
    const next = { ...routing, [taskType]: value };
    setRouting(next);
    setSaving(taskType);
    setError(null);

    const res = await fetch("/api/preferences", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_type_routing: next }),
    });

    setSaving(null);

    if (!res.ok) {
      setRouting(previous);
      setError("Could not save routing.");
      return;
    }

    router.refresh();
  }

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-border bg-background-elevated p-6">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-foreground-muted">
            <th className="pb-2 font-medium">Task type</th>
            <th className="pb-2 font-medium">Push to</th>
          </tr>
        </thead>
        <tbody>
          {TASK_TYPES.map((taskType) => (
            <tr key={taskType} className="border-t border-border">
              <td className="py-2 text-foreground">{TASK_TYPE_LABELS[taskType]}</td>
              <td className="py-2">
                <select
                  aria-label={`Where to push ${TASK_TYPE_LABELS[taskType]}`}
                  value={routing[taskType] ?? ""}
                  disabled={saving === taskType}
                  onChange={(e) => onChange(taskType, e)}
                  className="rounded-md border border-border bg-background px-2 py-1 text-foreground outline-none focus:border-accent-signal focus:ring-1 focus:ring-accent-signal disabled:opacity-50"
                >
                  {ROUTE_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {error && <p className="text-sm text-accent-warm">{error}</p>}
    </div>
  );
}
