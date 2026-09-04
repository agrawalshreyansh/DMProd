import { randomBytes } from "crypto";
import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/api";
import { getToken } from "@/lib/session";

const STATE_COOKIE = "google_oauth_state";

export async function GET(req: Request) {
  const token = await getToken();
  if (!token) return NextResponse.redirect(new URL("/login", req.url));

  const state = randomBytes(16).toString("hex");
  const res = await backendFetch(
    `/api/v1/integrations/google-calendar/connect?state=${state}`,
    {},
    token,
  );

  if (!res.ok) {
    return NextResponse.redirect(
      new URL("/dashboard/integrations?google_error=1", req.url),
    );
  }

  const { authorize_url } = await res.json();
  const redirectRes = NextResponse.redirect(authorize_url);
  // Short-lived — this only needs to survive the round trip to Google's
  // consent screen and back, and doubles as CSRF protection on the
  // callback: without it, a crafted callback link could link an attacker's
  // Google account to a victim's still-logged-in session here.
  redirectRes.cookies.set(STATE_COOKIE, state, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 600,
  });
  return redirectRes;
}
