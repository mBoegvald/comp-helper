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
    <!-- an edit of an approved note: the approved text stays on the site; decide on the edited text -->
    {@const isEdit = n.revised_text !== null}
    {@const proposed = n.revised_text ?? n.text}
    {@const source = isEdit ? n.revised_source : n.source}
    {@const link = safeLink(source)}
    <article>
      <div class="head">
        <b>
          {ROLE_LABEL[n.role]} · {n.champion}{n.opponent ? ` vs ${n.opponent}` : " (the champion)"}
          {#if isEdit}<span class="kind">Edit</span>{/if}
        </b>
        <span class="small muted">
          {n.author ?? "a removed account"} · {(n.revised_at ?? n.created_at).slice(0, 10)}
        </span>
      </div>
      {#if isEdit}
        <p class="now"><span class="small muted">Now on the site:</span> {n.text}</p>
      {/if}
      <label class="label" for="review-{n.id}">
        {isEdit ? "Edited note" : "Note"} (fix it before approving if needed)
      </label>
      <textarea
        id="review-{n.id}"
        rows="3"
        value={edits[n.id] ?? proposed}
        oninput={(e) => (edits[n.id] = e.currentTarget.value)}></textarea>
      {#if source}
        <p class="small muted">
          Source: {#if link}<a href={link} target="_blank" rel="noopener noreferrer nofollow ugc">{source}</a
            >{:else}{source}{/if}
        </p>
      {/if}
      <div class="row actions">
        <button class="btn primary" disabled={busy === n.id} onclick={() => act(n.id, true, proposed)}>
          {isEdit ? "Approve edit" : "Approve"}
        </button>
        <input
          aria-label="Reason for rejecting (optional)"
          placeholder="Reason for rejecting (optional)"
          bind:value={reasons[n.id]}
        />
        <button class="btn danger" disabled={busy === n.id} onclick={() => act(n.id, false, proposed)}>
          {isEdit ? "Reject edit" : "Reject"}
        </button>
      </div>
    </article>
  {/each}
</div>

<style>
  .kind {
    font-size: 11px;
    font-weight: 700;
    padding: 1px 6px;
    margin-left: 6px;
    border-radius: 99px;
    color: var(--warn);
    background: var(--warn-bg);
  }
  .now {
    margin: 0 0 6px;
    padding-left: 8px;
    border-left: 3px solid var(--good);
    overflow-wrap: anywhere;
  }
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
