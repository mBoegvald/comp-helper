<script lang="ts">
  import { ROLE_LABEL, ROLES } from "../../lib/constants.ts";
  import type { Role } from "../../lib/types.ts";

  let { value = $bindable(), label = "Role" }: { value: Role; label?: string } = $props();
</script>

<div class="seg" role="group" aria-label={label}>
  {#each ROLES as r (r)}
    <button type="button" aria-pressed={r === value} onclick={() => (value = r)}>{ROLE_LABEL[r]}</button>
  {/each}
</div>

<style>
  .seg {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    background: var(--panel-2);
    border: 1px solid var(--line);
    border-radius: 9px;
    padding: 3px;
    gap: 3px;
  }
  button {
    border: 0;
    background: none;
    padding: 7px 0;
    border-radius: 7px;
    cursor: pointer;
    font-weight: 600;
    color: var(--muted);
  }
  button[aria-pressed="true"] {
    background: var(--accent);
    color: var(--accent-text);
  }
  @media (max-width: 420px) {
    button {
      font-size: 12px;
    }
  }
</style>
