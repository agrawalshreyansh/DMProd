"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/dashboard", label: "Overview", tag: "00" },
  { href: "/dashboard/instagram", label: "Instagram Account", tag: "01" },
  { href: "/dashboard/integrations", label: "Integrations", tag: "02" },
  { href: "/dashboard/preferences", label: "Preferences", tag: "03" },
  { href: "/dashboard/history", label: "History", tag: "04" },
  { href: "/dashboard/tasks", label: "Tasks", tag: "05" },
  { href: "/dashboard/stats", label: "Stats", tag: "06" },
  { href: "/dashboard/settings", label: "Settings", tag: "07" },
];

export default function SidebarNav() {
  const pathname = usePathname();

  return (
    <ul className="flex flex-col gap-0.5 text-sm">
      {NAV.map((item) => {
        const active =
          item.href === "/dashboard" ? pathname === item.href : pathname.startsWith(item.href);
        return (
          <li key={item.href}>
            <Link
              href={item.href}
              className={`flex items-center gap-2.5 rounded-md border-l-2 px-2.5 py-1.5 transition ${
                active
                  ? "border-accent-signal bg-background-elevated-2 text-foreground"
                  : "border-transparent text-foreground-muted hover:bg-background-elevated-2 hover:text-foreground"
              }`}
            >
              <span
                className={`font-mono text-[10px] tracking-wider ${
                  active ? "text-accent-signal" : "text-foreground-muted/60"
                }`}
              >
                {item.tag}
              </span>
              {item.label}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
