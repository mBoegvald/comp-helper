<script lang="ts">
  import { dataChanged } from "../../lib/app.svelte.ts";
  import { deleteNote, errorMessage } from "../../lib/api.ts";
  import { safeLink } from "../../lib/format.ts";
  import { session } from "../../lib/session.svelte.ts";
  import type { CommunityNote } from "../../lib/types.ts";
  import ErrorBox from "../common/ErrorBox.svelte";

  /** Approved community notes. For a matchup, notes from the other side say whose side they are. */
  let { notes, champ = "" }: { notes: CommunityNote[]; champ?: string } = $props();

  let error = $state<string | null>(null);
  let confirming = $state<number | null>(null); // note id waiting for a second click

  async function remove(id: number) {
    if (confirming !== id) {
      confirming = id;
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
