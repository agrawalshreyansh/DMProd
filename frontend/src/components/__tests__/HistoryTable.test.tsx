import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import HistoryTable from "@/components/HistoryTable";
import type { Reel, ReelDetail } from "@/lib/types";

beforeEach(() => {
  global.fetch = jest.fn();
});

const reel: Reel = {
  id: "share-1",
  url: "https://instagram.com/reel/abc",
  caption: "gym motivation",
  received_at: "2026-08-24T00:00:00Z",
  reel_status: "transcribed",
  error_message: null,
  visual_processing_status: "done",
  task_generation_status: "generated",
  task: { id: "task-1", task_type: "action_item", title: "Go to the gym", status: "not_started" },
  push: { integration_type: "notion", external_ref_url: "https://notion.so/abc" },
  outcome: "not_started",
};

const detail: ReelDetail = {
  ...reel,
  transcript_text: "full transcript text",
  transcript_language: "en",
  visual_summary: "[00:01] a gym sign",
  visual_events: [],
  comment_unlock_status: null,
  task_generation_error: null,
  title: "Go to the gym",
  details: { description: "Start going to the gym", location: null, link: "https://example.com/gym", key_points: ["Warm up first"] },
  task_status: "not_started",
  push_logs: [{ integration_type: "notion", status: "success", external_ref_url: "https://notion.so/abc", error_message: null, pushed_at: "2026-08-24T00:00:00Z" }],
};

function mockDetailFetch(body: ReelDetail) {
  (global.fetch as jest.Mock).mockResolvedValueOnce({ ok: true, json: async () => body });
}

test("clicking a row opens a modal and fetches its detail", async () => {
  mockDetailFetch(detail);
  render(<HistoryTable reels={[reel]} />);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

  await userEvent.click(screen.getByText("Go to the gym"));

  expect(global.fetch).toHaveBeenCalledWith("/api/reels/share-1");
  const dialog = await screen.findByRole("dialog");
  expect(within(dialog).getByText("Start going to the gym")).toBeInTheDocument();
  expect(within(dialog).getByText("Warm up first")).toBeInTheDocument();
});

test("closing the modal via Escape removes it", async () => {
  mockDetailFetch(detail);
  render(<HistoryTable reels={[reel]} />);
  await userEvent.click(screen.getByText("Go to the gym"));
  await screen.findByRole("dialog");

  await userEvent.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

test("clicking the reel link in the row does not open the modal", async () => {
  render(<HistoryTable reels={[reel]} />);
  await userEvent.click(screen.getByRole("link", { name: /view reel/i }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(global.fetch).not.toHaveBeenCalled();
});

test("a javascript: URI in reel.url or details.link is never rendered as a clickable link", async () => {
  const malicious: Reel = { ...reel, url: "javascript:alert(document.cookie)" };
  const maliciousDetail: ReelDetail = {
    ...detail,
    url: malicious.url,
    details: { ...detail.details!, link: "javascript:alert(document.cookie)" },
  };
  mockDetailFetch(maliciousDetail);
  render(<HistoryTable reels={[malicious]} />);

  expect(screen.queryByRole("link", { name: /view reel/i })).not.toBeInTheDocument();

  await userEvent.click(screen.getByText("Go to the gym"));
  const dialog = await screen.findByRole("dialog");
  expect(within(dialog).queryByRole("link", { name: /javascript:/i })).not.toBeInTheDocument();
  expect(within(dialog).getByText("javascript:alert(document.cookie)")).toBeInTheDocument();
});

test("shows an error message when the detail fetch fails", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({ ok: false });
  render(<HistoryTable reels={[reel]} />);

  await userEvent.click(screen.getByText("Go to the gym"));
  expect(await screen.findByText(/couldn't load this reel/i)).toBeInTheDocument();
});
