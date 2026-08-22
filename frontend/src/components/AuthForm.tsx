"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Wordmark from "@/components/Wordmark";

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
    <main className="mx-auto flex min-h-screen w-full max-w-sm flex-col justify-center gap-8 px-6">
      <Link href="/" className="w-fit">
        <Wordmark className="text-base text-foreground-muted transition hover:text-foreground" />
      </Link>

      <div className="flex flex-col gap-6 rounded-lg border border-border bg-background-elevated p-6">
        <h1 className="font-display text-xl font-semibold">{copy.title}</h1>
        <form onSubmit={onSubmit} className="flex flex-col gap-3">
          <input
            type="email"
            required
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded-md border border-border bg-background px-3 py-2 text-foreground placeholder:text-foreground-muted outline-none focus:border-accent-signal focus:ring-1 focus:ring-accent-signal"
          />
          <input
            type="password"
            required
            minLength={8}
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded-md border border-border bg-background px-3 py-2 text-foreground placeholder:text-foreground-muted outline-none focus:border-accent-signal focus:ring-1 focus:ring-accent-signal"
          />
          {error && <p className="text-sm text-accent-warm">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="rounded-md bg-accent-signal px-3 py-2 font-medium text-background transition hover:brightness-110 disabled:opacity-50"
          >
            {loading ? "Please wait..." : copy.cta}
          </button>
        </form>
      </div>

      <p className="text-center text-sm text-foreground-muted">
        {copy.footer}{" "}
        <Link href={copy.footerHref} className="text-accent-signal underline underline-offset-2">
          {copy.footerLinkText}
        </Link>
      </p>
    </main>
  );
}
