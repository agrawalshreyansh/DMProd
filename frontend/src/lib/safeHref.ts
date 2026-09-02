// task.details.link and task.reel_url both trace back to untrusted sources
// (Gemini's structured output over a stranger's reel caption/transcript, and
// Meta's webhook payload) — reject anything that isn't http(s) before ever
// putting it in an href, so a crafted `javascript:` URI can't execute.
//
// No base URL here on purpose: these fields are always meant to be absolute
// external URLs, and `new URL(url, window.location.origin)` breaks SSR —
// `window` doesn't exist in Node, so the try/catch silently returned
// `undefined` on the server but a real href in the browser, a hydration
// mismatch (same input, different output depending on which environment
// rendered it). `new URL(url)` alone just rejects non-absolute input
// instead, deterministically, in both environments.
export function safeHref(url: string | null | undefined): string | undefined {
  if (!url) return undefined;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "https:" || parsed.protocol === "http:"
      ? parsed.toString()
      : undefined;
  } catch {
    return undefined;
  }
}
