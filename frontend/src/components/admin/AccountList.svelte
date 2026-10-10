<script lang="ts">
  import { errorMessage, getAccounts, setBlocked } from "../../lib/api.ts";
  import { session } from "../../lib/session.svelte.ts";
  import type { Account } from "../../lib/types.ts";
  import ErrorBox from "../common/ErrorBox.svelte";

  let accounts = $state<Account[]>([]);
  let error = $state<string | null>(null);
  let filter = $state("");

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
              <button class="btn" class:danger={!a.blocked} onclick={() => toggle(a)}>
                {a.blocked ? "Unblock" : "Block"}
              </button>
            {/if}
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
  <p class="small muted">Blocking signs the account out and stops it from signing in.</p>
</div>

<style>
  .blocked td {
    color: var(--muted);
  }
  p {
    margin-bottom: 0;
  }
</style>
