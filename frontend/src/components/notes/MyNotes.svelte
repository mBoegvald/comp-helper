<script lang="ts">
  import { app } from "../../lib/app.svelte.ts";
  import { errorMessage, getMyNotes } from "../../lib/api.ts";
  import { ROLE_LABEL } from "../../lib/constants.ts";
  import type { NoteStatus, Suggestion } from "../../lib/types.ts";
  import ErrorBox from "../common/ErrorBox.svelte";

  const STATUS: Record<NoteStatus, string> = {
    pending: "Waiting for review",
    approved: "Approved",
    rejected: "Rejected",
  };

  let mine = $state<Suggestion[] | null>(null);
  let error = $state<string | null>(null);

  // reload each time the tab is opened, so a fresh review shows
  $effect(() => {
    if (app.view !== "mine") return;
    getMyNotes().then(
      (r) => ([mine, error] = [r.notes, null]),
      (e) => (error = errorMessage(e)),
    );
  });
</script>

<div class="mine">
  <div class="panel">
    <h2>My notes</h2>
    <ErrorBox message={error} />
    {#if mine && !mine.length}
      <p class="muted">
        You have not suggested any notes yet. Open a champion or a matchup in Lookup and choose “Suggest a note”.
      </p>
    {/if}
    {#each mine ?? [] as n (n.id)}
      <article>
        <div class="head">
          <b>{ROLE_LABEL[n.role]} · {n.champion}{n.opponent ? ` vs ${n.opponent}` : ""}</b>
          <span class="status {n.status}">{STATUS[n.status]}</span>
        </div>
        <p class="text">{n.text}</p>
        <div class="small muted">
          {n.created_at.slice(0, 10)}{n.source ? ` · source: ${n.source}` : ""}
          {#if n.review_note}· reason: {n.review_note}{/if}
        </div>
      </article>
    {/each}
  </div>
</div>

<style>
  .mine {
    max-width: 760px;
  }
  article {
    border-top: 1px solid var(--line);
    padding: 10px 0;
  }
  .head {
    margin-bottom: 4px;
  }
  .text {
    margin: 0 0 4px;
    overflow-wrap: anywhere;
  }
  .status {
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 99px;
  }
  .pending {
    color: var(--warn);
    background: var(--warn-bg);
  }
  .approved {
    color: var(--good);
    background: var(--good-bg);
  }
  .rejected {
    color: var(--bad);
    background: var(--bad-bg);
  }
</style>
