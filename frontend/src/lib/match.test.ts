import { describe, expect, it } from "vitest";
import { suggestNames } from "./match.ts";

const NAMES = ["Darius", "Diana", "Dr. Mundo", "Twisted Fate", "Miss Fortune", "Kai'Sa", "Kayle", "Akali", "Garen"];

describe("suggestNames", () => {
  it("puts names that start with the text first", () => {
    expect(suggestNames(NAMES, "da")).toEqual(["Darius"]);
    expect(suggestNames(NAMES, "d")).toEqual(["Darius", "Diana", "Dr. Mundo"]);
  });

  it("puts an exact name first, so Enter picks what was typed", () => {
    expect(suggestNames(["Viego", "Viktor", "Vi"], "vi")).toEqual(["Vi", "Viego", "Viktor"]);
  });

  it("ignores case, spaces and punctuation", () => {
    expect(suggestNames(NAMES, "KAIS")).toEqual(["Kai'Sa"]);
    expect(suggestNames(NAMES, "drmu")).toEqual(["Dr. Mundo"]);
  });

  it("finds a later word and initials", () => {
    expect(suggestNames(NAMES, "fate")).toEqual(["Twisted Fate"]);
    expect(suggestNames(NAMES, "mundo")).toEqual(["Dr. Mundo"]);
    expect(suggestNames(NAMES, "tf")).toEqual(["Twisted Fate"]);
    expect(suggestNames(NAMES, "mf")).toEqual(["Miss Fortune"]);
  });

  it("then names that only contain the text", () => {
    expect(suggestNames(NAMES, "ka")).toEqual(["Kai'Sa", "Kayle", "Akali"]); // Akali last: "ka" is inside
  });

  it("suggests nothing for empty text or no match", () => {
    expect(suggestNames(NAMES, "  ")).toEqual([]);
    expect(suggestNames(NAMES, "zzz")).toEqual([]);
  });

  it("stops at the limit", () => {
    expect(suggestNames(NAMES, "d", 2)).toEqual(["Darius", "Diana"]);
  });
});
