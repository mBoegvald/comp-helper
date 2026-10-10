import { describe, expect, it } from "vitest";
import { cleanPrefs } from "./cleanPrefs.ts";

describe("cleanPrefs", () => {
  it("keeps a valid draft", () => {
    const draft = {
      role: "top",
      ally: { bot: "Jinx" },
      enemy: { top: "Darius" },
      style: "wombo",
      unavailable: ["Garen"],
    };
    expect(cleanPrefs(draft)).toEqual(draft);
  });

  it("drops fields of the wrong type", () => {
    expect(cleanPrefs({ ally: null, enemy: ["x"], unavailable: "Garen", style: 5 })).toEqual({});
  });

  it("drops unknown roles, unknown fields and non-text names", () => {
    expect(
      cleanPrefs({ role: "feeder", lkRole: "mid", ally: { top: "Ornn", afk: "x", bot: 3 }, __proto__x: 1 }),
    ).toEqual({
      lkRole: "mid",
      ally: { top: "Ornn" },
    });
  });

  it("caps text and list lengths", () => {
    const out = cleanPrefs({ lkChamp: "x".repeat(500), unavailable: Array(80).fill("Zed") });
    expect(out.lkChamp).toHaveLength(60);
    expect(out.unavailable).toHaveLength(50);
  });

  it("ignores anything that is not an object", () => {
    for (const raw of [null, "draft", 42, ["top"]]) expect(cleanPrefs(raw)).toEqual({});
  });
});
