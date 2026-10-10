<script lang="ts">
  import { app } from "../../lib/app.svelte.ts";
  import { ROLE_LABEL, ROLE_SHORT, ROLES } from "../../lib/constants.ts";
  import type { Role, Slot } from "../../lib/types.ts";
  import ChampInput from "../common/ChampInput.svelte";

  /** Five name inputs for one team. `slots` is /api/recommend's reading of each typed name. */
  interface Props {
    side: "ally" | "enemy";
    values: Partial<Record<Role, string>>;
    myRole: Role;
    slots?: Record<string, Slot>;
  }
  let { side, values = $bindable(), myRole, slots = {} }: Props = $props();

  function check(role: Role) {
    const typed = (values[role] || "").trim();
    const s = slots[`${side}.${role}`];
    if (!typed || !s) return { unknown: false, title: "" };
    if (!s.known) return { unknown: true, title: "Unknown champion name" };
    const readAs = s.name && s.name.toLowerCase() !== typed.toLowerCase() ? `Read as ${s.name}` : "";
    return { unknown: false, title: readAs };
  }
</script>

<div>
  <h4>{side === "ally" ? "Your team" : "Enemy team"}</h4>
  {#each ROLES as r (r)}
    {@const you = side === "ally" && r === myRole}
    {@const lane = side === "enemy" && r === myRole}
    {@const c = check(r)}
    <div class="slot" class:you class:lane>
      <span class="r">{ROLE_SHORT[r]}</span>
      {#if you}
        <input placeholder="You" disabled aria-label="Your {ROLE_LABEL[r]} (you)" />
      {:else}
        <ChampInput
          names={app.meta?.names ?? []}
          placeholder={lane ? "Lane opponent" : ROLE_LABEL[r]}
          label="{side === 'ally' ? 'Your' : 'Enemy'} {ROLE_LABEL[r]}"
          unknown={c.unknown}
          title={c.title}
          bind:value={values[r]}
        />
      {/if}
    </div>
  {/each}
</div>

<style>
  h4 {
    margin: 0 0 6px;
    font-size: 12px;
    color: var(--muted);
    font-weight: 600;
  }
  .slot {
    display: grid;
    grid-template-columns: 26px 1fr;
    align-items: center;
    gap: 6px;
    margin-bottom: 5px;
  }
  .r {
    font-size: 11px;
    color: var(--muted);
    font-weight: 700;
    text-transform: uppercase;
  }
  .you input {
    width: 100%;
    min-width: 0;
    background: var(--you);
    border-style: dashed;
    font-weight: 600;
  }
  .lane :global(input) {
    border-color: var(--accent);
  }
</style>
