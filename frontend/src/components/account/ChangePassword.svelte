<script lang="ts">
  import { changePassword, errorMessage } from "../../lib/api.ts";
  import ErrorBox from "../common/ErrorBox.svelte";

  /** Change your password, with the current one to confirm. Your other devices are signed out. */
  const uid = $props.id();
  let open = $state(false);
  let old = $state("");
  let next = $state("");
  let error = $state<string | null>(null);
  let done = $state(false);
  let busy = $state(false);

  async function submit(e: SubmitEvent) {
    e.preventDefault();
    busy = true;
    try {
      await changePassword(old, next);
      [open, done, error] = [false, true, null];
    } catch (err) {
      error = errorMessage(err);
    } finally {
      [old, next, busy] = ["", "", false];
    }
  }
</script>

<div class="panel">
  <h2>Password</h2>
  {#if done}<p class="small done" role="status">Your password was changed. Other devices are signed out.</p>{/if}
  {#if open}
    <form onsubmit={submit}>
      <div class="field">
        <label for="{uid}-old">Current password</label>
        <input id="{uid}-old" type="password" autocomplete="current-password" required bind:value={old} />
      </div>
      <div class="field">
        <label for="{uid}-new">New password</label>
        <input id="{uid}-new" type="password" autocomplete="new-password" required bind:value={next} />
        <p class="small muted">At least 10 characters.</p>
      </div>
      <ErrorBox message={error} />
      <div class="row actions">
        <button class="btn primary" disabled={busy}>Change password</button>
        <button type="button" class="btn" onclick={() => ([open, old, next, error] = [false, "", "", null])}>
          Cancel
        </button>
      </div>
    </form>
  {:else}
    <button class="btn" onclick={() => ([open, done] = [true, false])}>Change password…</button>
  {/if}
</div>

<style>
  .done {
    color: var(--good);
  }
  .actions {
    margin-top: 10px;
  }
</style>
