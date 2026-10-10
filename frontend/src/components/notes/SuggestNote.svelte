<script lang="ts">
  import { dataChanged } from "../../lib/app.svelte.ts";
  import { errorMessage, suggestNote } from "../../lib/api.ts";
  import { session } from "../../lib/session.svelte.ts";
  import type { Role } from "../../lib/types.ts";
  import ErrorBox from "../common/ErrorBox.svelte";

  /** "Suggest a note" on a champion, or on champion vs opponent (hosted mode, signed in). Admins' notes are added
   * at once; everyone else's wait for review. */
  let { role, champion, opponent = null }: { role: Role; champion: string; opponent?: string | null } = $props();

  const uid = $props.id();
  // another champion or matchup starts over. The props are re-read whenever the parent reloads its data (e.g. right
  // after this note was saved), but `about` keeps its value then, so the "added" message stays.
  const about = $derived(opponent ? `${champion} vs ${opponent}` : champion);
  let open = $derived.by(() => (void about, false));
  let done = $derived.by((): string | null => (void about, null));
  let error = $derived.by((): string | null => (void about, null));
  let text = $state("");
  let source = $state("");
  let busy = $state(false);

  async function submit(e: SubmitEvent) {
    e.preventDefault();
    busy = true;
    try {
      const { note } = await suggestNote(role, champion, opponent, text, source);
      [text, source, open, error] = ["", "", false, null];
      if (note.status === "approved") {
        done = "Your note was added.";
        dataChanged();
      } else {
        done = "Thanks! Your note shows up once an admin approves it. Follow it under My account.";
      }
    } catch (err) {
      error = errorMessage(err);
    } finally {
      busy = false;
    }
  }
</script>

{#if session.hosted && session.user}
  <div class="suggest">
    {#if done}<p class="small done" role="status">{done}</p>{/if}
    {#if open}
      <form onsubmit={submit}>
        <div class="field">
          <label for="{uid}-text">Your note on {about}</label>
          <textarea
            id="{uid}-text"
            rows="3"
            maxlength="1000"
            placeholder={opponent
              ? `What should a ${champion} player know in this lane?`
              : `What helps playing ${champion}?`}
            bind:value={text}></textarea>
        </div>
        <div class="field">
          <label for="{uid}-source">Source (optional)</label>
          <input
            id="{uid}-source"
            maxlength="200"
            placeholder="A link, a streamer, or your own games"
            bind:value={source}
          />
        </div>
        <ErrorBox message={error} />
        <div class="row actions">
          <button class="btn primary" disabled={busy}>{session.admin ? "Add note" : "Send for review"}</button>
          <button type="button" class="btn" onclick={() => (open = false)}>Cancel</button>
        </div>
      </form>
    {:else}
      <button class="btn link" onclick={() => ([open, done] = [true, null])}>+ Suggest a note</button>
    {/if}
  </div>
{/if}

<style>
  .suggest {
    margin-top: 12px;
  }
  .done {
    color: var(--good);
    margin: 0 0 6px;
  }
  textarea {
    resize: vertical;
  }
  .actions {
    margin-top: 10px;
  }
</style>
