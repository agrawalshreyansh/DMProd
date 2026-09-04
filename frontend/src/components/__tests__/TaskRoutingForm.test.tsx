import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TaskRoutingForm from "@/components/TaskRoutingForm";

const refresh = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));

beforeEach(() => {
  refresh.mockClear();
  global.fetch = jest.fn();
});

test("shows the destination already routed for each task type", () => {
  render(
    <TaskRoutingForm
      initialRouting={{ action_item: "notion", event_reminder: "google_calendar", content_idea: null }}
    />,
  );
  expect(screen.getByRole("combobox", { name: /action item/i })).toHaveValue("notion");
  expect(screen.getByRole("combobox", { name: /event reminder/i })).toHaveValue("google_calendar");
  expect(screen.getByRole("combobox", { name: /content idea/i })).toHaveValue("");
});

test("selecting a destination saves the full updated routing and refreshes", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({ ok: true, json: async () => ({}) });

  render(<TaskRoutingForm initialRouting={{ action_item: null, content_idea: "notion" }} />);
  await userEvent.selectOptions(
    screen.getByRole("combobox", { name: /action item/i }),
    "google_calendar",
  );

  expect(global.fetch).toHaveBeenCalledWith(
    "/api/preferences",
    expect.objectContaining({
      method: "PUT",
      body: JSON.stringify({
        task_type_routing: { action_item: "google_calendar", content_idea: "notion" },
      }),
    }),
  );
  expect(refresh).toHaveBeenCalled();
});

test("selecting Don't push routes that task type to null", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({ ok: true, json: async () => ({}) });

  render(<TaskRoutingForm initialRouting={{ action_item: "notion" }} />);
  await userEvent.selectOptions(screen.getByRole("combobox", { name: /action item/i }), "");

  expect(global.fetch).toHaveBeenCalledWith(
    "/api/preferences",
    expect.objectContaining({
      body: JSON.stringify({ task_type_routing: { action_item: null } }),
    }),
  );
});

test("reverts the selection and shows an error if saving fails", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({ ok: false, json: async () => ({}) });

  render(<TaskRoutingForm initialRouting={{ action_item: null }} />);
  await userEvent.selectOptions(screen.getByRole("combobox", { name: /action item/i }), "notion");

  expect(await screen.findByText(/could not save routing/i)).toBeInTheDocument();
  expect(screen.getByRole("combobox", { name: /action item/i })).toHaveValue("");
  expect(refresh).not.toHaveBeenCalled();
});
