/** Signed number: +1.5, -0.3, or a dash when missing. */
export const signed = (v: number | null | undefined, digits = 1) =>
  v == null || Number.isNaN(Number(v)) ? "–" : (v > 0 ? "+" : "") + Number(v).toFixed(digits);

export const percent = (v: number | null | undefined) => (v == null ? "–" : Number(v).toFixed(1) + "%");

/** Seconds since 1970 -> "5 min ago". */
export function ago(ts: number | null | undefined, now = Date.now() / 1000) {
  if (!ts) return "never";
  const s = now - ts;
  if (s < 3600) return Math.max(1, Math.round(s / 60)) + " min ago";
  if (s < 86400) return Math.round(s / 3600) + " h ago";
  return Math.round(s / 86400) + " days ago";
}

/** Only links to Reddit threads are shown as links (the text comes from scraped data). */
export const safeRedditUrl = (u: string | null | undefined) =>
  u && /^https:\/\/(www\.|old\.)?reddit\.com\//.test(u) ? u : null;

/** A user-typed source as a link, only when it is a plain http(s) URL; anything else stays text. */
export const safeLink = (u: string | null | undefined) => (u && /^https?:\/\/[^\s/]+\.[^\s]+$/i.test(u) ? u : null);

export const initials = (name: string) =>
  name
    .replace(/[^A-Za-z ]/g, "")
    .split(" ")
    .filter(Boolean)
    .map((w) => w[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

export function debounce<A extends unknown[]>(fn: (...args: A) => void, ms: number) {
  let t: ReturnType<typeof setTimeout> | undefined;
  return (...args: A) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}
