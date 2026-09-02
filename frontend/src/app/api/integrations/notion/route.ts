import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/api";
import { getToken } from "@/lib/session";

export async function GET() {
  const token = await getToken();
  if (!token) return NextResponse.json({ error: "unauthenticated" }, { status: 401 });

  const res = await backendFetch("/api/v1/integrations/notion", {}, token);
  return NextResponse.json(await res.json(), { status: res.status });
}

export async function POST(req: NextRequest) {
  const token = await getToken();
  if (!token) return NextResponse.json({ error: "unauthenticated" }, { status: 401 });

  const body = await req.json();
  const res = await backendFetch(
    "/api/v1/integrations/notion",
    { method: "POST", body: JSON.stringify(body) },
    token,
  );
  return NextResponse.json(await res.json(), { status: res.status });
}

export async function DELETE() {
  const token = await getToken();
  if (!token) return NextResponse.json({ error: "unauthenticated" }, { status: 401 });

  const res = await backendFetch("/api/v1/integrations/notion", { method: "DELETE" }, token);
  return NextResponse.json(await res.json(), { status: res.status });
}
