// What a #draft= link or old saved state may set: only known fields with the right types. A link is typed by anyone,
// and a value of the wrong type (an `ally` that is null) would break the page on every visit once saved.
import { ROLES } from "./constants.ts";
import type { Prefs } from "./prefs.svelte.ts";
import type { Role } from "./types.ts";

const MAX_TEXT = 60;
const isRole = (v: unknown): v is Role => typeof v === "string" && (ROLES as string[]).includes(v);
const text = (v: unknown) => (typeof v === "string" ? v.slice(0, MAX_TEXT) : undefined);

function team(v: unknown): Partial<Record<Role, string>> | undefined {
  if (!v || typeof v !== "object" || Array.isArray(v)) return undefined;
  const out: Partial<Record<Role, string>> = {};
  for (const [k, name] of Object.entries(v)) if (isRole(k) && typeof name === "string") out[k] = text(name);
  return out;
}

export function cleanPrefs(raw: unknown): Partial<Prefs> {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return {};
  const r = raw as Record<string, unknown>;
  const out: Partial<Prefs> = {};
  if (isRole(r.role)) out.role = r.role;
  if (isRole(r.lkRole)) out.lkRole = r.lkRole;
  for (const k of ["ally", "enemy"] as const) {
    const t = team(r[k]);
    if (t) out[k] = t;
  }
  for (const k of ["style", "need", "lkChamp"] as const) {
    const t = text(r[k]);
    if (t !== undefined) out[k] = t;
  }
  if (Array.isArray(r.unavailable))
    out.unavailable = r.unavailable
      .filter((n): n is string => typeof n === "string")
      .map((n) => n.slice(0, MAX_TEXT))
      .slice(0, 50);
  return out;
}
