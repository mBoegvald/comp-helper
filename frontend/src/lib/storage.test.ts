import { afterEach, describe, expect, it, vi } from "vitest";
import { load, save } from "./storage.ts";

function fakeStorage(): Storage {
  const m = new Map<string, string>();
  return {
    getItem: (k) => m.get(k) ?? null,
    setItem: (k, v) => void m.set(k, v),
    removeItem: (k) => void m.delete(k),
    clear: () => m.clear(),
    key: (i) => [...m.keys()][i] ?? null,
    get length() {
      return m.size;
    },
  };
}

afterEach(() => vi.unstubAllGlobals());

describe("storage", () => {
  it("round-trips values under the ph. prefix", () => {
    const s = fakeStorage();
    vi.stubGlobal("localStorage", s);
    save("view", "lookup");
    expect(s.getItem("ph.view")).toBe('"lookup"');
    expect(load("view", "draft")).toBe("lookup");
  });

  it("falls back when nothing is stored", () => {
    vi.stubGlobal("localStorage", fakeStorage());
    expect(load("missing", 42)).toBe(42);
  });

  it("falls back on a broken stored value", () => {
    const s = fakeStorage();
    s.setItem("ph.state", "{not json");
    vi.stubGlobal("localStorage", s);
    expect(load("state", { ok: true })).toEqual({ ok: true });
  });

  it("never throws when storage is blocked (private windows)", () => {
    const blocked = {
      ...fakeStorage(),
      getItem: () => {
        throw new Error("denied");
      },
      setItem: () => {
        throw new Error("denied");
      },
    };
    vi.stubGlobal("localStorage", blocked);
    expect(load("view", "draft")).toBe("draft");
    expect(() => save("view", "data")).not.toThrow();
  });
});
