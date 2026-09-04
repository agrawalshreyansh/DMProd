import { redirect } from "next/navigation";
import Link from "next/link";
import { getToken } from "@/lib/session";
import LogoutButton from "@/components/LogoutButton";
import Wordmark from "@/components/Wordmark";
import SidebarNav from "@/components/SidebarNav";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // ponytail: layout-level auth guard is enough for a Phase 0 MVP. It runs
  // once per top-level /dashboard entry; per-page data fetches (e.g.
  // Settings) still forward the token to the backend on every request, so a
  // revoked/expired token still gets caught there even between navigations.
  const token = await getToken();
  if (!token) redirect("/login");

  return (
    <div className="flex min-h-screen">
      <nav className="flex w-60 shrink-0 flex-col border-r border-border bg-background-elevated p-5">
        <Link href="/dashboard" className="mb-8">
          <Wordmark className="text-base text-foreground" />
        </Link>
        <span className="mb-2 font-mono text-xs uppercase tracking-widest text-foreground-muted">
          Menu
        </span>
        <SidebarNav />
        <LogoutButton />
      </nav>
      <main className="flex-1 overflow-y-auto p-10">
        <div className="mx-auto flex w-full max-w-4xl flex-col gap-8">{children}</div>
      </main>
    </div>
  );
}
