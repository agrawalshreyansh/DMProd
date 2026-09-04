"use client";

import { useState } from "react";
import OutcomeBadge from "@/components/OutcomeBadge";
import ReelDetailModal from "@/components/ReelDetailModal";
import { TASK_TYPE_LABELS, type Reel } from "@/lib/types";
import { safeHref } from "@/lib/safeHref";

export default function HistoryTable({ reels }: { reels: Reel[] }) {
  const [openReel, setOpenReel] = useState<Reel | null>(null);

  return (
    <>
      <ul className="flex flex-col gap-3">
        {reels.map((reel) => {
          const reelHref = safeHref(reel.url);
          return (
            <li key={reel.id}>
              <button
                type="button"
                onClick={() => setOpenReel(reel)}
                className="flex w-full flex-col gap-2 rounded-lg border border-border bg-background-elevated p-4 text-left transition hover:bg-background-elevated-2"
              >
                <div className="flex items-start justify-between gap-3">
                  <p className="line-clamp-2 text-sm leading-relaxed text-foreground">
                    {reel.task?.title || reel.caption || "No caption"}
                  </p>
                  <OutcomeBadge outcome={reel.outcome} />
                </div>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-foreground-muted">
                  <span className="font-mono">{new Date(reel.received_at).toLocaleString()}</span>
                  {reel.task && (
                    <span>{TASK_TYPE_LABELS[reel.task.task_type] ?? reel.task.task_type}</span>
                  )}
                  {reel.push && (
                    <span className="text-accent-signal">→ {reel.push.integration_type}</span>
                  )}
                  {reelHref && (
                    <a
                      href={reelHref}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="text-accent-signal underline underline-offset-2"
                    >
                      View reel
                    </a>
                  )}
                </div>
              </button>
            </li>
          );
        })}
      </ul>

      {openReel && <ReelDetailModal reel={openReel} onClose={() => setOpenReel(null)} />}
    </>
  );
}
