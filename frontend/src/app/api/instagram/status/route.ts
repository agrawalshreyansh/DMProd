import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/api";
import { getToken } from "@/lib/session";

export async function GET() {
  const token = await getToken();
  if (!token) return NextResponse.json({ error: "unauthenticated" }, { status: 401 });

  const res = await backendFetch("/api/v1/instagram/status", {}, token);
  return NextResponse.json(await res.json(), { status: res.status });
}
