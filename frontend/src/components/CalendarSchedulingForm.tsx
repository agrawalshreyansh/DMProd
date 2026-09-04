"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export type CalendarScheduling = {
  days_of_week: number[];
  start_time: string;
  end_time: string;
  event_duration_minutes: number;
  timezone: string;
};

const DAYS = [
  { value: 0, label: "Mon" },
  { value: 1, label: "Tue" },
  { value: 2, label: "Wed" },
  { value: 3, label: "Thu" },
  { value: 4, label: "Fri" },
  { value: 5, label: "Sat" },
  { value: 6, label: "Sun" },
];

export default function CalendarSchedulingForm({ initial }: { initial: CalendarScheduling }) {
  const router = useRouter();
  const [form, setForm] = useState(initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggleDay(day: number) {
    setForm((f) => ({
      ...f,
      days_of_week: f.days_of_week.includes(day)
        ? f.days_of_week.filter((d) => d !== day)
        : [...f.days_of_week, day].sort((a, b) => a - b),
    }));
  }

  async function onSave() {
    setSaving(true);
    setError(null);

    const res = await fetch("/api/preferences", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ calendar_scheduling: form }),
    });

    setSaving(false);
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      setError(typeof body.detail === "string" ? body.detail : "Could not save.");
      return;
    }
    router.refresh();
  }

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-border bg-background-elevated p-6">
      <div>
        <h2 className="text-sm font-medium text-foreground">Calendar scheduling</h2>
        <p className="mt-1 text-sm leading-relaxed text-foreground-muted">
          When a task is pushed to Google Calendar, it only lands on these
          days and within this time window — checked against your real
          calendar so it won&apos;t land on top of something else.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {DAYS.map((day) => (
          <button
            key={day.value}
            type="button"
            onClick={() => toggleDay(day.value)}
            aria-pressed={form.days_of_week.includes(day.value)}
            className={
              form.days_of_week.includes(day.value)
                ? "rounded-md bg-accent-signal px-3 py-1 text-sm font-medium text-background"
                : "rounded-md border border-border px-3 py-1 text-sm text-foreground-muted transition hover:bg-background-elevated-2"
            }
          >
            {day.label}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-end gap-4 text-sm">
        <label className="flex flex-col gap-1 text-foreground-muted">
          From
          <input
            type="time"
            value={form.start_time}
            onChange={(e) => setForm((f) => ({ ...f, start_time: e.target.value }))}
            className="rounded-md border border-border bg-background px-2 py-1 text-foreground outline-none focus:border-accent-signal focus:ring-1 focus:ring-accent-signal"
          />
        </label>
        <label className="flex flex-col gap-1 text-foreground-muted">
          To
          <input
            type="time"
            value={form.end_time}
            onChange={(e) => setForm((f) => ({ ...f, end_time: e.target.value }))}
            className="rounded-md border border-border bg-background px-2 py-1 text-foreground outline-none focus:border-accent-signal focus:ring-1 focus:ring-accent-signal"
          />
        </label>
        <label className="flex flex-col gap-1 text-foreground-muted">
          Event length (min)
          <input
            type="number"
            min={5}
            max={480}
            value={form.event_duration_minutes}
            onChange={(e) =>
              setForm((f) => ({ ...f, event_duration_minutes: Number(e.target.value) }))
            }
            className="w-24 rounded-md border border-border bg-background px-2 py-1 text-foreground outline-none focus:border-accent-signal focus:ring-1 focus:ring-accent-signal"
          />
        </label>
        <label className="flex flex-col gap-1 text-foreground-muted">
          Timezone
          <input
            type="text"
            value={form.timezone}
            onChange={(e) => setForm((f) => ({ ...f, timezone: e.target.value }))}
            placeholder="e.g. Asia/Kolkata"
            className="w-40 rounded-md border border-border bg-background px-2 py-1 text-foreground placeholder:text-foreground-muted outline-none focus:border-accent-signal focus:ring-1 focus:ring-accent-signal"
          />
        </label>
      </div>

      <button
        type="button"
        onClick={onSave}
        disabled={saving}
        className="self-start rounded-md bg-accent-signal px-4 py-2 text-sm font-medium text-background transition hover:brightness-110 disabled:opacity-50"
      >
        {saving ? "Saving..." : "Save"}
      </button>
      {error && <p className="text-sm text-accent-warm">{error}</p>}
    </div>
  );
}
