import { getToken } from "@/lib/session";
import { backendFetch } from "@/lib/api";
import InstagramConnect from "@/components/InstagramConnect";

export default async function InstagramAccountPage() {
  const token = await getToken();
  const res = await backendFetch("/api/v1/instagram/status", {}, token);
  const { connected, username } = await res.json();

  return (
    <div className="flex max-w-md flex-col gap-4">
      <h1 className="font-display text-xl font-semibold">Instagram Account</h1>
      <p className="text-sm leading-relaxed text-foreground-muted">
        Connect the Instagram account you&apos;ll DM reels from — we use this
        to verify a shared reel really came from you before turning it into
        a task. Works with any account, personal or professional.
      </p>
      <InstagramConnect initiallyConnected={connected} username={username} />
    </div>
  );
}
