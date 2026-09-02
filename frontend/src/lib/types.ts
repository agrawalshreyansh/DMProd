export type Task = {
  id: string;
  task_type: string;
  title: string;
  details: {
    description: string | null;
    location: string | null;
    link: string | null;
    key_points: string[];
  };
  due_date: string | null;
  status: string;
  reel_url: string | null;
  reel_caption: string | null;
  created_at: string;
};

export const TASK_TYPE_LABELS: Record<string, string> = {
  content_idea: "Content idea",
  action_item: "Action item",
  event_reminder: "Event reminder",
  resource_reference: "Resource",
  other: "Other",
};
