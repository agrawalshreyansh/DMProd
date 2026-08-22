export default function Wordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 font-display font-semibold tracking-tight ${className}`}>
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping-dot rounded-full bg-accent-signal" />
      </span>
      Dolphin AI
    </span>
  );
}
