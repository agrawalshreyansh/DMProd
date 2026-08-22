const BAR_HEIGHTS = [28, 52, 34, 68, 44, 80, 38, 60, 30, 72, 46, 56, 32, 64, 40, 24];

export default function SignalStrip() {
  return (
    <div className="flex items-center gap-6 sm:gap-10">
      <div
        className="flex h-16 flex-1 items-end gap-[3px]"
        role="img"
        aria-label="Audio waveform resolving into a structured task list"
      >
        {BAR_HEIGHTS.map((height, i) => (
          <span
            key={i}
            className="w-full flex-1 origin-bottom animate-signal-pulse rounded-full bg-accent-signal"
            style={{ height: `${height}%`, animationDelay: `${i * 90}ms` }}
          />
        ))}
      </div>

      <svg
        aria-hidden
        viewBox="0 0 24 16"
        className="hidden h-4 w-6 shrink-0 text-foreground-muted sm:block"
        fill="none"
      >
        <path d="M0 8h20M14 2l6 6-6 6" stroke="currentColor" strokeWidth="1.5" />
      </svg>

      <div className="grid shrink-0 grid-cols-3 gap-1.5">
        {[true, true, false, false, true, false].map((done, i) => (
          <span
            key={i}
            className={
              done
                ? "h-4 w-4 rounded-[4px] bg-accent-warm sm:h-5 sm:w-5"
                : "h-4 w-4 rounded-[4px] border border-border sm:h-5 sm:w-5"
            }
          />
        ))}
      </div>
    </div>
  );
}
