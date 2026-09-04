import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CalendarSchedulingForm from "@/components/CalendarSchedulingForm";

const refresh = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));

const initial = {
  days_of_week: [0, 1, 2, 3, 4],
  start_time: "09:00",
  end_time: "18:00",
  event_duration_minutes: 30,
  timezone: "UTC",
};

beforeEach(() => {
  refresh.mockClear();
  global.fetch = jest.fn();
});

test("renders the initial days as selected", () => {
  render(<CalendarSchedulingForm initial={initial} />);
  expect(screen.getByRole("button", { name: "Mon" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByRole("button", { name: "Sat" })).toHaveAttribute("aria-pressed", "false");
});

test("toggling a day and saving sends the full updated preference", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({ ok: true, json: async () => ({}) });

  render(<CalendarSchedulingForm initial={initial} />);
  await userEvent.click(screen.getByRole("button", { name: "Sat" }));
  await userEvent.click(screen.getByRole("button", { name: /^save$/i }));

  expect(global.fetch).toHaveBeenCalledWith(
    "/api/preferences",
    expect.objectContaining({
      method: "PUT",
      body: JSON.stringify({
        calendar_scheduling: { ...initial, days_of_week: [0, 1, 2, 3, 4, 5] },
      }),
    }),
  );
  expect(refresh).toHaveBeenCalled();
});

test("shows the backend's error message when saving fails", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: false,
    json: async () => ({ detail: "start_time must be before end_time." }),
  });

  render(<CalendarSchedulingForm initial={initial} />);
  await userEvent.click(screen.getByRole("button", { name: /^save$/i }));

  expect(await screen.findByText("start_time must be before end_time.")).toBeInTheDocument();
  expect(refresh).not.toHaveBeenCalled();
});
