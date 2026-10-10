<script lang="ts">
  import { errorMessage } from "../../lib/api.ts";
  import { deleteMyAccount, session } from "../../lib/session.svelte.ts";
  import ErrorBox from "../common/ErrorBox.svelte";

  /** Delete your own account, with your password as the confirmation. Your notes go with it. */
  const uid = $props.id();
  let open = $state(false);
  let password = $state("");
  let error = $state<string | null>(null);
  let busy = $state(false);

  async function submit(e: SubmitEvent) {
    e.preventDefault();
    busy = true;
    try {
      await deleteMyAccount(password);
    } catch (err) {
      error = errorMessage(err);
    } finally {
      [password, busy] = ["", false];
    }
  }
</script>

<div class="panel">
  <h2>Delete my account</h2>
  <p class="muted">
    This removes your account, {session.user?.username}, and all your notes, approved or not, and your name on lane
    tips. It cannot be undone.
  </p>
  {#if open}
    <form onsubmit={submit}>
      <div class="field">
        <label for="{uid}-pass">Your password, to confirm</label>
        <input id="{uid}-pass" type="password" autocomplete="current-password" required bind:value={password} />
      </div>
      <ErrorBox message={error} />
      <div class="row actions">
        <button class="btn danger" disabled={busy}>Delete my account</button>
        <button type="button" class="btn" onclick={() => ([open, password, error] = [false, "", null])}>Cancel</button>
      </div>
    </form>
  {:else}
    <button class="btn" onclick={() => (open = true)}>Delete my account…</button>
  {/if}
</div>

<style>
  .actions {
    margin-top: 10px;
  }
</style>
