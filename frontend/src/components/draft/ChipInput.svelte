<script lang="ts">
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
  <input
    {id}
    list="champ-list"
    autocomplete="off"
    {placeholder}
    bind:value={text}
    {onkeydown}
    onchange={() => names.includes(text) && add(text)}
  />
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
  input {
    border: 0;
    flex: 1;
    min-width: 110px;
    padding: 3px 4px;
    box-shadow: none !important;
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
