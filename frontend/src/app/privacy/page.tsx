import Link from "next/link";
import Wordmark from "@/components/Wordmark";

export const metadata = {
  title: "Privacy Policy — Dolphin AI",
};

// ponytail: [PLACEHOLDER] markers below are the only things that need a
// real value before this goes in front of Meta's reviewers or real users —
// legal entity name, contact email, and effective date once it's final.
const EFFECTIVE_DATE = "August 23, 2026";
const CONTACT_EMAIL = "privacy@dolphinai.app"; // [PLACEHOLDER] replace with a real inbox you control

export default function PrivacyPolicyPage() {
  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-10 px-6 py-16">
      <header className="flex flex-col gap-4">
        <Link href="/" className="w-fit">
          <Wordmark className="text-base text-foreground-muted transition hover:text-foreground" />
        </Link>
        <div className="flex flex-col gap-1">
          <h1 className="font-display text-3xl font-semibold tracking-tight">Privacy Policy</h1>
          <p className="font-mono text-xs uppercase tracking-widest text-foreground-muted">
            Effective {EFFECTIVE_DATE}
          </p>
        </div>
      </header>

      <Section title="Overview">
        <p>
          Dolphin AI (&ldquo;we&rdquo;, &ldquo;us&rdquo;) is a service that
          lets you share Instagram reels with our bot account and turns them
          into structured tasks — pushed to destinations like Notion, Google
          Calendar, or Google Sheets that you configure. This policy explains
          what we collect, why, and how you can control it.
        </p>
      </Section>

      <Section title="Information we collect">
        <List
          items={[
            [
              "Account information",
              "The email address and password (stored as a salted hash, never in plain text) you use to sign up for the Dolphin AI dashboard.",
            ],
            [
              "Instagram account information",
              "When you connect your Instagram account, we store your Instagram user ID and username so we can match reels you send our bot to your Dolphin AI account. We do not store your Instagram password — connection happens through Instagram's own login flow.",
            ],
            [
              "Content you send us",
              "Reels and captions you DM to our Instagram bot account. We download the video temporarily to extract audio, transcribe it, and generate a structured task from it. We do not access, read, or process any Instagram content you have not explicitly sent to our bot.",
            ],
            [
              "Your Gemini API key",
              "If you provide your own Google Gemini API key, we store it encrypted at rest and use it only to process transcripts and captions on your behalf. We never use it for anything outside your own requests.",
            ],
            [
              "Integration credentials",
              "If you connect Notion, Google Calendar, or Google Sheets, we store the resulting access tokens encrypted at rest, and use them only to push tasks generated from your content to the destinations you've configured.",
            ],
          ]}
        />
      </Section>

      <Section title="How we use your information">
        <p>
          We use the information above solely to operate Dolphin AI: to
          identify you, to process reels you send us into structured tasks,
          and to deliver those tasks to the destinations you choose. We do
          not sell your information, and we do not use your content to train
          any models — reels you share are processed through Google&apos;s
          Gemini API under your own API key and Google&apos;s own terms.
        </p>
      </Section>

      <Section title="Third-party services">
        <p>
          Processing your content necessarily involves a small number of
          third-party services, each acting under their own privacy terms:
        </p>
        <List
          items={[
            ["Meta / Instagram", "to receive the reels you share with our bot account."],
            ["Google Gemini", "to transcribe audio and generate structured tasks, using your own API key."],
            ["Notion, Google Calendar, Google Sheets", "only if and where you've connected them, to deliver the resulting tasks."],
            ["MongoDB Atlas", "our database provider, to store the information described above."],
          ]}
          plain
        />
      </Section>

      <Section title="Data retention">
        <p>
          We retain your account and connected-account information for as
          long as your account is active. Downloaded reel video is deleted
          after audio extraction; we retain the transcript and generated
          task so you can see your own history in the dashboard. You can
          request deletion of your account and all associated data at any
          time — see Contact below.
        </p>
      </Section>

      <Section title="Data security">
        <p>
          API keys and third-party access tokens are encrypted at rest.
          Passwords are hashed, never stored in plain text. Access to your
          data is limited to what Dolphin AI&apos;s own systems need to
          operate the service.
        </p>
      </Section>

      <Section title="Your rights">
        <p>
          You can disconnect your Instagram account, remove integration
          connections, or delete your Gemini API key at any time from the
          dashboard. To request a full export or deletion of your account
          and associated data, contact us using the details below.
        </p>
      </Section>

      <Section title="Changes to this policy">
        <p>
          If we make material changes to this policy, we&apos;ll update the
          effective date above and, where required, notify you directly.
        </p>
      </Section>

      <Section title="Contact">
        <p>
          Questions about this policy or a data request? Email{" "}
          <a href={`mailto:${CONTACT_EMAIL}`} className="text-accent-signal underline underline-offset-2">
            {CONTACT_EMAIL}
          </a>
          .
        </p>
      </Section>
    </main>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3 border-t border-border pt-6">
      <h2 className="font-display font-semibold text-foreground">{title}</h2>
      <div className="flex flex-col gap-3 text-sm leading-relaxed text-foreground-muted">
        {children}
      </div>
    </section>
  );
}

function List({ items, plain }: { items: [string, string][]; plain?: boolean }) {
  return (
    <ul className="flex flex-col gap-2">
      {items.map(([label, body]) => (
        <li key={label}>
          {plain ? (
            <>
              <span className="font-medium text-foreground">{label}</span> — {body}
            </>
          ) : (
            <>
              <span className="font-medium text-foreground">{label}.</span> {body}
            </>
          )}
        </li>
      ))}
    </ul>
  );
}
