import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/api";
import { getToken } from "@/lib/session";

export async function GET() {
  const token = await getToken();
  if (!token) return NextResponse.json({ error: "unauthenticated" }, { status: 401 });

  const res = await backendFetch("/api/v1/preferences", {}, token);
  return NextResponse.json(await res.json(), { status: res.status });
}

export async function PUT(req: NextRequest) {
  const token = await getToken();
  if (!token) return NextResponse.json({ error: "unauthenticated" }, { status: 401 });

  const body = await req.json();
  const res = await backendFetch(
    "/api/v1/preferences",
    { method: "PUT", body: JSON.stringify(body) },
    token,
  );
  return NextResponse.json(await res.json(), { status: res.status });
}
