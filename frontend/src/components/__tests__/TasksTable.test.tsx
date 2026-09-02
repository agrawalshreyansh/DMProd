import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TasksTable from "@/components/TasksTable";
import type { Task } from "@/lib/types";

jest.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: jest.fn() }),
}));

beforeEach(() => {
  global.fetch = jest.fn();
});

const task: Task = {
  id: "task-1",
  task_type: "action_item",
  title: "Go to the gym",
  details: {
    description: "Start going to the gym",
    location: "Downtown gym",
    link: "https://example.com/gym",
    key_points: ["Warm up first", "Track progress weekly"],
  },
  due_date: "2026-09-01",
  status: "not_started",
  reel_url: "https://instagram.com/reel/abc",
  reel_caption: "gym motivation",
  created_at: "2026-08-24T00:00:00Z",
};

test("clicking a row opens a modal with the full task details", async () => {
  render(<TasksTable tasks={[task]} />);
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();

  await userEvent.click(screen.getByText("Go to the gym"));

  const dialog = screen.getByRole("dialog");
  expect(dialog).toBeInTheDocument();
  expect(within(dialog).getByText("Start going to the gym")).toBeInTheDocument();
  expect(within(dialog).getByText("Warm up first")).toBeInTheDocument();
  expect(within(dialog).getByText("Downtown gym")).toBeInTheDocument();
});

test("closing the modal via the close button removes it", async () => {
  render(<TasksTable tasks={[task]} />);
  await userEvent.click(screen.getByText("Go to the gym"));
  expect(screen.getByRole("dialog")).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: /close/i }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

test("closing the modal via Escape removes it", async () => {
  render(<TasksTable tasks={[task]} />);
  await userEvent.click(screen.getByText("Go to the gym"));
  expect(screen.getByRole("dialog")).toBeInTheDocument();

  await userEvent.keyboard("{Escape}");
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

test("clicking the reel link in the row does not open the modal", async () => {
  render(<TasksTable tasks={[task]} />);
  await userEvent.click(screen.getByRole("link", { name: /gym motivation/i }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

test("a javascript: URI in reel_url or details.link is never rendered as a clickable link", async () => {
  const malicious: Task = {
    ...task,
    reel_url: "javascript:alert(document.cookie)",
    details: { ...task.details, link: "javascript:alert(document.cookie)" },
  };
  render(<TasksTable tasks={[malicious]} />);

  // Row: reel_url falls back to plain text, not an anchor.
  expect(screen.queryByRole("link", { name: /gym motivation/i })).not.toBeInTheDocument();
  expect(screen.getByText("gym motivation")).toBeInTheDocument();

  // Modal: details.link falls back to plain text too.
  await userEvent.click(screen.getByText("Go to the gym"));
  const dialog = screen.getByRole("dialog");
  expect(within(dialog).queryByRole("link", { name: /javascript:/i })).not.toBeInTheDocument();
  expect(within(dialog).getByText("javascript:alert(document.cookie)")).toBeInTheDocument();
});
