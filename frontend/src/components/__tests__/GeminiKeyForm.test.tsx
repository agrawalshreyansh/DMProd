import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import GeminiKeyForm from "@/components/GeminiKeyForm";

const refresh = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));

beforeEach(() => {
  refresh.mockClear();
  global.fetch = jest.fn();
});

test("shows not connected when no key is saved yet", () => {
  render(<GeminiKeyForm initiallyConnected={false} />);
  expect(screen.getByText("not connected")).toBeInTheDocument();
});

test("shows saved when a key is already connected", () => {
  render(<GeminiKeyForm initiallyConnected={true} />);
  expect(screen.getByText("●●●● saved")).toBeInTheDocument();
});

test("saving a key calls the settings endpoint and flips to saved", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ connected: true }),
  });

  render(<GeminiKeyForm initiallyConnected={false} />);

  await userEvent.type(
    screen.getByPlaceholderText("Paste your Gemini API key"),
    "sk-test-key",
  );
  await userEvent.click(screen.getByRole("button", { name: /save/i }));

  expect(await screen.findByText("●●●● saved")).toBeInTheDocument();
  expect(global.fetch).toHaveBeenCalledWith(
    "/api/settings/gemini-key",
    expect.objectContaining({
      method: "PUT",
      body: JSON.stringify({ api_key: "sk-test-key" }),
    }),
  );
});

test("shows an error and stays not connected when the save fails", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({ ok: false });

  render(<GeminiKeyForm initiallyConnected={false} />);

  await userEvent.type(
    screen.getByPlaceholderText("Paste your Gemini API key"),
    "sk-test-key",
  );
  await userEvent.click(screen.getByRole("button", { name: /save/i }));

  expect(await screen.findByText(/could not save key/i)).toBeInTheDocument();
  expect(screen.getByText("not connected")).toBeInTheDocument();
});
