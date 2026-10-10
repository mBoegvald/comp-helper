<script lang="ts">
  import { DIFF_HELP } from "../../lib/constants.ts";
  import { percent, signed } from "../../lib/format.ts";
  import type { Matchup } from "../../lib/types.ts";
  import ResultTag from "./ResultTag.svelte";

  /** Win-rate line for one matchup. `opp` is shown when the context does not already name the opponent. */
  let { m, opp = "" }: { m: Pick<Matchup, "wr" | "dnorm" | "games" | "label" | "low_sample">; opp?: string } = $props();
</script>

<div class="lane">
  {#if opp}<span>vs <b>{opp}</b></span>{/if}
  <span>Win rate <b>{percent(m.wr)}</b></span>
  <span title={DIFF_HELP}><b>{signed(m.dnorm)}</b> vs usual</span>
  <span><b>{m.games}</b> games</span>
  <ResultTag label={m.label} low={m.low_sample} />
</div>

<style>
  .lane {
    padding: 8px 10px;
    border-radius: 8px;
    background: var(--panel-2);
    display: flex;
    gap: 10px 16px;
    flex-wrap: wrap;
    align-items: center;
    font-size: 13px;
  }
  b {
    font-variant-numeric: tabular-nums;
  }
</style>
