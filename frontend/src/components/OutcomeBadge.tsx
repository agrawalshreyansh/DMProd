import { OUTCOME_LABELS, type ReelOutcome } from "@/lib/types";

const COLORS: Record<ReelOutcome, string> = {
  failed: "border-accent-warm/40 bg-accent-warm/10 text-accent-warm",
  processing: "border-border bg-background-elevated-2 text-foreground-muted",
  not_started: "border-border bg-background-elevated-2 text-foreground-muted",
  in_progress: "border-accent-signal/40 bg-accent-signal/10 text-accent-signal",
  completed: "border-accent-signal/40 bg-accent-signal/10 text-accent-signal",
};

export default function OutcomeBadge({ outcome }: { outcome: ReelOutcome }) {
  return (
    <span
      className={`inline-flex w-fit items-center rounded-full border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider ${COLORS[outcome]}`}
    >
      {OUTCOME_LABELS[outcome]}
    </span>
  );
}
