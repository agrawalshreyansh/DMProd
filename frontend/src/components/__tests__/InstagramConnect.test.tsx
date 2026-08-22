import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import InstagramConnect from "@/components/InstagramConnect";

const refresh = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));

beforeEach(() => {
  refresh.mockClear();
  global.fetch = jest.fn();
});

afterEach(() => {
  jest.useRealTimers();
});

test("shows a connect button when not connected", () => {
  render(<InstagramConnect initiallyConnected={false} username={null} />);
  expect(screen.getByText("Not connected")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /connect instagram/i })).toBeInTheDocument();
});

test("shows the connected username and a disconnect button", () => {
  render(<InstagramConnect initiallyConnected={true} username="alex" />);
  expect(screen.getByText("Connected as @alex")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /disconnect/i })).toBeInTheDocument();
});

test("generating a code shows it", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ code: "AB12CD", expires_at: "2026-08-23T00:15:00Z" }),
  });

  render(<InstagramConnect initiallyConnected={false} username={null} />);
  await userEvent.click(screen.getByRole("button", { name: /connect instagram/i }));

  expect(screen.getByText("AB12CD")).toBeInTheDocument();
  expect(global.fetch).toHaveBeenCalledWith("/api/instagram/connect", { method: "POST" });
});

test("polling flips to connected once the backend reports it", async () => {
  jest.useFakeTimers();
  const user = userEvent.setup({ delay: null, advanceTimers: jest.advanceTimersByTime });

  (global.fetch as jest.Mock)
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ code: "AB12CD", expires_at: "2026-08-23T00:15:00Z" }),
    })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ connected: true, username: "alex" }) });

  render(<InstagramConnect initiallyConnected={false} username={null} />);
  await user.click(screen.getByRole("button", { name: /connect instagram/i }));

  await act(async () => {
    jest.advanceTimersByTime(3000);
    await Promise.resolve();
  });

  // username comes from the server-fetched prop, not client state — a real
  // router.refresh() would re-fetch it, but that's mocked out here, so only
  // the connected flag (driven by our own poll) is observable in this test.
  expect(await screen.findByText("Connected")).toBeInTheDocument();
  expect(refresh).toHaveBeenCalled();
});

test("disconnecting calls the API and flips back to not connected", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({ ok: true });

  render(<InstagramConnect initiallyConnected={true} username="alex" />);
  await userEvent.click(screen.getByRole("button", { name: /disconnect/i }));

  expect(await screen.findByText("Not connected")).toBeInTheDocument();
  expect(global.fetch).toHaveBeenCalledWith("/api/instagram", { method: "DELETE" });
  expect(refresh).toHaveBeenCalled();
});
