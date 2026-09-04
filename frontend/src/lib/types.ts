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

export type ReelOutcome = "failed" | "processing" | "not_started" | "in_progress" | "completed";

export const OUTCOME_LABELS: Record<ReelOutcome, string> = {
  failed: "Failed",
  processing: "Processing",
  not_started: "Not started",
  in_progress: "In progress",
  completed: "Completed",
};

export type Reel = {
  id: string;
  url: string | null;
  caption: string | null;
  received_at: string;
  reel_status: string;
  error_message: string | null;
  visual_processing_status: string | null;
  task_generation_status: string;
  task: { id: string; task_type: string; title: string; status: string } | null;
  push: { integration_type: string; external_ref_url: string } | null;
  outcome: ReelOutcome;
};

export type VisualEvent = {
  timestamp_seconds: number;
  description: string;
  on_screen_text: string | null;
};

export type PushLogEntry = {
  integration_type: string;
  status: string;
  external_ref_url: string | null;
  error_message: string | null;
  pushed_at: string;
};

export type ReelDetail = Reel & {
  transcript_text: string | null;
  transcript_language: string | null;
  visual_summary: string | null;
  visual_events: VisualEvent[];
  comment_unlock_status: string | null;
  task_generation_error: string | null;
  title: string | null;
  details: Task["details"] | null;
  task_status: string | null;
  push_logs: PushLogEntry[];
};

export type Stats = {
  total_reels: number;
  reels_this_week: number;
  reels_this_month: number;
  reels_succeeded: number;
  reels_failed: number;
  reels_processing: number;
  by_task_type: { label: string; count: number }[];
  by_destination: { label: string; count: number }[];
};
