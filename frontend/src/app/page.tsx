import Link from "next/link";
import { redirect } from "next/navigation";
import { getToken } from "@/lib/session";

const STEPS = [
  {
    title: "Share a reel",
    body: "Follow the DMProd Instagram account and DM it any reel — a recipe, a tip, an event, a product you want to remember.",
  },
  {
    title: "We do the reading",
    body: "We transcribe the audio and send it to Gemini, using your own API key, to figure out what kind of task or idea it actually is.",
  },
  {
    title: "It lands where you check it",
    body: "Notion, Google Calendar, Google Sheets — you choose the destination per task type, once, in Settings.",
  },
];

export default async function Home() {
  const token = await getToken();
  if (token) redirect("/dashboard");

  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-16 px-6 py-16">
      <header className="flex items-center justify-between">
        <span className="text-lg font-semibold">DMProd</span>
        <nav className="flex gap-4 text-sm">
          <Link href="/login" className="hover:underline">
            Log in
          </Link>
          <Link
            href="/signup"
            className="rounded bg-black px-3 py-1.5 text-white hover:bg-gray-800"
          >
            Sign up
          </Link>
        </nav>
      </header>

      <section className="flex flex-col gap-4">
        <h1 className="text-3xl font-semibold tracking-tight sm:text-4xl">
          Turn shared reels into tasks, automatically.
        </h1>
        <p className="max-w-xl text-lg text-gray-600">
          DMProd is an Instagram bot you DM reels to. It reads them for you —
          transcribes the audio, figures out what kind of task or idea it is,
          and pushes it straight to Notion, Google Calendar, or Google Sheets.
          No copy-pasting captions into a notes app at midnight.
        </p>
      </section>

      <section className="grid gap-8 sm:grid-cols-3">
        {STEPS.map((step, i) => (
          <div key={step.title} className="flex flex-col gap-2">
            <span className="text-sm font-medium text-gray-400">
              {String(i + 1).padStart(2, "0")}
            </span>
            <h2 className="font-semibold">{step.title}</h2>
            <p className="text-sm text-gray-600">{step.body}</p>
          </div>
        ))}
      </section>

      <section className="flex flex-col gap-2 border-t border-gray-200 pt-8">
        <h2 className="font-semibold">Prefer to type it yourself?</h2>
        <p className="max-w-xl text-sm text-gray-600">
          You don&apos;t need a reel at all — create the same kind of
          structured task directly from the dashboard, and it routes to the
          same destinations.
        </p>
      </section>

      <footer className="mt-auto flex items-center justify-between border-t border-gray-200 pt-6 text-sm text-gray-500">
        <span>&copy; {new Date().getFullYear()} DMProd</span>
        <Link href="/privacy" className="hover:underline">
          Privacy Policy
        </Link>
      </footer>
    </main>
  );
}
