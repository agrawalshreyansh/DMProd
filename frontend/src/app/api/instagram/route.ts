import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/api";
import { getToken } from "@/lib/session";

export async function DELETE() {
  const token = await getToken();
  if (!token) return NextResponse.json({ error: "unauthenticated" }, { status: 401 });

  const res = await backendFetch("/api/v1/instagram", { method: "DELETE" }, token);
  return new NextResponse(null, { status: res.status });
}
