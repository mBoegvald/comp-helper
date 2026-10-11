// Where the page is, as the address bar shows it, so Back and Forward work and a matchup can be linked:
//   #/draft   #/lookup/top   #/lookup/top/Darius   #/lookup/top/Darius/Garen   #/data   #/account   #/admin   #/privacy
// Old draft links (#draft={...}) still open the Draft tab with that draft.
import type { View } from "./app.svelte.ts";
import { cleanPrefs } from "./cleanPrefs.ts";
import { ROLES } from "./constants.ts";
import type { Prefs } from "./prefs.svelte.ts";
import type { Role } from "./types.ts";

export interface Route {
  view: View;
  role?: Role;
  champ?: string;
  opp?: string;
  draft?: Partial<Prefs>; // from a #draft= link
}

const PATHS: Record<View, string> = {
  draft: "draft",
  lookup: "lookup",
  data: "data",
  mine: "account",
  admin: "admin",
  privacy: "privacy",
};
const VIEWS = Object.fromEntries(Object.entries(PATHS).map(([view, path]) => [path, view as View]));
const MAX_NAME = 60;

export function formatRoute(r: Route): string {
  const parts = [PATHS[r.view]];
  if (r.view === "lookup" && r.role) {
    parts.push(r.role);
    if (r.champ) parts.push(r.champ, ...(r.opp ? [r.opp] : []));
  }
  return "#/" + parts.map(encodeURIComponent).join("/");
}

/** The route in a location hash, or null when there is none (an empty hash, or one this page does not know). */
export function parseRoute(hash: string): Route | null {
  try {
    const draft = hash.match(/^#draft=(.+)$/);
    if (draft) return { view: "draft", draft: cleanPrefs(JSON.parse(decodeURIComponent(draft[1]))) };
    if (!hash.startsWith("#/")) return null;
    const [path, role, champ, opp] = hash.slice(2).split("/").map(decodeURIComponent);
    const view = Object.hasOwn(VIEWS, path) ? VIEWS[path] : undefined;
    if (!view) return null;
    if (view !== "lookup" || !(ROLES as string[]).includes(role)) return { view };
    const name = (s: string | undefined) => s?.trim().slice(0, MAX_NAME) || undefined;
    const r: Route = { view, role: role as Role, champ: name(champ) };
    if (r.champ && name(opp)) r.opp = name(opp);
    return r;
  } catch {
    return null; // a broken link: stay where the page would be anyway
  }
}
