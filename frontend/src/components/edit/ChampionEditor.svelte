<script lang="ts">
  import { errorMessage, getHandChampion, saveHandChampion } from "../../lib/api.ts";
  import { BLIND_OPTIONS } from "../../lib/constants.ts";
  import type { HandChampion, HandField, Role } from "../../lib/types.ts";
  import ErrorBox from "../common/ErrorBox.svelte";

  /** Edit a champion's notes for one role. An empty field means "use the default" (role_data.py). */
  interface Props {
    role: Role;
    name: string;
    onsaved?: () => void;
    oncancel?: () => void;
  }
  let { role, name, onsaved, oncancel }: Props = $props();

  interface Field {
    key: HandField;
    label: string;
    kind: "archetype" | "select" | "text" | "area";
    options?: string[];
    hint?: string;
  }
  const FIELDS: Field[] = [
    { key: "archetype", label: "Archetype", kind: "archetype" },
    { key: "damage", label: "Damage", kind: "select", options: ["AP", "AD", "Mixed"] },
    { key: "blind_safe", label: "Blind-safe", kind: "select", options: BLIND_OPTIONS },
    {
      key: "comps",
      label: "Strong in comps",
      kind: "text",
      hint: "The picker looks for: wombo, teamfight, poke, siege, pick, dive, split, flank, scaling, late, front-to-back.",
    },
    { key: "pick_when", label: "Pick when", kind: "text" },
    { key: "good_into", label: "Good into", kind: "area", hint: "Shown after the best matchups from the win rates." },
    {
      key: "struggles_into",
      label: "Struggles into",
      kind: "area",
      hint: "Shown after the worst matchups from the win rates.",
    },
  ];

  const optionsFor = (f: Field, h: HandChampion) => (f.kind === "archetype" ? h.archetypes : (f.options ?? []));

  let loaded = $state<HandChampion | null>(null);
  let form = $state<Partial<Record<HandField, string>>>({});
  let error = $state<string | null>(null);
  let saving = $state(false);

  $effect(() => {
    getHandChampion(role, name).then(
      (r) => {
        loaded = r;
        form = Object.fromEntries(FIELDS.map((f) => [f.key, r.hand[f.key] ?? ""]));
      },
      (e) => (error = errorMessage(e)),
    );
  });

  async function save(e: SubmitEvent) {
    e.preventDefault();
    if (!loaded) return;
    saving = true;
    try {
      await saveHandChampion(role, loaded.champion, $state.snapshot(form));
      onsaved?.();
    } catch (err) {
      error = errorMessage(err);
    } finally {
      saving = false;
    }
  }
</script>

<form onsubmit={save}>
  <ErrorBox message={error} />
  {#if loaded}
    {#each FIELDS as f (f.key)}
      {@const def = loaded.defaults[f.key]}
      {@const id = `edit-${f.key}`}
      <div class="field">
        <label for={id}>{f.label}</label>
        {#if f.kind === "archetype" || f.kind === "select"}
          <select {id} bind:value={form[f.key]}>
            <option value="">Default{def ? ` (${def})` : ""}</option>
            {#each optionsFor(f, loaded) as o (o)}<option value={o}>{o}</option>{/each}
          </select>
        {:else if f.kind === "area"}
          <textarea {id} rows="2" placeholder={def ? `Default: ${def}` : ""} bind:value={form[f.key]}></textarea>
        {:else}
          <input {id} placeholder={def ? `Default: ${def}` : ""} bind:value={form[f.key]} />
        {/if}
        {#if f.hint}<p class="small muted">{f.hint}</p>{/if}
      </div>
    {/each}
    <div class="row actions">
      <button class="btn primary" disabled={saving}>{saving ? "Saving…" : "Save"}</button>
      <button type="button" class="btn" onclick={oncancel}>Cancel</button>
      <span class="small muted">Empty fields use the default.</span>
    </div>
  {/if}
</form>

<style>
  form {
    margin-top: 10px;
  }
  p {
    margin: 3px 0 0;
  }
  textarea {
    resize: vertical;
  }
  .actions {
    margin-top: 12px;
  }
</style>
