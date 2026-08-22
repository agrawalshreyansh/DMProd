// Server-only on purpose (no NEXT_PUBLIC_ prefix): this module only ever
// runs in Route Handlers / Server Components, never in the browser bundle.
// NEXT_PUBLIC_ vars get inlined at build time everywhere they're used,
// including server code — a plain var is read from real process.env at
// request time instead, so it can change per-environment without a rebuild.
const API_URL = process.env.API_URL ?? "http://localhost:8000";

export async function backendFetch(
  path: string,
  init: RequestInit = {},
  token?: string,
): Promise<Response> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);

  return fetch(`${API_URL}${path}`, { ...init, headers, cache: "no-store" });
}
