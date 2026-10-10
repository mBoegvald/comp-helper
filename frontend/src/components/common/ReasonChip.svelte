<script lang="ts">
  import { percent, signed } from "../../lib/format.ts";
  import type { Part } from "../../lib/types.ts";

  /** One scoring reason from /api/recommend. */
  let { part }: { part: Part } = $props();

  const text = $derived.by(() => {
    if (part.kind !== "matchup") return part.text;
    if (part.main) return `lane vs ${part.enemy_name}`;
    const bits = [part.wr != null ? percent(part.wr) : null, part.games ? `${part.games} games` : null].filter(Boolean);
    return `vs ${part.enemy_name}${bits.length ? " · " + bits.join(", ") : ""}`;
  });
</script>

<span
  class="reason"
  class:pos={part.value > 0}
  class:neg={part.value < 0}
  title={part.kind === "matchup" && !part.main ? "Other enemies count one third" : undefined}
>
  <b>{signed(part.value)}</b>
  {text}
</span>

<style>
  .reason {
    font-size: 12px;
    padding: 2px 8px;
    border-radius: 6px;
    border: 1px solid var(--line);
    background: var(--panel);
    white-space: nowrap;
  }
  b {
    font-variant-numeric: tabular-nums;
  }
  .pos {
    border-color: color-mix(in srgb, var(--good) 40%, var(--line));
  }
  .pos b {
    color: var(--good);
  }
  .neg {
    border-color: color-mix(in srgb, var(--bad) 40%, var(--line));
  }
  .neg b {
    color: var(--bad);
  }
</style>
