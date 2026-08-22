import { getToken } from "@/lib/session";
import { backendFetch } from "@/lib/api";
import GeminiKeyForm from "@/components/GeminiKeyForm";

export default async function SettingsPage() {
  const token = await getToken();
  const res = await backendFetch("/api/v1/settings/gemini-key", {}, token);
  const { connected } = await res.json();

  return (
    <div className="flex max-w-md flex-col gap-4">
      <h1 className="font-display text-xl font-semibold">Settings</h1>
      <GeminiKeyForm initiallyConnected={connected} />
    </div>
  );
}
