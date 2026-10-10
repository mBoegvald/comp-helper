<script lang="ts">
  import { dataChanged } from "../../lib/app.svelte.ts";
  import { editNote, errorMessage, withdrawNote } from "../../lib/api.ts";
  import { ROLE_LABEL } from "../../lib/constants.ts";
  import { session } from "../../lib/session.svelte.ts";
  import type { Suggestion } from "../../lib/types.ts";
  import ErrorBox from "../common/ErrorBox.svelte";

  /** One of your notes: its status, and Edit / Withdraw. Edits wait for review again (admins' apply at once). */
  let { note, onchanged }: { note: Suggestion; onchanged: () => void } = $props();

  const uid = $props.id();
  let editing = $state(false);
  let text = $state("");
  let source = $state("");
  let error = $state<string | null>(null);
  let busy = $state(false);
  let confirmWithdraw = $state(false);

  const status = $derived.by(() => {
    if (note.revised_text !== null) return { cls: "pending", label: "Edit waiting for review" };
    if (note.status === "pending") return { cls: "pending", label: "Waiting for review" };
    if (note.status === "rejected") return { cls: "rejected", label: "Rejected" };
    return { cls: "approved", label: "Approved" };
  });

  function startEdit() {
    [text, source] = [
      note.revised_text ?? note.text,
      (note.revised_text !== null ? note.revised_source : note.source) ?? "",
    ];
    [editing, error, confirmWithdraw] = [true, null, false];
  }

  async function save(e: SubmitEvent) {
    e.preventDefault();
    busy = true;
    try {
      await editNote(note.id, text, source);
      [editing, error] = [false, null];
      if (session.admin) dataChanged(); // an admin's edit shows on the site at once
      onchanged();
    } catch (err) {
      error = errorMessage(err);
    } finally {
      busy = false;
    }
  }

  async function withdraw() {
    if (!confirmWithdraw) {
      confirmWithdraw = true;
      return;
    }
    try {
      await withdrawNote(note.id);
      dataChanged(); // an approved note leaves the site
      onchanged();
    } catch (err) {
      error = errorMessage(err);
    }
  }
</script>

<article>
  <div class="head">
    <b>{ROLE_LABEL[note.role]} · {note.champion}{note.opponent ? ` vs ${note.opponent}` : ""}</b>
    <span class="status {status.cls}">{status.label}</span>
  </div>
  <p class="text">{note.text}</p>
  {#if note.revised_text !== null}
    <p class="text revision"><span class="small muted">Your edit:</span> {note.revised_text}</p>
  {/if}
  <div class="small muted">
    {note.created_at.slice(0, 10)}{note.source ? ` · source: ${note.source}` : ""}
    {#if note.review_note}
      · {note.status === "approved" ? "your last edit was not accepted" : "reason"}: {note.review_note}
    {/if}
  </div>
  <ErrorBox message={error} />
  {#if editing}
    <form onsubmit={save}>
      <div class="field">
        <label for="{uid}-text">Your note</label>
        <textarea id="{uid}-text" rows="3" maxlength="1000" bind:value={text}></textarea>
      </div>
      <div class="field">
        <label for="{uid}-source">Source (optional)</label>
        <input id="{uid}-source" maxlength="200" bind:value={source} />
      </div>
      <p class="small muted">
        {session.admin
          ? "Your edit shows at once."
          : note.status === "approved"
            ? "Your edit waits for review; the approved text stays on the site until then."
            : "Your note waits for review again."}
      </p>
      <div class="row">
        <button class="btn primary" disabled={busy}>Save</button>
        <button type="button" class="btn" onclick={() => (editing = false)}>Cancel</button>
      </div>
    </form>
  {:else}
    <div class="row actions">
      <button class="btn link" onclick={startEdit}>Edit</button>
      <button class="btn link" class:danger={confirmWithdraw} onclick={withdraw}>
        {confirmWithdraw ? "Really withdraw?" : "Withdraw"}
      </button>
    </div>
  {/if}
</article>

<style>
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
  .revision {
    border-left: 3px solid var(--warn);
    padding-left: 8px;
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
  textarea {
    resize: vertical;
  }
  form p {
    margin: 6px 0;
  }
  .actions {
    margin-top: 4px;
  }
  .btn.danger {
    color: var(--bad);
  }
</style>
