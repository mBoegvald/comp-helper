import { afterEach, describe, expect, it, vi } from "vitest";
import { errorMessage, getMatchup, recommend, saveCuratedMatchup } from "./api.ts";

function answer(status: number, body: unknown) {
  return vi.fn(async () => new Response(typeof body === "string" ? body : JSON.stringify(body), { status }));
}

afterEach(() => vi.unstubAllGlobals());

describe("api", () => {
  it("GETs with the parameters in the query string", async () => {
    const f = answer(200, { champ: "Zed" });
    vi.stubGlobal("fetch", f);
    await getMatchup("mid", "Zed", "Kai'Sa");
    expect(f).toHaveBeenCalledWith("/api/matchup?role=mid&a=Zed&b=Kai%27Sa", {});
  });

  it("POSTs JSON", async () => {
    const f = answer(200, { ok: true });
    vi.stubGlobal("fetch", f);
    await saveCuratedMatchup("top", "Garen", "Darius", "Favored", "tip");
    const [url, init] = f.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/curated/matchup");
    expect(init.method).toBe("POST");
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
    expect(JSON.parse(String(init.body))).toEqual({
      role: "top",
      champion: "Garen",
      opponent: "Darius",
      result: "Favored",
      tip: "tip",
    });
  });

  it("throws the server's error message", async () => {
    vi.stubGlobal("fetch", answer(400, { error: "unknown role nope" }));
    await expect(getMatchup("mid", "a", "b")).rejects.toThrow("unknown role nope");
  });

  it("throws the HTTP status when the answer is not JSON", async () => {
    vi.stubGlobal("fetch", answer(502, "<html>Bad gateway</html>"));
    await expect(recommend({} as never)).rejects.toThrow("HTTP 502");
  });

  it("errorMessage handles anything thrown", () => {
    expect(errorMessage(new Error("boom"))).toBe("boom");
    expect(errorMessage("plain")).toBe("plain");
  });
});
