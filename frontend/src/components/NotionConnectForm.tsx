"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

export default function NotionConnectForm({
  initiallyConnected,
  initialDatabaseTitle,
}: {
  initiallyConnected: boolean;
  initialDatabaseTitle: string | null;
}) {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [databaseId, setDatabaseId] = useState("");
  const [connected, setConnected] = useState(initiallyConnected);
  const [databaseTitle, setDatabaseTitle] = useState(initialDatabaseTitle);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);

    const res = await fetch("/api/integrations/notion", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, database_id: databaseId }),
    });

    const body = await res.json();
    setSaving(false);

    if (!res.ok) {
      setError(typeof body.detail === "string" ? body.detail : "Could not connect to Notion.");
      return;
    }

    setConnected(true);
    setDatabaseTitle(body.database_title ?? null);
    setToken("");
    setDatabaseId("");
    router.refresh();
  }

  async function onDisconnect() {
    setSaving(true);
    setError(null);

    const res = await fetch("/api/integrations/notion", { method: "DELETE" });

    setSaving(false);
    if (!res.ok) {
      setError("Could not disconnect Notion.");
      return;
    }

    setConnected(false);
    setDatabaseTitle(null);
    router.refresh();
  }

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-border bg-background-elevated p-6">
      <div className="flex items-center gap-2 text-sm">
        <span className="text-foreground-muted">Notion</span>
        <span
          className={
            connected
              ? "flex items-center gap-1.5 font-medium text-accent-signal"
              : "font-medium text-foreground-muted"
          }
        >
          {connected && <span className="h-1.5 w-1.5 rounded-full bg-accent-signal" />}
          {connected ? databaseTitle ?? "Connected" : "Not connected"}
        </span>
      </div>

      {connected ? (
        <button
          type="button"
          onClick={onDisconnect}
          disabled={saving}
          className="self-start rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground transition hover:bg-background-elevated-2 disabled:opacity-50"
        >
          {saving ? "Disconnecting..." : "Disconnect"}
        </button>
      ) : (
        <form onSubmit={onSubmit} className="flex flex-col gap-2">
          <input
            type="password"
            placeholder="Paste your Notion integration token"
            value={token}
            onChange={(e) => setToken(e.target.value)}
            required
            className="rounded-md border border-border bg-background px-3 py-2 text-foreground placeholder:text-foreground-muted outline-none focus:border-accent-signal focus:ring-1 focus:ring-accent-signal"
          />
          <input
            type="text"
            placeholder="Database ID (shared with the integration)"
            value={databaseId}
            onChange={(e) => setDatabaseId(e.target.value)}
            required
            className="rounded-md border border-border bg-background px-3 py-2 text-foreground placeholder:text-foreground-muted outline-none focus:border-accent-signal focus:ring-1 focus:ring-accent-signal"
          />
          <button
            type="submit"
            disabled={saving}
            className="self-start rounded-md bg-accent-signal px-4 py-2 font-medium text-background transition hover:brightness-110 disabled:opacity-50"
          >
            {saving ? "Connecting..." : "Connect"}
          </button>
        </form>
      )}
      {error && <p className="text-sm text-accent-warm">{error}</p>}
    </div>
  );
}
