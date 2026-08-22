import Link from "next/link";
import Wordmark from "@/components/Wordmark";

export function PolicyPage({
  title,
  effectiveDate,
  children,
}: {
  title: string;
  effectiveDate: string;
  children: React.ReactNode;
}) {
  return (
    <main className="mx-auto flex w-full max-w-2xl flex-1 flex-col gap-10 px-6 py-16">
      <header className="flex flex-col gap-4">
        <Link href="/" className="w-fit">
          <Wordmark className="text-base text-foreground-muted transition hover:text-foreground" />
        </Link>
        <div className="flex flex-col gap-1">
          <h1 className="font-display text-3xl font-semibold tracking-tight">{title}</h1>
          <p className="font-mono text-xs uppercase tracking-widest text-foreground-muted">
            Effective {effectiveDate}
          </p>
        </div>
      </header>
      {children}
    </main>
  );
}

export function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3 border-t border-border pt-6">
      <h2 className="font-display font-semibold text-foreground">{title}</h2>
      <div className="flex flex-col gap-3 text-sm leading-relaxed text-foreground-muted">
        {children}
      </div>
    </section>
  );
}

export function List({ items, plain }: { items: [string, string][]; plain?: boolean }) {
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
