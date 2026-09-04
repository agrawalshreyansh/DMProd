import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/api";
import { getToken } from "@/lib/session";

const STATE_COOKIE = "google_oauth_state";

export async function GET(req: NextRequest) {
  const token = await getToken();
  if (!token) return NextResponse.redirect(new URL("/login", req.url));

  const code = req.nextUrl.searchParams.get("code");
  const state = req.nextUrl.searchParams.get("state");
  const expectedState = req.cookies.get(STATE_COOKIE)?.value;

  const fail = () => {
    const res = NextResponse.redirect(new URL("/dashboard/integrations?google_error=1", req.url));
    res.cookies.delete(STATE_COOKIE);
    return res;
  };

  if (!code || !state || !expectedState || state !== expectedState) return fail();

  const res = await backendFetch(
    "/api/v1/integrations/google-calendar/callback",
    { method: "POST", body: JSON.stringify({ code }) },
    token,
  );
  if (!res.ok) return fail();

  const success = NextResponse.redirect(
    new URL("/dashboard/integrations?google=connected", req.url),
  );
  success.cookies.delete(STATE_COOKIE);
  return success;
}
