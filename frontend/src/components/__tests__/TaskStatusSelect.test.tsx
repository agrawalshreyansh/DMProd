import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TaskStatusSelect from "@/components/TaskStatusSelect";

const refresh = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));

beforeEach(() => {
  refresh.mockClear();
  global.fetch = jest.fn();
});

test("shows the initial status", () => {
  render(<TaskStatusSelect taskId="task-1" initialStatus="not_started" />);
  expect(screen.getByRole("combobox")).toHaveValue("not_started");
});

test("changing the status patches the backend and refreshes", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({ ok: true, json: async () => ({}) });

  render(<TaskStatusSelect taskId="task-1" initialStatus="not_started" />);
  await userEvent.selectOptions(screen.getByRole("combobox"), "in_progress");

  expect(global.fetch).toHaveBeenCalledWith(
    "/api/tasks/task-1",
    expect.objectContaining({
      method: "PATCH",
      body: JSON.stringify({ status: "in_progress" }),
    }),
  );
  expect(refresh).toHaveBeenCalled();
});

test("reverts the selection if the patch fails", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({ ok: false, json: async () => ({}) });

  render(<TaskStatusSelect taskId="task-1" initialStatus="not_started" />);
  await userEvent.selectOptions(screen.getByRole("combobox"), "completed");

  expect(screen.getByRole("combobox")).toHaveValue("not_started");
  expect(refresh).not.toHaveBeenCalled();
});
