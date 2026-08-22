import { render, screen } from "@testing-library/react";
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
  render(<GeminiKeyForm initiallyConnected={false} initialMaskedKey={null} />);
  expect(screen.getByText("Not connected")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /^save$/i })).toBeInTheDocument();
});

test("shows the masked key when one is already saved, never the full key", () => {
  render(<GeminiKeyForm initiallyConnected={true} initialMaskedKey="••••abcd" />);
  expect(screen.getByText("••••abcd")).toBeInTheDocument();
  expect(screen.queryByText("Connected")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /replace/i })).toBeInTheDocument();
});

test("saving a key calls the settings endpoint and shows the new masked key", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ connected: true, masked_key: "••••test-key" }),
  });

  render(<GeminiKeyForm initiallyConnected={false} initialMaskedKey={null} />);

  await userEvent.type(
    screen.getByPlaceholderText("Paste your Gemini API key"),
    "sk-test-key",
  );
  await userEvent.click(screen.getByRole("button", { name: /^save$/i }));

  expect(await screen.findByText("••••test-key")).toBeInTheDocument();
  expect(global.fetch).toHaveBeenCalledWith(
    "/api/settings/gemini-key",
    expect.objectContaining({
      method: "PUT",
      body: JSON.stringify({ api_key: "sk-test-key" }),
    }),
  );
});

test("replacing an existing key updates the masked value shown", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ connected: true, masked_key: "••••w-key" }),
  });

  render(<GeminiKeyForm initiallyConnected={true} initialMaskedKey="••••old1" />);

  await userEvent.type(
    screen.getByPlaceholderText("Enter a new key to replace it"),
    "sk-new-key",
  );
  await userEvent.click(screen.getByRole("button", { name: /replace/i }));

  expect(await screen.findByText("••••w-key")).toBeInTheDocument();
  expect(screen.queryByText("••••old1")).not.toBeInTheDocument();
});

test("shows an error and stays not connected when the save fails", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({ ok: false });

  render(<GeminiKeyForm initiallyConnected={false} initialMaskedKey={null} />);

  await userEvent.type(
    screen.getByPlaceholderText("Paste your Gemini API key"),
    "sk-test-key",
  );
  await userEvent.click(screen.getByRole("button", { name: /^save$/i }));

  expect(await screen.findByText(/could not save key/i)).toBeInTheDocument();
  expect(screen.getByText("Not connected")).toBeInTheDocument();
});
