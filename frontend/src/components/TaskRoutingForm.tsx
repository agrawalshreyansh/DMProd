"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { TASK_TYPE_LABELS } from "@/lib/types";

const TASK_TYPES = Object.keys(TASK_TYPE_LABELS);

export default function TaskRoutingForm({
  initialRouting,
}: {
  initialRouting: Record<string, string | null>;
}) {
  const router = useRouter();
  const [routing, setRouting] = useState(initialRouting);
  const [saving, setSaving] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function toggle(taskType: string, checked: boolean) {
    const previous = routing;
    const next = { ...routing, [taskType]: checked ? "notion" : null };
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
            <th className="pb-2 font-medium">Push to Notion</th>
          </tr>
        </thead>
        <tbody>
          {TASK_TYPES.map((taskType) => (
            <tr key={taskType} className="border-t border-border">
              <td className="py-2 text-foreground">{TASK_TYPE_LABELS[taskType]}</td>
              <td className="py-2">
                <input
                  type="checkbox"
                  aria-label={`Push ${TASK_TYPE_LABELS[taskType]} to Notion`}
                  checked={routing[taskType] === "notion"}
                  disabled={saving === taskType}
                  onChange={(e) => toggle(taskType, e.target.checked)}
                  className="h-4 w-4 accent-accent-signal"
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {error && <p className="text-sm text-accent-warm">{error}</p>}
    </div>
  );
}
