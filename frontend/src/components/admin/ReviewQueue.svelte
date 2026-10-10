<script lang="ts">
  import { ROLE_LABEL } from "../../lib/constants.ts";
  import { safeLink } from "../../lib/format.ts";
  import { decide, review } from "../../lib/review.svelte.ts";
  import ErrorBox from "../common/ErrorBox.svelte";

  // per note: the text as the admin may correct it, and an optional reason for rejecting
  let edits = $state<Record<number, string>>({});
  let reasons = $state<Record<number, string>>({});
  let busy = $state<number | null>(null);

  async function act(id: number, approve: boolean, original: string) {
    busy = id;
    const text = edits[id] ?? original;
    await decide(id, approve, approve && text !== original ? text : undefined, approve ? undefined : reasons[id]);
    busy = null;
  }
</script>

<div class="panel">
  <h2>Waiting for review ({review.notes.length})</h2>
  <ErrorBox message={review.error} />
  {#if !review.notes.length}
    <p class="small muted">Nothing to review. New suggestions show up here.</p>
  {/if}
  {#each review.notes as n (n.id)}
    {@const link = safeLink(n.source)}
    <article>
      <div class="head">
        <b>{ROLE_LABEL[n.role]} · {n.champion}{n.opponent ? ` vs ${n.opponent}` : " (the champion)"}</b>
        <span class="small muted">{n.author ?? "a removed account"} · {n.created_at.slice(0, 10)}</span>
      </div>
      <label class="label" for="review-{n.id}">Note (fix it before approving if needed)</label>
      <textarea
        id="review-{n.id}"
        rows="3"
        value={edits[n.id] ?? n.text}
        oninput={(e) => (edits[n.id] = e.currentTarget.value)}></textarea>
      {#if n.source}
        <p class="small muted">
          Source: {#if link}<a href={link} target="_blank" rel="noopener noreferrer nofollow ugc">{n.source}</a
            >{:else}{n.source}{/if}
        </p>
      {/if}
      <div class="row actions">
        <button class="btn primary" disabled={busy === n.id} onclick={() => act(n.id, true, n.text)}>Approve</button>
        <input
          aria-label="Reason for rejecting (optional)"
          placeholder="Reason for rejecting (optional)"
          bind:value={reasons[n.id]}
        />
        <button class="btn danger" disabled={busy === n.id} onclick={() => act(n.id, false, n.text)}>Reject</button>
      </div>
    </article>
  {/each}
</div>

<style>
  article {
    border-top: 1px solid var(--line);
    padding: 10px 0;
  }
  .head {
    margin-bottom: 6px;
  }
  textarea {
    width: 100%;
    resize: vertical;
  }
  p {
    margin: 4px 0 0;
    overflow-wrap: anywhere;
  }
  .actions {
    margin-top: 8px;
  }
  .actions input {
    flex: 1;
    min-width: 160px;
  }
</style>
