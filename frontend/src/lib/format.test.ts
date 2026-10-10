import { afterEach, describe, expect, it, vi } from "vitest";
import { ago, debounce, initials, percent, safeRedditUrl, signed } from "./format.ts";
import { safeLink } from "./format.ts";

describe("signed", () => {
  it.each([
    [1.25, "+1.3"],
    [-0.3, "-0.3"],
    [0, "0.0"],
    [null, "–"],
    [undefined, "–"],
  ])("%s -> %s", (v, out) => expect(signed(v)).toBe(out));

  it("takes the number of digits", () => expect(signed(2, 2)).toBe("+2.00"));
});

describe("percent", () => {
  it("rounds to one digit", () => expect(percent(45.55)).toBe("45.5%"));
  it("shows a dash when missing", () => expect(percent(null)).toBe("–"));
});

describe("ago", () => {
  const now = 1_800_000_000;
  it.each([
    [now - 10, "1 min ago"], // never "0 min"
    [now - 600, "10 min ago"],
    [now - 7200, "2 h ago"],
    [now - 3 * 86400, "3 days ago"],
  ])("%s -> %s", (ts, out) => expect(ago(ts, now)).toBe(out));

  it("says never without a time", () => expect(ago(null, now)).toBe("never"));
});

describe("safeRedditUrl", () => {
  it.each([
    "https://www.reddit.com/r/zedmains/comments/abc/x/",
    "https://reddit.com/r/x/",
    "https://old.reddit.com/r/x/",
  ])("keeps %s", (u) => expect(safeRedditUrl(u)).toBe(u));

  it.each([
    "javascript:alert(1)",
    "http://www.reddit.com/r/x/", // not https
    "https://reddit.com.evil.example/r/x/",
    "https://evil.example/?https://www.reddit.com/",
    "",
    null,
  ])("drops %s", (u) => expect(safeRedditUrl(u)).toBeNull());
});

describe("initials", () => {
  it.each([
    ["Twisted Fate", "TF"],
    ["Kai'Sa", "K"], // one word (the apostrophe is dropped): one letter
    ["Nunu & Willump", "NW"],
    ["Zed", "Z"],
  ])("%s -> %s", (name, out) => expect(initials(name)).toBe(out));
});

describe("debounce", () => {
  afterEach(() => vi.useRealTimers());

  it("calls once, with the last arguments, after the quiet time", () => {
    vi.useFakeTimers();
    const fn = vi.fn();
    const d = debounce(fn, 250);
    d("a");
    d("b");
    vi.advanceTimersByTime(249);
    expect(fn).not.toHaveBeenCalled();
    d("c");
    vi.advanceTimersByTime(250);
    expect(fn).toHaveBeenCalledOnce();
    expect(fn).toHaveBeenCalledWith("c");
  });
});

describe("safeLink", () => {
  it.each(["https://www.reddit.com/r/DariusMains/", "http://example.com/guide", "https://youtu.be/abc"])(
    "links %s",
    (u) => expect(safeLink(u)).toBe(u),
  );

  it.each([
    "javascript:alert(1)",
    "a streamer called X", // a plain source stays text
    "https://", // no host
    "https://localhost/x", // no dot in the host
    "https://evil.example/ x", // spaces
    "data:text/html,hi",
    null,
  ])("keeps %s as text", (u) => expect(safeLink(u)).toBeNull());
});
