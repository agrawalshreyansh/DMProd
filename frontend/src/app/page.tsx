import Link from "next/link";
import { redirect } from "next/navigation";
import { getToken } from "@/lib/session";
import Wordmark from "@/components/Wordmark";
import SignalStrip from "@/components/SignalStrip";
import BreakdownBars from "@/components/BreakdownBars";

const FACTS = [
  "BYO Gemini key — no subscription",
  "Transcription runs locally (whisper.cpp, Hinglish-tuned)",
  "DM-only — no app to install",
];

const PIPELINE = [
  {
    tag: "SIG.01",
    title: "Link your Instagram",
    body: "Panda DMs you a short code; send it back from the account you'll share reels from — personal or professional. Verifies the account. Never sees the password.",
  },
  {
    tag: "SIG.02",
    title: "DM it a reel",
    body: "Recipe, product, event flyer, a tip from a friend — share it to Panda's Instagram like you would to anyone else.",
  },
  {
    tag: "SIG.03",
    title: "It listens and it watches",
    body: "Audio transcribed, frames sampled and read by Gemini vision — on-screen text and visuals count too, not just what's said.",
  },
  {
    tag: "SIG.04",
    title: "Gemini turns it into a task",
    body: "Transcript and visual read-out together decide the task type, then pull out title, description, location, link, due date, key points.",
  },
  {
    tag: "SIG.05",
    title: "Routes itself — Notion or Calendar",
    body: "Set a destination per task type once, in Preferences. Notion pages get title, link, and key points already filled in. Calendar reminders get slotted around your actual free/busy time, ahead of the due date, on a preferred day — not just dumped at a fixed hour.",
  },
  {
    tag: "SIG.06",
    title: "Comments unlock the rest",
    body: "\"Comment KEYWORD for the link\" reels: Panda posts that comment for you and folds the creator's reply straight into the task.",
  },
];

const TASK_TYPES = [
  { label: "content_idea", count: 34 },
  { label: "action_item", count: 22 },
  { label: "event_reminder", count: 15 },
  { label: "resource_reference", count: 11 },
  { label: "other", count: 4 },
];

const TASK_TYPE_LABELS: Record<string, string> = {
  content_idea: "Content idea",
  action_item: "Action item",
  event_reminder: "Event reminder",
  resource_reference: "Resource",
  other: "Other",
};

export default async function Home() {
  const token = await getToken();
  if (token) redirect("/dashboard");

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col px-6">
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

      {/* Hero — same eyebrow/heading grammar as DashboardPageHeader */}
      <section className="flex flex-col gap-8 py-16 sm:py-24">
        <div className="flex flex-col gap-5">
          <span className="font-mono text-xs font-medium uppercase tracking-[0.2em] text-accent-signal">
            SIG.00 · Signal in, task out
          </span>
          <h1 className="font-display text-4xl font-semibold leading-[1.1] tracking-tight sm:text-7xl">
            Every reel you save
            <br />
            becomes a task.
          </h1>
          <p className="max-w-xl text-lg text-foreground-muted">
            Panda is an Instagram bot you DM reels to. It transcribes the
            audio, reads the frames, and turns what it finds into a
            structured task — pushed straight to Notion or Google Calendar.
          </p>
        </div>

        <SignalStrip />

        <ul className="flex flex-col gap-2 text-sm text-foreground-muted">
          {FACTS.map((fact) => (
            <li key={fact} className="flex items-center gap-2">
              <span className="h-1 w-1 shrink-0 rounded-full bg-accent-signal" />
              {fact}
            </li>
          ))}
        </ul>

        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/signup"
            className="inline-block rounded-md bg-accent-signal px-5 py-2.5 font-medium text-background transition hover:brightness-110"
          >
            Get started
          </Link>
          <Link
            href="/login"
            className="inline-block rounded-md border border-border px-5 py-2.5 font-medium text-foreground transition hover:bg-background-elevated"
          >
            Log in
          </Link>
        </div>
      </section>

      {/* Pipeline walkthrough — every real feature, in order */}
      <section className="flex flex-col gap-10 border-t border-border py-16">
        <div className="flex flex-col gap-2">
          <span className="font-mono text-xs font-medium uppercase tracking-[0.2em] text-accent-signal">
            SIG.01–06 · How it actually works
          </span>
          <h2 className="font-display text-2xl font-semibold tracking-tight sm:text-3xl">
            Six steps. Zero typing.
          </h2>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          {PIPELINE.map((step) => (
            <div
              key={step.tag}
              className="flex flex-col gap-2 rounded-lg border border-border bg-background-elevated p-5"
            >
              <span className="font-mono text-xs font-medium tracking-widest text-accent-signal">
                {step.tag}
              </span>
              <h3 className="font-display text-lg font-semibold">{step.title}</h3>
              <p className="text-sm leading-relaxed text-foreground-muted">{step.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Task types, styled exactly like the Stats page breakdown */}
      <section className="flex flex-col gap-4 border-t border-border py-16">
        <div className="flex flex-col gap-2">
          <span className="font-mono text-xs font-medium uppercase tracking-[0.2em] text-accent-signal">
            SIG.07 · Every reel lands somewhere
          </span>
          <h2 className="font-display text-2xl font-semibold tracking-tight sm:text-3xl">
            Sorted before you even open the dashboard.
          </h2>
        </div>
        <div className="rounded-lg border border-border bg-background-elevated p-5">
          <BreakdownBars items={TASK_TYPES} labels={TASK_TYPE_LABELS} />
        </div>
        <p className="text-sm text-foreground-muted">
          No reel handy?{" "}
          <span className="text-foreground">Create the same structured task by hand</span> from
          the dashboard — it routes exactly the same way.
        </p>
      </section>

      {/* Big closing CTA */}
      <section className="flex flex-col items-start gap-5 border-t border-border py-20">
        <h2 className="font-display text-3xl font-semibold tracking-tight sm:text-5xl">
          Stop losing reels
          <br />
          to your saved folder.
        </h2>
        <Link
          href="/signup"
          className="inline-block rounded-md bg-accent-signal px-6 py-3 text-base font-medium text-background transition hover:brightness-110"
        >
          Get started free
        </Link>
      </section>

      <footer className="mt-auto flex flex-wrap items-center justify-between gap-4 border-t border-border py-8 text-sm text-foreground-muted">
        <span>&copy; {new Date().getFullYear()} Panda</span>
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
