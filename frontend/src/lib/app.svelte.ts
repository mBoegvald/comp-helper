// State shared by every tab: what the data covers, whether an update runs, and a counter views watch to refetch.
import { errorMessage, getMeta, getStatus } from "./api.ts";
import { prefs } from "./prefs.svelte.ts";
import { load, save } from "./storage.ts";
import type { Meta, Role } from "./types.ts";

export type View = "draft" | "lookup" | "data" | "admin";

export const app = $state({
  view: load<View>("view", "draft"),
  meta: null as Meta | null, // /api/meta
  error: null as string | null,
  running: false,
  log: "",
  dataVersion: 0, // bumped when data changed (update finished, hand edit saved)
});

export async function loadMeta() {
  try {
    app.meta = await getMeta();
    app.error = null;
  } catch (e) {
    app.error = "Could not load data: " + errorMessage(e);
  }
}

$effect.root(() => {
  $effect(() => save("view", app.view));
});

/** Show a champion in the Lookup tab (where its notes can be edited). */
export function openLookup(role: Role, name: string) {
  prefs.lkRole = role;
  prefs.lkChamp = name;
  app.view = "lookup";
  scrollTo({ top: 0 });
}

/** Call after anything that changes the picker's data, so open views refetch. */
export function dataChanged() {
  app.dataVersion++;
}

export async function refreshStatus() {
  let s;
  try {
    s = await getStatus();
  } catch {
    return;
  }
  const finished = app.running && !s.running;
  app.running = s.running;
  app.log = s.log;
  if (finished) {
    await loadMeta();
    dataChanged();
  }
}

/** Polls the update status every 3 s while an update runs or `watching()` is true. Returns a stop function. */
export function pollStatus(watching: () => boolean) {
  refreshStatus();
  const id = setInterval(() => {
    if (!document.hidden && (app.running || watching())) refreshStatus();
  }, 3000);
  return () => clearInterval(id);
}
