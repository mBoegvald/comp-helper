<script lang="ts">
  import { initials } from "../../lib/format.ts";
  import { iconUrl } from "../../lib/icons.svelte.ts";

  let { name, size = "md" }: { name: string; size?: "sm" | "md" } = $props();

  const src = $derived(iconUrl(name));
  let failedSrc = $state<string | null>(null); // offline or no such icon: show initials
</script>

<span class="icon {size}" aria-hidden="true">
  {#if src && src !== failedSrc}
    <img {src} alt="" onerror={() => (failedSrc = src)} />
  {:else}
    {initials(name)}
  {/if}
</span>

<style>
  .icon {
    width: 48px;
    height: 48px;
    border-radius: 9px;
    background: var(--panel-2);
    display: grid;
    place-items: center;
    font-weight: 700;
    color: var(--muted);
    overflow: hidden;
    flex: none;
  }
  .icon.sm {
    width: 26px;
    height: 26px;
    border-radius: 6px;
    font-size: 11px;
  }
  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
  @media (max-width: 420px) {
    .icon.md {
      width: 40px;
      height: 40px;
    }
  }
</style>
