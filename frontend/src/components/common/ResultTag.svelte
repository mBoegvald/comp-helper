<script lang="ts">
  import { LOW_SAMPLE_HELP } from "../../lib/constants.ts";
  import type { Label } from "../../lib/types.ts";

  let { label = null, low = false }: { label?: Label | null; low?: boolean } = $props();
</script>

{#if label}<span class="tag {label}">{label}</span>{/if}
{#if low}<span class="tag low" title={LOW_SAMPLE_HELP}>low sample</span>{/if}

<style>
  .tag {
    display: inline-block;
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 99px;
  }
  .Favored {
    color: var(--good);
    background: var(--good-bg);
  }
  .Unfavored {
    color: var(--bad);
    background: var(--bad-bg);
  }
  .Even {
    color: var(--even);
    background: var(--even-bg);
  }
  .low {
    color: var(--warn);
    background: var(--warn-bg);
  }
</style>
