"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

type Mode = "login" | "signup";

const COPY: Record<Mode, { title: string; endpoint: string; cta: string; footer: string; footerHref: string; footerLinkText: string }> = {
  login: {
    title: "Log in",
    endpoint: "/api/auth/login",
    cta: "Log in",
    footer: "No account?",
    footerHref: "/signup",
    footerLinkText: "Sign up",
  },
  signup: {
    title: "Sign up",
    endpoint: "/api/auth/signup",
    cta: "Create account",
    footer: "Already have an account?",
    footerHref: "/login",
    footerLinkText: "Log in",
  },
};

export default function AuthForm({ mode }: { mode: Mode }) {
  const copy = COPY[mode];
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const res = await fetch(copy.endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    setLoading(false);

    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      setError(data.detail ?? "Something went wrong");
      return;
    }

    router.push("/dashboard");
    router.refresh();
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-4 p-6">
      <h1 className="text-2xl font-semibold">{copy.title}</h1>
      <form onSubmit={onSubmit} className="flex flex-col gap-3">
        <input
          type="email"
          required
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="rounded border px-3 py-2"
        />
        <input
          type="password"
          required
          minLength={8}
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="rounded border px-3 py-2"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="rounded bg-black px-3 py-2 text-white disabled:opacity-50"
        >
          {loading ? "Please wait..." : copy.cta}
        </button>
      </form>
      <p className="text-sm text-gray-600">
        {copy.footer}{" "}
        <Link href={copy.footerHref} className="underline">
          {copy.footerLinkText}
        </Link>
      </p>
    </main>
  );
}
