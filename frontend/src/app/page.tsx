import { redirect } from "next/navigation";
import { getToken } from "@/lib/session";

export default async function Home() {
  const token = await getToken();
  redirect(token ? "/dashboard" : "/login");
}
