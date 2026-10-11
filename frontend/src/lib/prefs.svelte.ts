// What the page remembers between visits. Same storage key as the old page, so a saved draft carries over.
import { cleanPrefs } from "./cleanPrefs.ts";
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

// a draft link (#draft={...}) is applied over this by the router
export const prefs = $state<Prefs>({ ...DEFAULTS, ...cleanPrefs(load<unknown>("state", {})) });

$effect.root(() => {
  $effect(() => save("state", $state.snapshot(prefs)));
});

export function clearDraft() {
  Object.assign(prefs, { ally: {}, enemy: {}, unavailable: [], style: "", need: "" });
}
