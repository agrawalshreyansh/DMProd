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
    <button onClick={onClick} className="mt-6 text-sm text-red-600 hover:underline">
      Log out
    </button>
  );
}
