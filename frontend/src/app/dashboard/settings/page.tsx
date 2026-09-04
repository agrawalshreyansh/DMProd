import DashboardPageHeader from "@/components/DashboardPageHeader";
import { getToken } from "@/lib/session";
import { backendFetch } from "@/lib/api";
import GeminiKeyForm from "@/components/GeminiKeyForm";

export default async function SettingsPage() {
  const token = await getToken();
  const res = await backendFetch("/api/v1/settings/gemini-key", {}, token);
  const { connected, masked_key } = await res.json();

  return (
    <div className="flex max-w-md flex-col gap-4">
      <DashboardPageHeader
        eyebrow="SIG.07"
        title="Settings"
        description="Your own Gemini API key — used to structure every reel you share, never shared across users."
      />
      <GeminiKeyForm initiallyConnected={connected} initialMaskedKey={masked_key ?? null} />
    </div>
  );
}
