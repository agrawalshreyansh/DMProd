"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";

export default function GeminiKeyForm({
  initiallyConnected,
}: {
  initiallyConnected: boolean;
}) {
  const router = useRouter();
  const [apiKey, setApiKey] = useState("");
  const [connected, setConnected] = useState(initiallyConnected);
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

    setConnected(true);
    setApiKey("");
    router.refresh();
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-gray-600">
        Gemini API key:{" "}
        <span className={connected ? "text-green-700" : "text-gray-500"}>
          {connected ? "●●●● saved" : "not connected"}
        </span>
      </p>
      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          type="password"
          placeholder="Paste your Gemini API key"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          required
          className="flex-1 rounded border px-3 py-2"
        />
        <button
          type="submit"
          disabled={saving}
          className="rounded bg-black px-3 py-2 text-white disabled:opacity-50"
        >
          {saving ? "Saving..." : "Save"}
        </button>
      </form>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}
