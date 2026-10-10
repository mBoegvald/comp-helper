<script lang="ts">
  import { errorMessage, getChampion } from "../../lib/api.ts";
  import { app } from "../../lib/app.svelte.ts";
  import { ROLE_LABEL } from "../../lib/constants.ts";
  import { debounce } from "../../lib/format.ts";
  import { prefs } from "../../lib/prefs.svelte.ts";
  import type { ChampionLookup, Role } from "../../lib/types.ts";
  import ErrorBox from "../common/ErrorBox.svelte";
  import RoleSwitch from "../common/RoleSwitch.svelte";
  import ChampionSummary from "./ChampionSummary.svelte";
  import MatchupPanel from "./MatchupPanel.svelte";
  import MatchupTable from "./MatchupTable.svelte";

  let data = $state<ChampionLookup | null>(null);
  let error = $state<string | null>(null);
  let filter = $state("");
  let selected = $state<string | null>(null);
  let latest = 0;
  let loadedFor = ""; // role|name of `data`: a new champion clears the selected matchup, a data refresh keeps it

  const load = debounce(async (role: Role, name: string) => {
    const id = ++latest;
    if (!name) {
      [data, selected, error] = [null, null, null];
      return;
    }
    try {
      const r = await getChampion(role, name);
      if (id !== latest) return;
      const key = `${role}|${r.champion.name}`;
      if (key !== loadedFor) selected = null;
      [data, error, loadedFor] = [r, null, key];
    } catch (e) {
      if (id === latest) error = errorMessage(e);
    }
  }, 300);

  $effect(() => {
    void app.dataVersion;
    load(prefs.lkRole, (prefs.lkChamp || "").trim());
  });
</script>

<div class="grid">
  <div class="panel">
    <h2>Look up a champion</h2>
    <RoleSwitch bind:value={prefs.lkRole} />
    <div class="field">
      <label for="lk-champ">Champion</label>
      <input id="lk-champ" list="champ-list" autocomplete="off" placeholder="e.g. Zed" bind:value={prefs.lkChamp} />
    </div>
    <div class="field">
      <label for="lk-filter">Filter opponents</label>
      <input id="lk-filter" autocomplete="off" placeholder="type to filter" bind:value={filter} />
    </div>
    {#if data}<ChampionSummary {data} />{/if}
  </div>

  <div>
    <ErrorBox message={error} />
    {#if data && selected}
      <MatchupPanel role={data.role} champ={data.champion.name} opp={selected} />
    {/if}
    {#if data?.matchups.length}
      <div class="panel">
        <div class="head">
          <h3>{data.champion.name} {ROLE_LABEL[data.role].toLowerCase()}: {data.matchups.length} matchups</h3>
          <span class="small muted">Click a row for the full matchup</span>
        </div>
        <MatchupTable rows={data.matchups} {filter} bind:selected />
      </div>
    {:else if data}
      <div class="empty">No {ROLE_LABEL[data.role].toLowerCase()} matchup data for {data.champion.name}.</div>
    {:else}
      <div class="empty">
        Pick a role and type a champion to see every matchup with win rates, notes and Reddit tips.
      </div>
    {/if}
  </div>
</div>
