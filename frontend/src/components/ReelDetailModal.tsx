"use client";

import { useEffect, useState } from "react";
import OutcomeBadge from "@/components/OutcomeBadge";
import { TASK_TYPE_LABELS, type Reel, type ReelDetail } from "@/lib/types";
import { safeHref } from "@/lib/safeHref";

export default function ReelDetailModal({ reel, onClose }: { reel: Reel; onClose: () => void }) {
  const [detail, setDetail] = useState<ReelDetail | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);

    fetch(`/api/reels/${reel.id}`)
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then(setDetail)
      .catch(() => setError(true));

    return () => {
      document.body.style.overflow = originalOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [reel.id, onClose]);

  const reelHref = safeHref(reel.url);
  const linkHref = safeHref(detail?.details?.link ?? null);

  return (
    <div
      role="presentation"
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-6 pt-16 sm:pt-24"
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="reel-detail-title"
        onClick={(e) => e.stopPropagation()}
        className="flex w-full max-w-xl flex-col gap-5 rounded-lg border border-border bg-background-elevated p-6 shadow-xl"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex flex-col gap-1">
            <span className="font-mono text-xs uppercase tracking-widest text-foreground-muted">
              {new Date(reel.received_at).toLocaleString()}
            </span>
            <h2 id="reel-detail-title" className="font-display text-lg font-semibold text-foreground">
              {detail?.title || reel.caption || "Untitled reel"}
            </h2>
            <OutcomeBadge outcome={reel.outcome} />
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="shrink-0 rounded-md px-2 py-1 text-foreground-muted transition hover:bg-background-elevated-2 hover:text-foreground"
          >
            ✕
          </button>
        </div>

        {error && (
          <p className="text-sm text-accent-warm">Couldn&apos;t load this reel&apos;s detail.</p>
        )}

        {!error && !detail && (
          <p className="font-mono text-xs uppercase tracking-widest text-foreground-muted">Loading…</p>
        )}

        {detail && (
          <div className="flex flex-col gap-4 text-sm">
            {reel.error_message && (
              <p className="rounded-md border border-accent-warm/40 bg-accent-warm/10 p-3 text-xs text-accent-warm">
                {reel.error_message}
              </p>
            )}

            {detail.details?.description && (
              <p className="leading-relaxed text-foreground">{detail.details.description}</p>
            )}

            {(detail.details?.key_points.length ?? 0) > 0 && (
              <ul className="flex list-disc flex-col gap-1 pl-5 text-foreground">
                {detail.details!.key_points.map((point, i) => (
                  <li key={i}>{point}</li>
                ))}
              </ul>
            )}

            {detail.visual_summary && (
              <div className="flex flex-col gap-1.5 rounded-md border border-border p-3">
                <span className="font-mono text-[10px] uppercase tracking-widest text-foreground-muted">
                  Extracted from video frames
                </span>
                <p className="whitespace-pre-line text-xs leading-relaxed text-foreground-muted">
                  {detail.visual_summary}
                </p>
              </div>
            )}

            <dl className="flex flex-col gap-2 text-xs">
              {detail.task && (
                <div className="flex gap-2">
                  <dt className="w-24 shrink-0 text-foreground-muted">Task type</dt>
                  <dd className="text-foreground">
                    {TASK_TYPE_LABELS[detail.task.task_type] ?? detail.task.task_type}
                  </dd>
                </div>
              )}
              {detail.details?.link && (
                <div className="flex gap-2">
                  <dt className="w-24 shrink-0 text-foreground-muted">Link</dt>
                  <dd className="truncate">
                    {linkHref ? (
                      <a
                        href={linkHref}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-accent-signal underline underline-offset-2"
                      >
                        {detail.details.link}
                      </a>
                    ) : (
                      detail.details.link
                    )}
                  </dd>
                </div>
              )}
              {(reel.url || reel.caption) && (
                <div className="flex gap-2">
                  <dt className="w-24 shrink-0 text-foreground-muted">Reel</dt>
                  <dd className="truncate">
                    {reelHref ? (
                      <a
                        href={reelHref}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-accent-signal underline underline-offset-2"
                      >
                        {reel.caption || "View reel"}
                      </a>
                    ) : (
                      reel.caption
                    )}
                  </dd>
                </div>
              )}
              {detail.push_logs.length > 0 && (
                <div className="flex gap-2">
                  <dt className="w-24 shrink-0 text-foreground-muted">Pushed to</dt>
                  <dd className="flex flex-col gap-1">
                    {detail.push_logs.map((log, i) => (
                      <span key={i} className="text-foreground">
                        {log.status === "success" && log.external_ref_url ? (
                          <a
                            href={safeHref(log.external_ref_url) ?? undefined}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-accent-signal underline underline-offset-2"
                          >
                            {log.integration_type}
                          </a>
                        ) : (
                          <span className="text-accent-warm">
                            {log.integration_type} failed{log.error_message ? `: ${log.error_message}` : ""}
                          </span>
                        )}
                      </span>
                    ))}
                  </dd>
                </div>
              )}
              {detail.transcript_text && (
                <div className="flex flex-col gap-1 border-t border-border pt-2">
                  <dt className="text-foreground-muted">Transcript</dt>
                  <dd className="max-h-32 overflow-y-auto whitespace-pre-line text-foreground-muted">
                    {detail.transcript_text}
                  </dd>
                </div>
              )}
            </dl>
          </div>
        )}
      </div>
    </div>
  );
}
