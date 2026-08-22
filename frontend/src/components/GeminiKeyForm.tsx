"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

export default function GeminiKeyForm({
  initiallyConnected,
  initialMaskedKey,
}: {
  initiallyConnected: boolean;
  initialMaskedKey: string | null;
}) {
  const router = useRouter();
  const [apiKey, setApiKey] = useState("");
  const [connected, setConnected] = useState(initiallyConnected);
  const [maskedKey, setMaskedKey] = useState(initialMaskedKey);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);

    const res = await fetch("/api/settings/gemini-key", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ api_key: apiKey }),
    });

    setSaving(false);

    if (!res.ok) {
      setError("Could not save key. Please try again.");
      return;
    }

    const body = await res.json();
    setConnected(true);
    setMaskedKey(body.masked_key);
    setApiKey("");
    router.refresh();
  }

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-border bg-background-elevated p-6">
      <div className="flex items-center gap-2 text-sm">
        <span className="text-foreground-muted">Gemini API key</span>
        <span
          className={
            connected
              ? "flex items-center gap-1.5 font-medium text-accent-signal"
              : "font-medium text-foreground-muted"
          }
        >
          {connected && <span className="h-1.5 w-1.5 rounded-full bg-accent-signal" />}
          {connected && maskedKey ? maskedKey : connected ? "Connected" : "Not connected"}
        </span>
      </div>
      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          type="password"
          placeholder={connected ? "Enter a new key to replace it" : "Paste your Gemini API key"}
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          required
          className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-foreground placeholder:text-foreground-muted outline-none focus:border-accent-signal focus:ring-1 focus:ring-accent-signal"
        />
        <button
          type="submit"
          disabled={saving}
          className="rounded-md bg-accent-signal px-4 py-2 font-medium text-background transition hover:brightness-110 disabled:opacity-50"
        >
          {saving ? "Saving..." : connected ? "Replace" : "Save"}
        </button>
      </form>
      {error && <p className="text-sm text-accent-warm">{error}</p>}
    </div>
  );
}
