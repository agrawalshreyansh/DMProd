import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/api";
import { setToken } from "@/lib/session";

type Credentials = { email: string; password: string };

export async function proxySignupOrLogin(
  backendPath: "/api/v1/auth/signup" | "/api/v1/auth/login",
  body: Credentials,
): Promise<NextResponse> {
  const res = await backendFetch(backendPath, {
    method: "POST",
    body: JSON.stringify(body),
  });
  const data = await res.json();

  if (!res.ok) {
    return NextResponse.json(data, { status: res.status });
  }

  await setToken(data.access_token);
  return NextResponse.json({ email: data.email });
}
