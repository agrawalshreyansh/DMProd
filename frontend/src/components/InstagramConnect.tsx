"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

export default function InstagramConnect({
  initiallyConnected,
  username,
}: {
  initiallyConnected: boolean;
  username: string | null;
}) {
  const router = useRouter();
  const [connected, setConnected] = useState(initiallyConnected);
  const [code, setCode] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  async function onGenerate() {
    setGenerating(true);
    setError(null);

    const res = await fetch("/api/instagram/connect", { method: "POST" });
    setGenerating(false);

    if (!res.ok) {
      setError("Couldn't generate a code. Try again.");
      return;
    }

    const body = await res.json();
    setCode(body.code);
    setExpiresAt(body.expires_at);

    pollRef.current = setInterval(async () => {
      const statusRes = await fetch("/api/instagram/status");
      if (!statusRes.ok) return;
      const status = await statusRes.json();
      if (status.connected) {
        if (pollRef.current) clearInterval(pollRef.current);
        setConnected(true);
        setCode(null);
        router.refresh();
      }
    }, 3000);
  }

  async function onDisconnect() {
    setDisconnecting(true);
    const res = await fetch("/api/instagram", { method: "DELETE" });
    setDisconnecting(false);
    if (res.ok) {
      setConnected(false);
      router.refresh();
    }
  }

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-border bg-background-elevated p-6">
      <div className="flex items-center gap-2 text-sm">
        <span className="text-foreground-muted">Instagram account</span>
        <span
          className={
            connected
              ? "flex items-center gap-1.5 font-medium text-accent-signal"
              : "font-medium text-foreground-muted"
          }
        >
          {connected && <span className="h-1.5 w-1.5 rounded-full bg-accent-signal" />}
          {connected ? (username ? `Connected as @${username}` : "Connected") : "Not connected"}
        </span>
      </div>

      {error && <p className="text-sm text-accent-warm">{error}</p>}

      {connected ? (
        <button
          onClick={onDisconnect}
          disabled={disconnecting}
          className="w-fit rounded-md border border-border px-4 py-2 text-sm font-medium text-foreground-muted transition hover:border-accent-warm hover:text-accent-warm disabled:opacity-50"
        >
          {disconnecting ? "Disconnecting..." : "Disconnect"}
        </button>
      ) : code ? (
        <div className="flex flex-col gap-2">
          <p className="text-sm leading-relaxed text-foreground-muted">
            From the Instagram account you want to connect, DM this code to
            Panda&apos;s Instagram account:
          </p>
          <p className="w-fit rounded-md bg-background px-4 py-2 font-mono text-2xl font-semibold tracking-[0.3em] text-accent-signal">
            {code}
          </p>
          <p className="text-xs text-foreground-muted">
            Expires {expiresAt && new Date(expiresAt).toLocaleTimeString()} — this page updates
            automatically once we see it.
          </p>
        </div>
      ) : (
        <button
          onClick={onGenerate}
          disabled={generating}
          className="w-fit rounded-md bg-accent-signal px-4 py-2 text-sm font-medium text-background transition hover:brightness-110 disabled:opacity-50"
        >
          {generating ? "Generating..." : "Connect Instagram"}
        </button>
      )}
    </div>
  );
}
