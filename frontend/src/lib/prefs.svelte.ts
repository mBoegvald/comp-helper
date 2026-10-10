// What the page remembers between visits. Same storage key as the old page, so a saved draft carries over.
import { load, save } from "./storage.ts";
import type { Role } from "./types.ts";

export interface Prefs {
  role: Role;
  ally: Partial<Record<Role, string>>;
  enemy: Partial<Record<Role, string>>;
  style: string;
  need: string;
  unavailable: string[];
  lkRole: Role;
  lkChamp: string;
}

const DEFAULTS: Prefs = {
  role: "mid",
  ally: {},
  enemy: {},
  style: "",
  need: "",
  unavailable: [],
  lkRole: "mid",
  lkChamp: "",
};

function initial(): Prefs {
  const p: Prefs = { ...DEFAULTS, ...load<Partial<Prefs>>("state", {}) };
  try {
    // a draft in the address bar (#draft={...}) wins, so drafts can be bookmarked
    const m = location.hash.match(/^#draft=(.+)$/);
    if (m) Object.assign(p, JSON.parse(decodeURIComponent(m[1])));
  } catch {
    // a broken link: keep the remembered draft
  }
  return p;
}

export const prefs = $state(initial());

$effect.root(() => {
  $effect(() => save("state", $state.snapshot(prefs)));
});

export function clearDraft() {
  Object.assign(prefs, { ally: {}, enemy: {}, unavailable: [], style: "", need: "" });
}
