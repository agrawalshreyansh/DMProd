import { getToken } from "@/lib/session";
import { backendFetch } from "@/lib/api";

type Reel = {
  id: string;
  url: string | null;
  caption: string | null;
  received_at: string;
};

export default async function HistoryPage() {
  const token = await getToken();
  const res = await backendFetch("/api/v1/reels", {}, token);
  const reels: Reel[] = await res.json();

  return (
    <div className="flex max-w-2xl flex-col gap-4">
      <h1 className="font-display text-xl font-semibold">History</h1>

      {reels.length === 0 ? (
        <p className="text-sm leading-relaxed text-foreground-muted">
          No reels yet. Connect your Instagram account in{" "}
          <span className="text-foreground">Instagram Account</span>, then DM
          the bot a reel — it&apos;ll show up here.
        </p>
      ) : (
        <ul className="flex flex-col gap-3">
          {reels.map((reel) => (
            <li
              key={reel.id}
              className="flex flex-col gap-2 rounded-lg border border-border bg-background-elevated p-4"
            >
              <p className="text-sm leading-relaxed text-foreground">
                {reel.caption || "No caption"}
              </p>
              <div className="flex items-center justify-between text-xs text-foreground-muted">
                <span className="font-mono">
                  {new Date(reel.received_at).toLocaleString()}
                </span>
                {reel.url && (
                  <a
                    href={reel.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-accent-signal underline underline-offset-2"
                  >
                    View reel
                  </a>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
