import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import NotionConnectForm from "@/components/NotionConnectForm";

const refresh = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ refresh }),
}));

beforeEach(() => {
  refresh.mockClear();
  global.fetch = jest.fn();
});

test("shows not connected with a connect form when nothing is saved yet", () => {
  render(<NotionConnectForm initiallyConnected={false} initialDatabaseTitle={null} />);
  expect(screen.getByText("Not connected")).toBeInTheDocument();
  expect(screen.getByPlaceholderText(/integration token/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /^connect$/i })).toBeInTheDocument();
});

test("shows the connected database title and a disconnect button when already connected", () => {
  render(<NotionConnectForm initiallyConnected={true} initialDatabaseTitle="My Tasks" />);
  expect(screen.getByText("My Tasks")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /disconnect/i })).toBeInTheDocument();
  expect(screen.queryByPlaceholderText(/integration token/i)).not.toBeInTheDocument();
});

test("connecting posts the token and database id, then shows the database title", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ connected: true, database_id: "db-1", database_title: "My Tasks" }),
  });

  render(<NotionConnectForm initiallyConnected={false} initialDatabaseTitle={null} />);

  await userEvent.type(screen.getByPlaceholderText(/integration token/i), "secret-token");
  await userEvent.type(screen.getByPlaceholderText(/database id/i), "db-1");
  await userEvent.click(screen.getByRole("button", { name: /^connect$/i }));

  expect(await screen.findByText("My Tasks")).toBeInTheDocument();
  expect(global.fetch).toHaveBeenCalledWith(
    "/api/integrations/notion",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ token: "secret-token", database_id: "db-1" }),
    }),
  );
});

test("shows the backend's error message when connecting fails", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: false,
    json: async () => ({ detail: "Could not access that database" }),
  });

  render(<NotionConnectForm initiallyConnected={false} initialDatabaseTitle={null} />);

  await userEvent.type(screen.getByPlaceholderText(/integration token/i), "bad-token");
  await userEvent.type(screen.getByPlaceholderText(/database id/i), "db-1");
  await userEvent.click(screen.getByRole("button", { name: /^connect$/i }));

  expect(await screen.findByText("Could not access that database")).toBeInTheDocument();
  expect(screen.getByText("Not connected")).toBeInTheDocument();
});

test("disconnecting calls DELETE and reverts to the connect form", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({ ok: true, json: async () => ({}) });

  render(<NotionConnectForm initiallyConnected={true} initialDatabaseTitle="My Tasks" />);
  await userEvent.click(screen.getByRole("button", { name: /disconnect/i }));

  expect(global.fetch).toHaveBeenCalledWith(
    "/api/integrations/notion",
    expect.objectContaining({ method: "DELETE" }),
  );
  expect(await screen.findByText("Not connected")).toBeInTheDocument();
});
