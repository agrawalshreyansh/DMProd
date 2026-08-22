import { cookies } from "next/headers";

const COOKIE_NAME = "dmprod_token";

// ponytail: one httpOnly cookie on the Next.js domain holds the JWT. Route
// handlers set/clear it server-side; Server Components/layouts read it to
// gate pages and to forward it as a Bearer token to the backend. The
// browser never talks to FastAPI directly, so there's no cross-origin
// cookie problem to solve.

export async function getToken(): Promise<string | undefined> {
  const store = await cookies();
  return store.get(COOKIE_NAME)?.value;
}

export async function setToken(token: string): Promise<void> {
  const store = await cookies();
  store.set(COOKIE_NAME, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 7,
  });
}

export async function clearToken(): Promise<void> {
  const store = await cookies();
  store.delete(COOKIE_NAME);
}
