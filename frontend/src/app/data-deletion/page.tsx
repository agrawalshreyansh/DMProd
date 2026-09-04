import { PolicyPage, Section } from "@/components/PolicyPage";

export const metadata = {
  title: "Data Deletion — Panda",
};

// ponytail: [PLACEHOLDER] — same contact email as the privacy policy,
// replace with a real inbox you control before this is public.
const EFFECTIVE_DATE = "August 23, 2026";
const CONTACT_EMAIL = "privacy@usepanda.tech";

export default function DataDeletionPage() {
  return (
    <PolicyPage title="Data Deletion" effectiveDate={EFFECTIVE_DATE}>
      <Section title="Disconnect what you don't want stored">
        <p>
          From your Panda dashboard Settings, you can immediately:
        </p>
        <ul className="flex list-disc flex-col gap-1.5 pl-5">
          <li>Disconnect your Instagram account</li>
          <li>Remove Notion, Google Calendar, or Google Sheets connections</li>
          <li>Delete your saved Gemini API key</li>
        </ul>
        <p>
          Each of these removes the corresponding credential from our
          database right away — no waiting period.
        </p>
      </Section>

      <Section title="Delete your whole account">
        <p>
          Email{" "}
          <a href={`mailto:${CONTACT_EMAIL}?subject=Delete my account`} className="text-accent-signal underline underline-offset-2">
            {CONTACT_EMAIL}
          </a>{" "}
          from the address on your Panda account with the subject
          &ldquo;Delete my account.&rdquo; We&apos;ll delete your account,
          connected-account information, reel history, transcripts, and
          generated tasks within 30 days, and confirm by email once it&apos;s
          done.
        </p>
      </Section>

      <Section title="Revoking access from Instagram">
        <p>
          Removing Panda&apos;s access from your Instagram or Facebook
          app settings stops us from receiving new reels from that account,
          but it does not by itself delete data we&apos;ve already stored.
          Use the email request above for that.
        </p>
      </Section>

      <Section title="Contact">
        <p>
          Questions about a deletion request? Email{" "}
          <a href={`mailto:${CONTACT_EMAIL}`} className="text-accent-signal underline underline-offset-2">
            {CONTACT_EMAIL}
          </a>
          .
        </p>
      </Section>
    </PolicyPage>
  );
}
