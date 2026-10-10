<script lang="ts">
  import { dataChanged } from "../../lib/app.svelte.ts";
  import { ROLE_LABEL } from "../../lib/constants.ts";
  import type { ChampionLookup } from "../../lib/types.ts";
  import ChampFacts from "../common/ChampFacts.svelte";
  import ChampIcon from "../common/ChampIcon.svelte";
  import ChampionEditor from "../edit/ChampionEditor.svelte";

  let { data }: { data: ChampionLookup } = $props();

  let editing = $state(false);

  const champ = $derived(data.champion);

  // another champion or role: close the editor
  $effect.pre(() => {
    void data.role;
    void champ.name;
    editing = false;
  });
  const sub = $derived(
    data.in_role
      ? [champ.arch, champ.dmg].filter(Boolean).join(" · ")
      : `Not in the ${ROLE_LABEL[data.role].toLowerCase()} pool`,
  );
</script>

<div class="summary">
  <div class="row">
    <ChampIcon name={champ.name} />
    <div class="who">
      <div class="name">{champ.name}</div>
      <div class="small muted">{sub}</div>
    </div>
    {#if data.in_role && !editing}
      <button class="btn" onclick={() => (editing = true)}>Edit notes</button>
    {/if}
  </div>
  {#if editing}
    {#key data.role + champ.name}
      <ChampionEditor
        role={data.role}
        name={champ.name}
        onsaved={() => {
          editing = false;
          dataChanged();
        }}
        oncancel={() => (editing = false)}
      />
    {/key}
  {:else if data.in_role}
    <div class="facts"><ChampFacts {champ} /></div>
  {/if}
</div>

<style>
  .summary {
    margin-top: 12px;
  }
  .who {
    flex: 1;
  }
  .name {
    font-size: 16px;
    font-weight: 700;
  }
  .facts {
    margin-top: 10px;
  }
</style>
