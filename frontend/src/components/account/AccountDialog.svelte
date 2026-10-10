<script lang="ts">
  import { errorMessage } from "../../lib/api.ts";
  import { login, register } from "../../lib/session.svelte.ts";
  import ErrorBox from "../common/ErrorBox.svelte";

  type Mode = "signin" | "signup";

  /** Sign in or create an account (hosted mode). Call `open()` on the component to show it. */
  let { mode = $bindable("signin") }: { mode?: Mode } = $props();

  let dialog = $state<HTMLDialogElement>();
  let username = $state("");
  let password = $state("");
  let error = $state<string | null>(null);
  let busy = $state(false);

  export function open(m: Mode = "signin") {
    mode = m;
    [password, error] = ["", null];
    dialog?.showModal();
  }

  async function submit(e: SubmitEvent) {
    e.preventDefault();
    busy = true;
    try {
      await (mode === "signup" ? register : login)(username.trim(), password);
      password = "";
      dialog?.close();
    } catch (err) {
      error = errorMessage(err);
    } finally {
      busy = false;
    }
  }
</script>

<dialog bind:this={dialog} aria-labelledby="account-title">
  <form onsubmit={submit}>
    <div class="head">
      <h3 id="account-title">{mode === "signup" ? "Create an account" : "Sign in"}</h3>
      <button type="button" class="btn link" aria-label="Close" onclick={() => dialog?.close()}>✕</button>
    </div>
    <p class="small muted">
      {mode === "signup"
        ? "With an account you can suggest notes. An admin reviews them before they show up."
        : "Sign in to suggest notes."}
    </p>
    <ErrorBox message={error} />
    <div class="field">
      <label for="acc-user">Username</label>
      <input id="acc-user" autocomplete="username" required bind:value={username} />
      {#if mode === "signup"}<p class="small muted">3 to 24 letters, digits, - or _.</p>{/if}
    </div>
    <div class="field">
      <label for="acc-pass">Password</label>
      <input
        id="acc-pass"
        type="password"
        autocomplete={mode === "signup" ? "new-password" : "current-password"}
        required
        bind:value={password}
      />
      {#if mode === "signup"}<p class="small muted">At least 10 characters.</p>{/if}
    </div>
    <div class="row actions">
      <button class="btn primary" disabled={busy}>{mode === "signup" ? "Create account" : "Sign in"}</button>
      {#if mode === "signup"}
        <button type="button" class="btn link" onclick={() => ([mode, error] = ["signin", null])}>
          I have an account
        </button>
      {:else}
        <button type="button" class="btn link" onclick={() => ([mode, error] = ["signup", null])}>
          Create an account
        </button>
      {/if}
    </div>
  </form>
</dialog>

<style>
  dialog {
    width: min(380px, calc(100vw - 32px));
    border: 1px solid var(--line);
    border-radius: var(--radius);
    background: var(--panel);
    color: var(--text);
    box-shadow: var(--shadow);
    padding: 16px;
  }
  dialog::backdrop {
    background: rgb(0 0 0 / 0.35);
  }
  p {
    margin: 3px 0 0;
  }
  input[type="password"] {
    background: var(--panel);
    border: 1px solid var(--line);
    border-radius: 7px;
    padding: 6px 8px;
    outline: none;
  }
  .actions {
    margin-top: 14px;
    justify-content: space-between;
  }
</style>
