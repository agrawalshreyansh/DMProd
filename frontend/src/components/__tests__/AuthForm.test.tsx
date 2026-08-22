import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AuthForm from "@/components/AuthForm";

const push = jest.fn();
const refresh = jest.fn();

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh }),
}));

beforeEach(() => {
  push.mockClear();
  refresh.mockClear();
  global.fetch = jest.fn();
});

test("submits credentials to the login endpoint and redirects on success", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ email: "alex@example.com" }),
  });

  render(<AuthForm mode="login" />);

  await userEvent.type(screen.getByPlaceholderText("Email"), "alex@example.com");
  await userEvent.type(screen.getByPlaceholderText("Password"), "correct-horse-battery");
  await userEvent.click(screen.getByRole("button", { name: /log in/i }));

  await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));

  expect(global.fetch).toHaveBeenCalledWith(
    "/api/auth/login",
    expect.objectContaining({ method: "POST" }),
  );
});

test("shows the server error message and does not redirect on failure", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: false,
    json: async () => ({ detail: "Invalid email or password" }),
  });

  render(<AuthForm mode="login" />);

  await userEvent.type(screen.getByPlaceholderText("Email"), "alex@example.com");
  await userEvent.type(screen.getByPlaceholderText("Password"), "wrong-password");
  await userEvent.click(screen.getByRole("button", { name: /log in/i }));

  expect(await screen.findByText("Invalid email or password")).toBeInTheDocument();
  expect(push).not.toHaveBeenCalled();
});

test("signup mode posts to the signup endpoint", async () => {
  (global.fetch as jest.Mock).mockResolvedValueOnce({
    ok: true,
    json: async () => ({ email: "new@example.com" }),
  });

  render(<AuthForm mode="signup" />);

  await userEvent.type(screen.getByPlaceholderText("Email"), "new@example.com");
  await userEvent.type(screen.getByPlaceholderText("Password"), "correct-horse-battery");
  await userEvent.click(screen.getByRole("button", { name: /create account/i }));

  await waitFor(() =>
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/auth/signup",
      expect.objectContaining({ method: "POST" }),
    ),
  );
});
