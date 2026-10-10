<script lang="ts">
  import type { Champion } from "../../lib/types.ts";

  /** The champion's notes for a role: curated, or the defaults from role_data.py. */
  let { champ }: { champ: Champion } = $props();

  const rows = $derived(
    (
      [
        ["Pick when", champ.when],
        ["Comps", champ.comps],
        ["Good into", champ.good],
        ["Struggles into", champ.bad],
        ["Blind pick", champ.blind],
      ] as const
    ).filter(([, v]) => v),
  );
</script>

<dl>
  {#each rows as [k, v] (k)}
    <dt>{k}</dt>
    <dd>{v}</dd>
  {/each}
</dl>

<style>
  dl {
    display: grid;
    grid-template-columns: 120px 1fr;
    gap: 3px 10px;
    font-size: 13px;
    margin: 0;
  }
  dt {
    color: var(--muted);
  }
  dd {
    margin: 0;
  }
</style>
