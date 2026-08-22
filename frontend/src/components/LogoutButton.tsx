"use client";

import { useRouter } from "next/navigation";

export default function LogoutButton() {
  const router = useRouter();

  async function onClick() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  return (
    <button
      onClick={onClick}
      className="mt-auto flex items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm text-foreground-muted transition hover:bg-background-elevated-2 hover:text-accent-warm"
    >
      Log out
    </button>
  );
}
