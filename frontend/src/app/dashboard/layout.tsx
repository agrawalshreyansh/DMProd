import { redirect } from "next/navigation";
import Link from "next/link";
import { getToken } from "@/lib/session";
import LogoutButton from "@/components/LogoutButton";
import Wordmark from "@/components/Wordmark";

const NAV = [
  { href: "/dashboard", label: "Overview" },
  { href: "/dashboard/instagram", label: "Instagram Account" },
  { href: "/dashboard/integrations", label: "Integrations" },
  { href: "/dashboard/preferences", label: "Preferences" },
  { href: "/dashboard/history", label: "History" },
  { href: "/dashboard/stats", label: "Stats" },
  { href: "/dashboard/settings", label: "Settings" },
];

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
        <ul className="flex flex-col gap-0.5 text-sm">
          {NAV.map((item) => (
            <li key={item.href}>
              <Link
                href={item.href}
                className="block rounded-md px-2 py-1.5 text-foreground-muted transition hover:bg-background-elevated-2 hover:text-foreground"
              >
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
        <LogoutButton />
      </nav>
      <main className="flex-1 p-10">{children}</main>
    </div>
  );
}
