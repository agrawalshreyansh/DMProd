import { NextResponse } from "next/server";
import { backendFetch } from "@/lib/api";
import { getToken } from "@/lib/session";

export async function GET(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const token = await getToken();
  if (!token) return NextResponse.json({ error: "unauthenticated" }, { status: 401 });

  const { id } = await params;
  const res = await backendFetch(`/api/v1/reels/${id}`, {}, token);
  return NextResponse.json(await res.json(), { status: res.status });
}
