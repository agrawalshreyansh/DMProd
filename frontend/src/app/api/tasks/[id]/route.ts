import { NextRequest, NextResponse } from "next/server";
import { backendFetch } from "@/lib/api";
import { getToken } from "@/lib/session";

export async function PATCH(req: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const token = await getToken();
  if (!token) return NextResponse.json({ error: "unauthenticated" }, { status: 401 });

  const { id } = await params;
  const body = await req.json();
  const res = await backendFetch(
    `/api/v1/tasks/${id}`,
    { method: "PATCH", body: JSON.stringify(body) },
    token,
  );
  return NextResponse.json(await res.json(), { status: res.status });
}
