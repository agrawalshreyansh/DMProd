import DashboardPageHeader from "@/components/DashboardPageHeader";
import { getToken } from "@/lib/session";
import { backendFetch } from "@/lib/api";
import InstagramConnect from "@/components/InstagramConnect";

export default async function InstagramAccountPage() {
  const token = await getToken();
  const res = await backendFetch("/api/v1/instagram/status", {}, token);
  const { connected, username } = await res.json();

  return (
    <div className="flex max-w-md flex-col gap-4">
      <DashboardPageHeader
        eyebrow="SIG.01"
        title="Instagram Account"
        description="Connect the account you'll DM reels from — we use this to verify a shared reel really came from you before turning it into a task. Works with any account, personal or professional."
      />
      <InstagramConnect initiallyConnected={connected} username={username} />
    </div>
  );
}
