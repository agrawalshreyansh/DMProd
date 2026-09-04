import Link from "next/link";
import { PolicyPage, Section, List } from "@/components/PolicyPage";

export const metadata = {
  title: "Terms of Service — Panda",
};

// ponytail: [PLACEHOLDER] — same contact email as the privacy policy,
// replace with a real inbox you control before this is public. This is a
// plain-language ToS appropriate for an early-stage product, not a
// substitute for a lawyer's review before real signups/revenue depend on it.
const EFFECTIVE_DATE = "August 23, 2026";
const CONTACT_EMAIL = "privacy@usepanda.tech";

export default function TermsOfServicePage() {
  return (
    <PolicyPage title="Terms of Service" effectiveDate={EFFECTIVE_DATE}>
      <Section title="Agreement">
        <p>
          By creating a Panda account or connecting your Instagram
          account to our bot, you agree to these terms. If you don&apos;t
          agree, don&apos;t use the service.
        </p>
      </Section>

      <Section title="What the service does">
        <p>
          Panda receives reels you share with our Instagram bot
          account, processes them into structured tasks using your own
          Google Gemini API key, and pushes the results to destinations you
          configure (Notion, Google Calendar, Google Sheets). You can also
          create tasks manually from the dashboard.
        </p>
      </Section>

      <Section title="Your account">
        <List
          items={[
            ["Eligibility", "you need to be able to form a binding contract in your jurisdiction to use Panda."],
            ["Accuracy", "keep your account email and connected-account details accurate."],
            ["Security", "you're responsible for keeping your password and API keys confidential — anyone with access to your account can act as you within the service."],
          ]}
          plain
        />
      </Section>

      <Section title="Your content and keys">
        <p>
          You own the reels, captions, and generated tasks associated with
          your account. Your Gemini API key is yours — usage and any cost
          incurred through Google&apos;s API is between you and Google,
          under Google&apos;s own terms. We only use your key to process
          requests you initiate.
        </p>
      </Section>

      <Section title="Acceptable use">
        <p>You agree not to:</p>
        <ul className="flex list-disc flex-col gap-1.5 pl-5">
          <li>Share reels or content you don&apos;t have the right to share with us</li>
          <li>Use Panda to process content that violates Instagram&apos;s or Meta&apos;s own terms</li>
          <li>Attempt to disrupt, overload, or reverse-engineer the service</li>
          <li>Use another person&apos;s account or Instagram connection without permission</li>
        </ul>
      </Section>

      <Section title="Third-party services">
        <p>
          Panda depends on Meta/Instagram, Google Gemini, and — where
          you connect them — Notion, Google Calendar, and Google Sheets.
          We&apos;re not responsible for outages, policy changes, or content
          decisions made by those services. See our{" "}
          <Link href="/privacy" className="text-accent-signal underline underline-offset-2">
            Privacy Policy
          </Link>{" "}
          for what we share with each of them.
        </p>
      </Section>

      <Section title="Termination">
        <p>
          You can stop using Panda and request account deletion at any
          time — see{" "}
          <Link href="/data-deletion" className="text-accent-signal underline underline-offset-2">
            Data Deletion
          </Link>
          . We may suspend or terminate accounts that violate these terms or
          Instagram&apos;s platform policies.
        </p>
      </Section>

      <Section title="No warranty">
        <p>
          Panda is provided &ldquo;as is,&rdquo; without warranties of
          any kind. We don&apos;t guarantee the accuracy of transcripts or
          generated tasks — always check what gets pushed to your Notion,
          Calendar, or Sheet before relying on it.
        </p>
      </Section>

      <Section title="Changes to these terms">
        <p>
          If we make material changes, we&apos;ll update the effective date
          above and, where required, notify you directly.
        </p>
      </Section>

      <Section title="Contact">
        <p>
          Questions about these terms? Email{" "}
          <a href={`mailto:${CONTACT_EMAIL}`} className="text-accent-signal underline underline-offset-2">
            {CONTACT_EMAIL}
          </a>
          .
        </p>
      </Section>
    </PolicyPage>
  );
}
