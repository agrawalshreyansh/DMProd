import Link from "next/link";
import { redirect } from "next/navigation";
import { getToken } from "@/lib/session";
import Wordmark from "@/components/Wordmark";
import SignalStrip from "@/components/SignalStrip";

const STEPS = [
  {
    tag: "SIG.01",
    title: "DM a reel",
    body: "Follow Dolphin AI on Instagram and share any reel with it — a recipe, a tip, an event, a product worth remembering.",
  },
  {
    tag: "SIG.02",
    title: "We listen to it",
    body: "The audio gets transcribed and read by Gemini, using your own API key, to work out what kind of task it actually is.",
  },
  {
    tag: "SIG.03",
    title: "It lands where you check it",
    body: "Notion, Google Calendar, Google Sheets — pick the destination per task type once, in Settings.",
  },
];

export default async function Home() {
  const token = await getToken();
  if (token) redirect("/dashboard");

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col px-6">
      <header className="flex items-center justify-between py-8">
        <Wordmark className="text-lg text-foreground" />
        <nav className="flex items-center gap-5 text-sm">
          <Link href="/login" className="text-foreground-muted transition hover:text-foreground">
            Log in
          </Link>
          <Link
            href="/signup"
            className="rounded-md bg-accent-signal px-4 py-2 font-medium text-background transition hover:brightness-110"
          >
            Sign up
          </Link>
        </nav>
      </header>

      <section className="flex flex-col gap-8 py-16 sm:py-24">
        <div className="flex flex-col gap-5">
          <span className="font-mono text-xs font-medium uppercase tracking-[0.2em] text-accent-signal">
            Signal in, task out
          </span>
          <h1 className="font-display text-4xl font-semibold leading-[1.1] tracking-tight sm:text-6xl">
            Turn shared reels
            <br />
            into tasks.
          </h1>
          <p className="max-w-lg text-lg text-foreground-muted">
            Dolphin AI is an Instagram bot you DM reels to. It reads them for
            you and pushes what it finds straight to Notion, Google Calendar,
            or Google Sheets — no copy-pasting captions into a notes app at
            midnight.
          </p>
        </div>

        <SignalStrip />

        <div>
          <Link
            href="/signup"
            className="inline-block rounded-md bg-accent-signal px-5 py-2.5 font-medium text-background transition hover:brightness-110"
          >
            Get started
          </Link>
        </div>
      </section>

      <section className="grid gap-10 border-t border-border py-16 sm:grid-cols-3">
        {STEPS.map((step) => (
          <div key={step.tag} className="flex flex-col gap-2">
            <span className="font-mono text-xs font-medium tracking-widest text-accent-signal">
              {step.tag}
            </span>
            <h2 className="font-display text-lg font-semibold">{step.title}</h2>
            <p className="text-sm leading-relaxed text-foreground-muted">{step.body}</p>
          </div>
        ))}
      </section>

      <section className="flex flex-col gap-3 rounded-lg border border-border bg-background-elevated px-6 py-8">
        <h2 className="font-display text-lg font-semibold">Prefer to type it yourself?</h2>
        <p className="max-w-lg text-sm leading-relaxed text-foreground-muted">
          You don&apos;t need a reel at all — create the same kind of
          structured task directly from the dashboard, and it routes to the
          same destinations.
        </p>
      </section>

      <footer className="mt-auto flex flex-wrap items-center justify-between gap-4 border-t border-border py-8 text-sm text-foreground-muted">
        <span>&copy; {new Date().getFullYear()} Dolphin AI</span>
        <nav className="flex gap-5">
          <Link href="/privacy" className="transition hover:text-foreground">
            Privacy Policy
          </Link>
          <Link href="/terms" className="transition hover:text-foreground">
            Terms of Service
          </Link>
          <Link href="/data-deletion" className="transition hover:text-foreground">
            Data Deletion
          </Link>
        </nav>
      </footer>
    </main>
  );
}
