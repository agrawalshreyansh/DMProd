import { redirect } from "next/navigation";
import Link from "next/link";
import { getToken } from "@/lib/session";
import LogoutButton from "@/components/LogoutButton";

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
      <nav className="w-56 shrink-0 border-r border-gray-200 p-4">
        <p className="mb-4 text-lg font-semibold">DMProd</p>
        <ul className="flex flex-col gap-2 text-sm text-gray-700">
          {NAV.map((item) => (
            <li key={item.href}>
              <Link href={item.href} className="hover:underline">
                {item.label}
              </Link>
            </li>
          ))}
        </ul>
        <LogoutButton />
      </nav>
      <main className="flex-1 p-8">{children}</main>
    </div>
  );
}
