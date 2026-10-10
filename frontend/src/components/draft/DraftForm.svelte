<script lang="ts">
  import { app } from "../../lib/app.svelte.ts";
  import { clearDraft, prefs } from "../../lib/prefs.svelte.ts";
  import type { Recommendation } from "../../lib/types.ts";
  import RoleSwitch from "../common/RoleSwitch.svelte";
  import ChipInput from "./ChipInput.svelte";
  import TeamSlots from "./TeamSlots.svelte";

  /** The draft as typed. `result` is the last /api/recommend answer (name checks, detected damage need). */
  let { result }: { result: Recommendation | null } = $props();

  const slots = $derived(result?.slots ?? {});
  const capitalize = (s: string) => s[0].toUpperCase() + s.slice(1);
</script>

<div class="panel">
  <h2>I'm picking</h2>
  <RoleSwitch bind:value={prefs.role} label="Your role" />

  <div class="teams">
    <TeamSlots side="ally" bind:values={prefs.ally} myRole={prefs.role} {slots} />
    <TeamSlots side="enemy" bind:values={prefs.enemy} myRole={prefs.role} {slots} />
  </div>

  <div class="opts">
    <div>
      <label class="label" for="style">Comp style</label>
      <select id="style" bind:value={prefs.style}>
        <option value="">Any</option>
        {#each app.meta?.styles ?? [] as s (s)}<option value={s}>{capitalize(s)}</option>{/each}
      </select>
    </div>
    <div>
      <label class="label" for="need">Damage</label>
      <select id="need" bind:value={prefs.need}>
        <option value="">Auto{result?.need_detected ? ` (${result.need_detected.toUpperCase()})` : ""}</option>
        <option value="ap">Need AP</option>
        <option value="ad">Need AD</option>
      </select>
    </div>
  </div>

  <div class="field">
    <label for="unavailable">Unavailable (bans, fearless)</label>
    <ChipInput
      id="unavailable"
      bind:items={prefs.unavailable}
      names={app.meta?.names ?? []}
      placeholder="Type a name, press Enter"
    />
  </div>

  <div class="row foot">
    <span class="small muted">Fill in what you know. Empty slots are fine.</span>
    <button class="btn" onclick={clearDraft}>Clear draft</button>
  </div>
</div>

<style>
  .teams {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-top: 12px;
  }
  .opts {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 10px;
    margin-top: 12px;
  }
  .opts select {
    width: 100%;
  }
  .foot {
    margin-top: 12px;
    justify-content: space-between;
  }
  @media (max-width: 420px) {
    .teams {
      grid-template-columns: 1fr;
    }
  }
</style>
