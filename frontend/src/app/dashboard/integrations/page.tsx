import { getToken } from "@/lib/session";
import { backendFetch, requireJson } from "@/lib/api";
import NotionConnectForm from "@/components/NotionConnectForm";

type NotionStatus = {
  connected: boolean;
  database_id: string | null;
  database_title: string | null;
};

export default async function IntegrationsPage() {
  const token = await getToken();
  const res = await backendFetch("/api/v1/integrations/notion", {}, token);
  const notion = await requireJson<NotionStatus>(res);

  return (
    <div className="flex max-w-md flex-col gap-4">
      <h1 className="font-display text-xl font-semibold">Integrations</h1>
      <p className="text-sm leading-relaxed text-foreground-muted">
        Connect a destination, then set up routing in{" "}
        <span className="text-foreground">Preferences</span> to push tasks
        there automatically.
      </p>
      <NotionConnectForm
        initiallyConnected={notion.connected}
        initialDatabaseTitle={notion.database_title}
      />
    </div>
  );
}
