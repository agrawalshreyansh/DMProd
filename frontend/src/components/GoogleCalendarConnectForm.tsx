"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

export default function GoogleCalendarConnectForm({
  initiallyConnected,
  initialCalendarSummary,
}: {
  initiallyConnected: boolean;
  initialCalendarSummary: string | null;
}) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [connected, setConnected] = useState(initiallyConnected);
  const [calendarSummary, setCalendarSummary] = useState(initialCalendarSummary);
  const [disconnecting, setDisconnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const connectFailed = searchParams.get("google_error") !== null;

  async function onDisconnect() {
    setDisconnecting(true);
    setError(null);

    const res = await fetch("/api/google-calendar", { method: "DELETE" });

    setDisconnecting(false);
    if (!res.ok) {
      setError("Could not disconnect Google Calendar.");
      return;
    }

    setConnected(false);
    setCalendarSummary(null);
    router.refresh();
  }

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-border bg-background-elevated p-6">
      <div className="flex items-center gap-2 text-sm">
        <span className="text-foreground-muted">Google Calendar</span>
        <span
          className={
            connected
              ? "flex items-center gap-1.5 font-medium text-accent-signal"
              : "font-medium text-foreground-muted"
          }
        >
          {connected && <span className="h-1.5 w-1.5 rounded-full bg-accent-signal" />}
          {connected ? calendarSummary ?? "Connected" : "Not connected"}
        </span>
      </div>

      {connected ? (
        <button
          type="button"
          onClick={onDisconnect}
          disabled={disconnecting}
          className="self-start rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground transition hover:bg-background-elevated-2 disabled:opacity-50"
        >
          {disconnecting ? "Disconnecting..." : "Disconnect"}
        </button>
      ) : (
        <a
          href="/api/google-calendar/connect"
          className="self-start rounded-md bg-accent-signal px-4 py-2 font-medium text-background transition hover:brightness-110"
        >
          Connect Google Calendar
        </a>
      )}
      {(error || connectFailed) && (
        <p className="text-sm text-accent-warm">
          {error ?? "Could not connect Google Calendar. Please try again."}
        </p>
      )}
    </div>
  );
}
