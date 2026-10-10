<script lang="ts">
  import { ROLE_LABEL } from "../../lib/constants.ts";
  import type { Recommendation } from "../../lib/types.ts";
  import PickCard from "./PickCard.svelte";

  /** /api/recommend's answer. `needChosen` is true when the damage need was picked by hand rather than detected. */
  let { result, needChosen }: { result: Recommendation; needChosen: boolean } = $props();

  const role = $derived(ROLE_LABEL[result.role].toLowerCase());
  const title = $derived(
    result.enemy_main ? `Best ${role} picks into ${result.enemy_main}` : `Best ${role} blind picks`,
  );
  const meta = $derived.by(() => {
    const bits = [`${result.candidates} candidates`];
    if (result.style) bits.push(`${result.style} comp`);
    if (result.need)
      bits.push(needChosen ? `needs ${result.need.toUpperCase()}` : `auto: team needs ${result.need.toUpperCase()}`);
    else if (!needChosen) bits.push("damage balanced");
    return bits.join(" · ");
  });
  const maxScore = $derived(Math.max(...result.picks.map((p) => p.score), 1));
</script>

<div class="head">
  <h3 class="title">{title}</h3>
  <span class="small muted">{meta}</span>
</div>

<div class="cards">
  {#each result.picks as pick, i (pick.key)}
    <PickCard {pick} role={result.role} rank={i + 1} {maxScore} />
  {:else}
    <div class="empty">No candidates left. Check the unavailable list.</div>
  {/each}
</div>

{#if result.avoid.length}
  <div class="avoid">
    <h2>Avoid</h2>
    <div class="cards">
      {#each result.avoid as pick (pick.key)}<PickCard {pick} role={result.role} compact />{/each}
    </div>
  </div>
{/if}

<style>
  .title {
    font-size: 17px;
  }
  .cards {
    display: grid;
    gap: 10px;
  }
  .avoid {
    margin-top: 16px;
  }
</style>
