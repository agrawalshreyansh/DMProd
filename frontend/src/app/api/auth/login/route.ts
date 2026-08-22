import { NextRequest } from "next/server";
import { proxySignupOrLogin } from "@/lib/auth-proxy";

export async function POST(req: NextRequest) {
  const body = await req.json();
  return proxySignupOrLogin("/api/v1/auth/login", body);
}
