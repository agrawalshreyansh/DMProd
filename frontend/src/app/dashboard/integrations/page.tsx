import DashboardPageHeader from "@/components/DashboardPageHeader";
import { getToken } from "@/lib/session";
import { backendFetch, requireJson } from "@/lib/api";
import NotionConnectForm from "@/components/NotionConnectForm";
import GoogleCalendarConnectForm from "@/components/GoogleCalendarConnectForm";

type NotionStatus = {
  connected: boolean;
  database_id: string | null;
  database_title: string | null;
};

type GoogleCalendarStatus = {
  connected: boolean;
  calendar_summary: string | null;
};

export default async function IntegrationsPage() {
  const token = await getToken();
  const [notionRes, gcalRes] = await Promise.all([
    backendFetch("/api/v1/integrations/notion", {}, token),
    backendFetch("/api/v1/integrations/google-calendar", {}, token),
  ]);
  const notion = await requireJson<NotionStatus>(notionRes);
  const gcal = await requireJson<GoogleCalendarStatus>(gcalRes);

  return (
    <div className="flex max-w-md flex-col gap-4">
      <DashboardPageHeader
        eyebrow="SIG.02"
        title="Integrations"
        description={
          "Connect a destination, then set up routing in Preferences to push tasks there automatically."
        }
      />
      <NotionConnectForm
        initiallyConnected={notion.connected}
        initialDatabaseTitle={notion.database_title}
      />
      <GoogleCalendarConnectForm
        initiallyConnected={gcal.connected}
        initialCalendarSummary={gcal.calendar_summary}
      />
    </div>
  );
}
