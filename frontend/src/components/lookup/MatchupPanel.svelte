<script lang="ts">
  import { errorMessage, getMatchup } from "../../lib/api.ts";
  import { app, dataChanged } from "../../lib/app.svelte.ts";
  import { session } from "../../lib/session.svelte.ts";
  import type { Matchup, Role } from "../../lib/types.ts";
  import ChampIcon from "../common/ChampIcon.svelte";
  import ErrorBox from "../common/ErrorBox.svelte";
  import LaneStats from "../common/LaneStats.svelte";
  import MatchupNotes from "../common/MatchupNotes.svelte";
  import MatchupEditor from "../edit/MatchupEditor.svelte";
  import SuggestNote from "../notes/SuggestNote.svelte";

  /** Everything about one pair in one role, from `champ`'s side. */
  let { role, champ, opp }: { role: Role; champ: string; opp: string } = $props();

  let m = $state<Matchup | null>(null);
  let error = $state<string | null>(null);
  let panel = $state<HTMLDivElement>();
  let editing = $state(false);

  // another opponent: close the editor
  $effect.pre(() => {
    void opp;
    editing = false;
  });

  $effect(() => {
    void app.dataVersion;
    const want = { role, champ, opp };
    getMatchup(role, champ, opp).then(
      (r) => {
        if (want.role === role && want.champ === champ && want.opp === opp) [m, error] = [r, null];
      },
      (e) => (error = errorMessage(e)),
    );
  });

  // bring a newly opened matchup into view
  $effect(() => {
    void opp;
    panel?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  });

  function saved(updated: Matchup) {
    m = updated;
    editing = false;
    dataChanged();
  }
</script>

<div class="panel" bind:this={panel}>
  <ErrorBox message={error} />
  {#if m}
    <div class="row title">
      <ChampIcon name={m.champ} />
      <h3>{m.champ} vs {m.opp}</h3>
      <ChampIcon name={m.opp} />
      {#if session.admin && !editing}<button class="btn edit" onclick={() => (editing = true)}>Edit</button>{/if}
    </div>
    {#if m.wr != null}
      <div class="stats"><LaneStats {m} /></div>
    {:else}
      <p class="small muted">No win-rate data for this pair.</p>
    {/if}
    <MatchupNotes {m} champ={m.champ} />
    <SuggestNote {role} champion={m.champ} opponent={m.opp} />
    {#if editing}
      {#key m.opp}
        <MatchupEditor {role} {m} onsaved={saved} oncancel={() => (editing = false)} />
      {/key}
    {/if}
  {/if}
</div>

<style>
  .title {
    margin-bottom: 10px;
  }
  .edit {
    margin-left: auto;
  }
  .stats {
    margin-bottom: 10px;
  }
</style>
