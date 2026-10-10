<script lang="ts">
  import { dataChanged } from "../../lib/app.svelte.ts";
  import { deleteNote, errorMessage, promoteNote } from "../../lib/api.ts";
  import { safeLink } from "../../lib/format.ts";
  import { session } from "../../lib/session.svelte.ts";
  import type { CommunityNote } from "../../lib/types.ts";
  import ErrorBox from "../common/ErrorBox.svelte";

  /** Approved community notes. For a matchup, notes from the other side say whose side they are, and admins can
   * make a note the lane tip of its side; `tipOwners` are the sides that already have one. */
  let {
    notes,
    champ = "",
    tipOwners = [],
  }: { notes: CommunityNote[]; champ?: string; tipOwners?: string[] } = $props();

  let error = $state<string | null>(null);
  let confirming = $state<number | null>(null); // note id waiting for a second click to delete
  let promoting = $state<number | null>(null); // ... to become the lane tip

  async function promote(id: number) {
    if (promoting !== id) {
      [promoting, confirming] = [id, null]; // one confirm at a time
      return;
    }
    promoting = null;
    try {
      await promoteNote(id);
      error = null;
      dataChanged();
    } catch (e) {
      error = errorMessage(e);
    }
  }

  async function remove(id: number) {
    if (confirming !== id) {
      [confirming, promoting] = [id, null];
      return;
    }
    confirming = null;
    try {
      await deleteNote(id);
      error = null;
      dataChanged();
    } catch (e) {
      error = errorMessage(e);
    }
  }
</script>

{#if notes.length}
  <section>
    <h5>Community notes</h5>
    <ErrorBox message={error} />
    {#each notes as n (n.id)}
      {@const link = safeLink(n.source)}
      <div class="note">
        {n.who && n.who !== champ ? `${n.who}'s side: ` : ""}{n.text}
        <div class="meta">
          {n.author ?? "a removed account"}{n.approved_at ? ` · ${n.approved_at.slice(0, 10)}` : ""}
          {#if n.source}
            · source:
            {#if link}<a href={link} target="_blank" rel="noopener noreferrer nofollow ugc">{n.source}</a
              >{:else}{n.source}{/if}
          {/if}
          {#if session.hosted && session.admin && n.who}
            <button
              class="btn link del"
              class:danger={promoting === n.id && tipOwners.includes(n.who)}
              onclick={() => promote(n.id)}
            >
              {promoting !== n.id
                ? "Make this the lane tip"
                : tipOwners.includes(n.who)
                  ? `Replace ${n.who}'s lane tip?`
                  : "Make it the lane tip?"}
            </button>
          {/if}
          {#if session.hosted && session.admin}
            <button class="btn link del" class:danger={confirming === n.id} onclick={() => remove(n.id)}>
              {confirming === n.id ? "Really delete?" : "Delete"}
            </button>
          {/if}
        </div>
      </div>
    {/each}
  </section>
{/if}

<style>
  h5 {
    margin: 0 0 4px;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--muted);
  }
  .note {
    background: var(--panel-2);
    border-left: 3px solid var(--good);
    padding: 6px 10px;
    border-radius: 0 6px 6px 0;
    font-size: 13px;
    overflow-wrap: anywhere;
  }
  .note + .note {
    margin-top: 4px;
  }
  .meta {
    font-size: 11px;
    color: var(--muted);
    margin-top: 3px;
  }
  .del {
    margin-left: 6px;
    font-size: 11px;
  }
  .del.danger {
    color: var(--bad);
  }
</style>
