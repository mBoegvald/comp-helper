<script lang="ts">
  import { suggestNames } from "../../lib/match.ts";
  import ChampIcon from "./ChampIcon.svelte";

  /** A champion name box with suggestions, usable from the keyboard (ARIA combobox): typing lists matches with the
   * best one highlighted, ↓/↑ move, Enter or Tab picks, Esc closes; clicking a suggestion picks it too. Keys the list
   * does not use go to `onkeydown`. */
  interface Props {
    value: string | undefined;
    names: readonly string[];
    id?: string;
    label?: string; // accessible name when no <label for> points at `id`
    placeholder?: string;
    title?: string;
    unknown?: boolean; // not a champion name: red border
    bare?: boolean; // no border, for use inside another box (the ban chips)
    onpick?: (name: string) => void;
    onkeydown?: (e: KeyboardEvent) => void;
  }
  let {
    value = $bindable(),
    names,
    id,
    label,
    placeholder = "",
    title,
    unknown = false,
    bare = false,
    onpick,
    onkeydown,
  }: Props = $props();

  const uid = $props.id();
  let open = $state(false);
  let active = $state(0);

  const options = $derived(open ? suggestNames(names, value ?? "") : []);
  const shown = $derived(options.length > 0);

  function pick(name: string) {
    value = name;
    open = false;
    onpick?.(name);
  }

  function keydown(e: KeyboardEvent) {
    if (shown) {
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        active = (active + (e.key === "ArrowDown" ? 1 : -1) + options.length) % options.length;
        return;
      }
      if (e.key === "Enter") {
        e.preventDefault();
        pick(options[active]);
        return;
      }
      if (e.key === "Tab" && !e.shiftKey) {
        pick(options[active]); // and focus moves on as usual
        return;
      }
      if (e.key === "Escape") {
        e.preventDefault();
        open = false;
        return;
      }
    } else if (e.key === "ArrowDown" && (value ?? "").trim()) {
      e.preventDefault();
      [open, active] = [true, 0];
      return;
    }
    onkeydown?.(e);
  }
</script>

<div class="combo" class:bare>
  <input
    {id}
    role="combobox"
    aria-label={label}
    aria-autocomplete="list"
    aria-expanded={shown}
    aria-controls="{uid}-list"
    aria-activedescendant={shown ? `${uid}-${active}` : undefined}
    autocomplete="off"
    spellcheck="false"
    {placeholder}
    {title}
    class:unknown
    bind:value
    oninput={() => ([open, active] = [true, 0])}
    onkeydown={keydown}
    onblur={() => (open = false)}
  />
  {#if shown}
    <ul id="{uid}-list" role="listbox" aria-label="Champions">
      {#each options as name, i (name)}
        <!-- the keyboard works on the input (aria-activedescendant); the mouse picks here without taking focus -->
        <li
          id="{uid}-{i}"
          role="option"
          aria-selected={i === active}
          onmousedown={(e) => {
            e.preventDefault();
            pick(name);
          }}
          onmousemove={() => (active = i)}
        >
          <ChampIcon {name} size="sm" />
          <span class="name">{name}</span>
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .combo {
    position: relative;
    display: block;
    width: 100%;
    min-width: 0;
  }
  input {
    width: 100%;
    min-width: 0;
  }
  input.unknown {
    border-color: var(--bad);
  }
  .bare input {
    border: 0;
    padding: 3px 4px;
    box-shadow: none !important;
  }
  ul {
    position: absolute;
    z-index: 10;
    top: calc(100% + 2px);
    left: 0;
    min-width: 100%;
    margin: 0;
    padding: 4px;
    list-style: none;
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 8px;
    box-shadow: var(--shadow);
  }
  li {
    display: flex;
    gap: 8px;
    align-items: center;
    padding: 4px 8px;
    border-radius: 6px;
    cursor: pointer;
    white-space: nowrap;
  }
  li[aria-selected="true"] {
    background: var(--you);
  }
</style>
