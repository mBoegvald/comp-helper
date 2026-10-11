<script lang="ts">
  import { errorMessage, getAccounts, resetPassword, setBlocked } from "../../lib/api.ts";
  import { session } from "../../lib/session.svelte.ts";
  import type { Account } from "../../lib/types.ts";
  import ErrorBox from "../common/ErrorBox.svelte";

  let accounts = $state.raw<Account[]>([]);
  let error = $state<string | null>(null);
  let filter = $state("");
  let confirmReset = $state<number | null>(null); // account id waiting for a second click
  let newPassword = $state<{ username: string; password: string } | null>(null);

  async function load() {
    try {
      accounts = (await getAccounts()).accounts;
      error = null;
    } catch (e) {
      error = errorMessage(e);
    }
  }

  async function toggle(a: Account) {
    try {
      accounts = (await setBlocked(a.id, !a.blocked)).accounts;
      error = null;
    } catch (e) {
      error = errorMessage(e);
    }
  }

  async function reset(a: Account) {
    if (confirmReset !== a.id) {
      confirmReset = a.id;
      return;
    }
    confirmReset = null;
    try {
      newPassword = { username: a.username, password: (await resetPassword(a.id)).password };
      error = null;
    } catch (e) {
      error = errorMessage(e);
    }
  }

  $effect(() => {
    load();
  });

  const shown = $derived(accounts.filter((a) => a.username.toLowerCase().includes(filter.trim().toLowerCase())));
</script>

<div class="panel">
  <div class="head">
    <h2>Accounts ({accounts.length})</h2>
    <input placeholder="Find a name" autocomplete="off" bind:value={filter} />
  </div>
  <ErrorBox message={error} />
  {#if newPassword}
    <p class="new-password" role="status">
      New password for <b>{newPassword.username}</b>: <code>{newPassword.password}</code><br />
      <span class="small muted">Pass it on now: it is not shown again. They can change it under My account.</span>
    </p>
  {/if}
  <div class="scroll-x">
    <table>
      <thead><tr><th>Name</th><th>Role</th><th>Joined</th><th>Status</th><th></th></tr></thead>
      <tbody>
        {#each shown as a (a.id)}
          <tr class:blocked={a.blocked}>
            <td>{a.username}</td>
            <td>{a.role}</td>
            <td>{a.created_at.slice(0, 10)}</td>
            <td>{a.blocked ? "Blocked" : "Active"}</td>
            <td class="num">
              {#if a.id !== session.user?.id}
                <button class="btn" class:danger={confirmReset === a.id} onclick={() => reset(a)}>
                  {confirmReset === a.id ? "Really reset?" : "Reset password"}
                </button>
                <button class="btn" class:danger={!a.blocked} onclick={() => toggle(a)}>
                  {a.blocked ? "Unblock" : "Block"}
                </button>
              {/if}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
  <p class="small muted">
    Blocking signs the account out and stops it from signing in. Resetting a password signs the account out and gives
    you a new password to pass on.
  </p>
</div>

<style>
  .blocked td {
    color: var(--muted);
  }
  p {
    margin-bottom: 0;
  }
  .new-password {
    margin: 8px 0;
  }
  code {
    user-select: all;
  }
</style>
