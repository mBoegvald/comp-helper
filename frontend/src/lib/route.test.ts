import { describe, expect, it } from "vitest";
import type { Prefs } from "./prefs.svelte.ts";
import { draftHash, formatRoute, parseRoute } from "./route.ts";

describe("routes", () => {
  it("round-trips every kind of route", () => {
    for (const r of [
      { view: "draft" },
      { view: "lookup", role: "top" },
      { view: "lookup", role: "top", champ: "Darius" },
      { view: "lookup", role: "support", champ: "Tahm Kench", opp: "Kai'Sa" },
      { view: "mine" },
      { view: "privacy" },
    ] as const) {
      expect(parseRoute(formatRoute(r))).toEqual(r);
    }
  });

  it("writes readable addresses", () => {
    expect(formatRoute({ view: "lookup", role: "top", champ: "Tahm Kench", opp: "Garen" })).toBe(
      "#/lookup/top/Tahm%20Kench/Garen",
    );
    expect(formatRoute({ view: "mine" })).toBe("#/account");
    expect(formatRoute({ view: "data", role: "top", champ: "Darius" })).toBe("#/data"); // only Lookup has more
  });

  it("knows no route in an empty or unknown hash", () => {
    for (const h of ["", "#", "#/", "#/nope", "#/constructor", "#/__proto__", "#top", "#/%E0%A4%A"]) {
      expect(parseRoute(h)).toBeNull();
    }
  });

  it("drops what does not fit", () => {
    expect(parseRoute("#/lookup/feeder/Darius")).toEqual({ view: "lookup" });
    expect(parseRoute("#/lookup/top//Garen")).toEqual({ view: "lookup", role: "top" });
    expect(parseRoute("#/data/top/Darius")).toEqual({ view: "data" });
    expect(parseRoute("#/lookup/top/" + "x".repeat(500))?.champ).toHaveLength(60);
  });

  it("reads old draft links, cleaned", () => {
    const link = "#draft=" + encodeURIComponent('{"role":"top","enemy":{"top":"Darius"},"ally":null}');
    expect(parseRoute(link)).toEqual({ view: "draft", draft: { role: "top", enemy: { top: "Darius" } } });
    expect(parseRoute("#draft=%7Bnot json")).toBeNull();
  });

  it("writes draft links that read back as the same draft, without the Lookup fields", () => {
    const draft = { role: "top", ally: { bot: "Jinx" }, enemy: { top: "Darius" }, style: "wombo", need: "ap" };
    const p: Prefs = { ...draft, unavailable: ["Garen"], lkRole: "mid", lkChamp: "Zed" } as Prefs;
    expect(parseRoute(draftHash(p))).toEqual({ view: "draft", draft: { ...draft, unavailable: ["Garen"] } });
  });
});
