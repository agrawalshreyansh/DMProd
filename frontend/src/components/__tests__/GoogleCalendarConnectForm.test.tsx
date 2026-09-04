import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import GoogleCalendarConnectForm from "@/components/GoogleCalendarConnectForm";

const refresh = jest.fn();
let searchParams = new URLSearchParams();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
  useSearchParams: () => searchParams,
}));

beforeEach(() => {
  refresh.mockClear();
  searchParams = new URLSearchParams();
  global.fetch = jest.fn();
});

test("shows a connect link when not connected", () => {
  render(<GoogleCalendarConnectForm initiallyConnected={false} initialCalendarSummary={null} />);
  expect(screen.getByText("Not connected")).toBeInTheDocument();
  const link = screen.getByRole("link", { name: /connect google calendar/i });
  expect(link).toHaveAttribute("href", "/api/google-calendar/connect");
});

test("shows the connected calendar and a disconnect button when already connected", () => {
  render(
    <GoogleCalendarConnectForm initiallyConnected={true} initialCalendarSummary="Personal" />,
  );
  expect(screen.getByText("Personal")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /disconnect/i })).toBeInTheDocument();
});

test("shows an error banner when redirected back with google_error", () => {
  searchParams = new URLSearchParams("google_error=1");
  render(<GoogleCalendarConnectForm initiallyConnected={false} initialCalendarSummary={null} />);
  expect(screen.getByText(/could not connect google calendar/i)).toBeInTheDocument();
});

test("disconnecting calls DELETE and reverts to the connect link", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({ ok: true, json: async () => ({}) });

  render(<GoogleCalendarConnectForm initiallyConnected={true} initialCalendarSummary="Personal" />);
  await userEvent.click(screen.getByRole("button", { name: /disconnect/i }));

  expect(global.fetch).toHaveBeenCalledWith(
    "/api/google-calendar",
    expect.objectContaining({ method: "DELETE" }),
  );
  expect(await screen.findByText("Not connected")).toBeInTheDocument();
});
