<script lang="ts">
  import { openLookup } from "../../lib/app.svelte.ts";
  import { signed } from "../../lib/format.ts";
  import type { Pick, Role } from "../../lib/types.ts";
  import ChampFacts from "../common/ChampFacts.svelte";
  import ChampIcon from "../common/ChampIcon.svelte";
  import LaneStats from "../common/LaneStats.svelte";
  import MatchupNotes from "../common/MatchupNotes.svelte";
  import ReasonChip from "../common/ReasonChip.svelte";

  /** One suggested pick. `compact` is the short form used in the Avoid list. */
  interface Props {
    pick: Pick;
    role: Role;
    rank?: number;
    maxScore?: number;
    compact?: boolean;
  }
  let { pick, role, rank = 0, maxScore = 1, compact = false }: Props = $props();

  let open = $state(false);
  const meter = $derived(Math.max(4, Math.min(100, (pick.score / (maxScore || 1)) * 100)));
  const sub = $derived([pick.arch, pick.dmg, pick.blind === "Yes" ? "blind-safe" : null].filter(Boolean).join(" · "));
</script>

<article class="card">
  <div class="top">
    <div class="rank">{compact ? "" : rank}</div>
    <ChampIcon name={pick.name} />
    <div>
      <div class="name">{pick.name}</div>
      <div class="sub">{sub}</div>
    </div>
    <div class="score">
      <b>{signed(pick.score)}</b>
      {#if !compact}<div class="meter"><i style:width="{meter}%"></i></div>{/if}
    </div>
  </div>

  {#if !compact && pick.lane?.wr != null}
    <div class="lane"><LaneStats m={pick.lane} opp={pick.lane.opp} /></div>
  {/if}

  <div class="reasons" class:last={compact}>
    {#each pick.parts as part, i (i)}<ReasonChip {part} />{:else}
      <span class="small muted">No specific reasons, ranked on general fit</span>
    {/each}
  </div>

  {#if !compact}
    <details bind:open>
      <summary>{pick.lane ? "Lane notes, Reddit tips and champion info" : "Champion info"}</summary>
      {#if open}
        <div class="detail">
          {#if pick.lane}<MatchupNotes m={pick.lane} champ={pick.name} />{/if}
          <section>
            <div class="head">
              <h5>{pick.name}</h5>
              <button class="btn link small" onclick={() => openLookup(role, pick.name)}
                >All matchups and notes →</button
              >
            </div>
            <ChampFacts champ={pick} />
          </section>
        </div>
      {/if}
    </details>
  {/if}
</article>

<style>
  .card {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
  }
  .top {
    display: grid;
    grid-template-columns: 30px 48px 1fr auto;
    gap: 12px;
    align-items: center;
    padding: 12px 14px 8px;
  }
  .rank {
    font-size: 18px;
    font-weight: 700;
    color: var(--muted);
    text-align: center;
  }
  .name {
    font-size: 16px;
    font-weight: 700;
  }
  .sub {
    font-size: 12px;
    color: var(--muted);
  }
  .score {
    text-align: right;
  }
  .score b {
    font-size: 20px;
    font-variant-numeric: tabular-nums;
  }
  .meter {
    width: 90px;
    height: 6px;
    background: var(--panel-2);
    border-radius: 99px;
    overflow: hidden;
    margin-top: 4px;
  }
  .meter i {
    display: block;
    height: 100%;
    background: var(--accent);
    border-radius: 99px;
  }
  .lane {
    margin: 0 14px;
  }
  .reasons {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    padding: 8px 14px 0;
  }
  .reasons.last {
    padding-bottom: 12px;
  }
  details {
    padding: 6px 14px 12px;
  }
  summary {
    cursor: pointer;
    color: var(--accent);
    font-size: 13px;
    font-weight: 600;
    padding: 4px 0;
    list-style: none;
  }
  summary::-webkit-details-marker {
    display: none;
  }
  summary::before {
    content: "▸ ";
  }
  details[open] summary::before {
    content: "▾ ";
  }
  .detail {
    display: grid;
    gap: 12px;
    margin-top: 6px;
  }
  .head {
    margin-bottom: 4px;
  }
  h5 {
    margin: 0;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--muted);
  }
  @media (max-width: 420px) {
    .top {
      grid-template-columns: 22px 40px 1fr auto;
      gap: 8px;
    }
  }
</style>
