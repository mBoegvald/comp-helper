<script lang="ts">
  import { app, type View } from "../../lib/app.svelte.ts";
  import { review } from "../../lib/review.svelte.ts";
  import { logout, session } from "../../lib/session.svelte.ts";

  let { view = $bindable(), onsignin }: { view: View; onsignin?: () => void } = $props();

  const tabs = $derived<{ id: View; label: string }[]>([
    { id: "draft", label: "Draft" },
    { id: "lookup", label: "Lookup" },
    { id: "data", label: "Data" },
    ...(session.hosted && session.user ? [{ id: "mine" as const, label: "My notes" }] : []),
    ...(session.hosted && session.admin ? [{ id: "admin" as const, label: "Admin" }] : []),
  ]);
</script>

<header>
  <div class="bar">
    <span class="brand">Pick Helper</span>
    <div class="pills">
      {#if app.meta?.patch}<span class="pill" title="Lolalytics patch and rank">Patch {app.meta.patch}</span>{/if}
      {#if app.meta}
        <span class="pill" title="Champions with Reddit data">Reddit: {app.meta.reddit_champions} champions</span>
      {/if}
      {#if app.running}<span class="pill run">Update running</span>{/if}
    </div>
    <div class="tabs" role="tablist" aria-label="Views">
      {#each tabs as t (t.id)}
        <button role="tab" aria-selected={view === t.id} onclick={() => (view = t.id)}>
          {t.label}{#if t.id === "admin" && review.notes.length}<span class="badge" title="Notes waiting for review"
              >{review.notes.length}</span
            >{/if}
        </button>
      {/each}
    </div>
    {#if session.hosted}
      <div class="account">
        {#if session.user}
          <span class="small muted">{session.user.username}{session.admin ? " (admin)" : ""}</span>
          <button class="btn" onclick={logout}>Sign out</button>
        {:else}
          <button class="btn primary" onclick={onsignin}>Sign in</button>
        {/if}
      </div>
    {/if}
  </div>
</header>

<style>
  header {
    position: sticky;
    top: 0;
    z-index: 5;
    background: var(--panel);
    border-bottom: 1px solid var(--line);
  }
  .bar {
    max-width: 1240px;
    margin: 0 auto;
    padding: 10px 16px;
    display: flex;
    gap: 12px;
    align-items: center;
    flex-wrap: wrap;
  }
  .brand {
    font-weight: 700;
    font-size: 16px;
    margin-right: 4px;
  }
  .pills {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
  .pill {
    font-size: 12px;
    color: var(--muted);
    background: var(--panel-2);
    border: 1px solid var(--line);
    border-radius: 99px;
    padding: 2px 9px;
    white-space: nowrap;
  }
  .pill.run {
    color: var(--warn);
    background: var(--warn-bg);
    border-color: transparent;
  }
  .tabs {
    margin-left: auto;
    display: flex;
    gap: 4px;
  }
  .tabs button {
    border: 0;
    background: none;
    padding: 7px 12px;
    border-radius: 8px;
    cursor: pointer;
    color: var(--muted);
    font-weight: 600;
  }
  .badge {
    margin-left: 6px;
    font-size: 11px;
    padding: 1px 6px;
    border-radius: 99px;
    background: var(--warn-bg);
    color: var(--warn);
  }
  .account {
    display: flex;
    gap: 8px;
    align-items: center;
  }
  .tabs button[aria-selected="true"] {
    background: var(--panel-2);
    color: var(--text);
  }
  @media (max-width: 900px) {
    .tabs {
      margin-left: 0;
    }
  }
</style>
