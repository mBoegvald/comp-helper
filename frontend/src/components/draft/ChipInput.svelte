<script lang="ts">
  import ChampInput from "../common/ChampInput.svelte";

  /** Names as removable chips: type and press Enter or comma, or pick from the suggestions; Backspace removes the last. */
  interface Props {
    items: string[];
    names?: string[];
    id?: string;
    placeholder?: string;
  }
  let { items = $bindable(), names = [], id, placeholder = "" }: Props = $props();

  let text = $state("");

  function add(value: string) {
    const v = value.trim();
    if (!v) return;
    const canon = names.find((n) => n.toLowerCase() === v.toLowerCase()) || v;
    if (!items.some((n) => n.toLowerCase() === canon.toLowerCase())) items.push(canon);
    text = "";
  }

  function onkeydown(e: KeyboardEvent) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      add(text);
    } else if (e.key === "Backspace" && !text && items.length) {
      items.pop();
    }
  }
</script>

<div class="chips">
  {#each items as name, i (name)}
    <span class="chip">
      {name}
      <button type="button" title="Remove" aria-label="Remove {name}" onclick={() => items.splice(i, 1)}>×</button>
    </span>
  {/each}
  <ChampInput {id} {names} {placeholder} bare bind:value={text} onpick={add} {onkeydown} />
</div>

<style>
  .chips {
    display: flex;
    flex-wrap: wrap;
    gap: 5px;
    align-items: center;
    border: 1px solid var(--line);
    border-radius: 7px;
    padding: 4px;
    background: var(--panel);
  }
  .chips :global(.combo) {
    flex: 1;
    width: auto;
    min-width: 110px;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: var(--panel-2);
    border: 1px solid var(--line);
    border-radius: 99px;
    padding: 1px 4px 1px 9px;
    font-size: 12px;
  }
  button {
    border: 0;
    background: none;
    cursor: pointer;
    color: var(--muted);
    padding: 0 4px;
    font-size: 14px;
    line-height: 1;
  }
</style>
