// Keeps the address bar and the page in step (addresses: route.ts). Moving around adds a history entry, so Back and
// Forward work; going Back, or opening a link, puts the page where the address says.
import { app, type View } from "./app.svelte.ts";
import { prefs } from "./prefs.svelte.ts";
import { formatRoute, parseRoute, type Route } from "./route.ts";

const TYPING_MS = 1500; // a champion change this soon after another replaces it: typing "Vi" on the way to "Viktor"

/** The champion's name for what is typed in Lookup, or undefined while it is not one (yet). */
function champion(typed: string) {
  const t = typed.trim().toLowerCase();
  return app.meta?.names.find((n) => n.toLowerCase() === t);
}

/** Where the page is now, or null while a half-typed name leaves that open. */
function current(): Route | null {
  if (app.view !== "lookup") return { view: app.view };
  const role = prefs.lkRole;
  if (!prefs.lkChamp.trim()) return { view: "lookup", role };
  const champ = champion(prefs.lkChamp);
  if (!champ) return null;
  const opp = app.lookupOpp?.for === `${role}|${champ}` ? app.lookupOpp.opp : undefined;
  return { view: "lookup", role, champ, opp };
}

function apply(r: Route) {
  if (r.draft) Object.assign(prefs, r.draft);
  if (r.role) {
    prefs.lkRole = r.role;
    prefs.lkChamp = r.champ ?? "";
    if (r.champ) app.lookupOpp = r.opp ? { for: `${r.role}|${r.champ}`, opp: r.opp } : null;
  }
  app.view = r.view;
}

let replacing = false;

/** Go to another view without a history entry: for pages you may not see, so Back does not land on one again. */
export function redirect(view: View) {
  replacing = true;
  app.view = view;
}

export function startRouter() {
  const start = parseRoute(location.hash);
  if (start) apply(start);
  addEventListener("popstate", () => {
    const r = parseRoute(location.hash);
    if (r) apply(r);
  });

  let lastChampion = 0; // when the last entry for a new champion was added
  $effect.root(() => {
    $effect(() => {
      const r = current();
      const replace = replacing;
      replacing = false;
      if (!r) return;
      const now = parseRoute(location.hash);
      const hash = formatRoute(r);
      if (now && !now.draft && formatRoute(now) === hash) return;
      const typing = now?.view === "lookup" && r.view === "lookup" && now.champ !== r.champ;
      if (replace || !now || now.draft || (typing && Date.now() - lastChampion < TYPING_MS)) {
        history.replaceState(null, "", hash);
      } else {
        history.pushState(null, "", hash);
        lastChampion = typing ? Date.now() : 0;
      }
    });
  });
}
