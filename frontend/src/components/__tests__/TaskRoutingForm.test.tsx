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

test("checks the box for task types already routed to notion", () => {
  render(<TaskRoutingForm initialRouting={{ action_item: "notion", content_idea: null }} />);
  expect(screen.getByRole("checkbox", { name: /action item/i })).toBeChecked();
  expect(screen.getByRole("checkbox", { name: /content idea/i })).not.toBeChecked();
});

test("checking a box saves the full updated routing and refreshes", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({ ok: true, json: async () => ({}) });

  render(<TaskRoutingForm initialRouting={{ action_item: null, content_idea: "notion" }} />);
  await userEvent.click(screen.getByRole("checkbox", { name: /action item/i }));

  expect(global.fetch).toHaveBeenCalledWith(
    "/api/preferences",
    expect.objectContaining({
      method: "PUT",
      body: JSON.stringify({
        task_type_routing: { action_item: "notion", content_idea: "notion" },
      }),
    }),
  );
  expect(refresh).toHaveBeenCalled();
});

test("unchecking a box routes that task type to null", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({ ok: true, json: async () => ({}) });

  render(<TaskRoutingForm initialRouting={{ action_item: "notion" }} />);
  await userEvent.click(screen.getByRole("checkbox", { name: /action item/i }));

  expect(global.fetch).toHaveBeenCalledWith(
    "/api/preferences",
    expect.objectContaining({
      body: JSON.stringify({ task_type_routing: { action_item: null } }),
    }),
  );
});

test("reverts the checkbox and shows an error if saving fails", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({ ok: false, json: async () => ({}) });

  render(<TaskRoutingForm initialRouting={{ action_item: null }} />);
  await userEvent.click(screen.getByRole("checkbox", { name: /action item/i }));

  expect(await screen.findByText(/could not save routing/i)).toBeInTheDocument();
  expect(screen.getByRole("checkbox", { name: /action item/i })).not.toBeChecked();
  expect(refresh).not.toHaveBeenCalled();
});
