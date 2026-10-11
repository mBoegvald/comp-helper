<script lang="ts">
  import { onMount } from "svelte";
  import AccountDialog from "./components/account/AccountDialog.svelte";
  import ChangePassword from "./components/account/ChangePassword.svelte";
  import DeleteAccount from "./components/account/DeleteAccount.svelte";
  import Privacy from "./components/account/Privacy.svelte";
  import AdminView from "./components/admin/AdminView.svelte";
  import MyNotes from "./components/notes/MyNotes.svelte";
  import ErrorBox from "./components/common/ErrorBox.svelte";
  import Header from "./components/common/Header.svelte";
  import DataView from "./components/data/DataView.svelte";
  import DraftView from "./components/draft/DraftView.svelte";
  import LookupView from "./components/lookup/LookupView.svelte";
  import { app, loadMeta, pollStatus } from "./lib/app.svelte.ts";
  import { loadReview } from "./lib/review.svelte.ts";
  import { redirect } from "./lib/router.svelte.ts";
  import { loadSession, session } from "./lib/session.svelte.ts";

  let accountDialog = $state<ReturnType<typeof AccountDialog>>();

  onMount(() => {
    loadMeta();
    loadSession();
    // update status is admin-only
    return pollStatus(() => session.admin && app.view === "data");
  });

  // the review queue (and the count on the Admin tab): for admins, fresh on each tab switch
  $effect(() => {
    void app.view;
    if (session.hosted && session.admin) loadReview();
  });

  // the privacy page belongs to the hosted site
  $effect(() => {
    if (session.loaded && app.view === "privacy" && !session.hosted) redirect("draft");
  });

  // signed out while on My account
  $effect(() => {
    if (session.loaded && app.view === "mine" && !(session.hosted && session.user)) redirect("draft");
  });

  // signed out of the admin account while on the Admin tab
  $effect(() => {
    if (session.loaded && app.view === "admin" && !(session.hosted && session.admin)) redirect("draft");
  });
</script>

<Header bind:view={app.view} onsignin={() => accountDialog?.open()} />
<AccountDialog bind:this={accountDialog} />

<main>
  <ErrorBox message={app.error} />
  {#if app.meta}
    <!-- all tabs stay mounted, so switching keeps each tab's state -->
    <section hidden={app.view !== "draft"}><DraftView /></section>
    <section hidden={app.view !== "lookup"}><LookupView /></section>
    <section hidden={app.view !== "data"}><DataView /></section>
    {#if session.hosted && session.user}
      <section class="account" hidden={app.view !== "mine"}><MyNotes /><ChangePassword /><DeleteAccount /></section>
    {/if}
    {#if session.hosted && session.admin}
      <section hidden={app.view !== "admin"}><AdminView /></section>
    {/if}
    {#if session.hosted}
      <section hidden={app.view !== "privacy"}><Privacy /></section>
    {/if}
  {/if}
</main>

{#if session.hosted}
  <footer>
    <button class="btn link small" onclick={() => ((app.view = "privacy"), scrollTo({ top: 0 }))}>Privacy</button>
  </footer>
{/if}

<style>
  footer {
    max-width: 1240px;
    margin: 0 auto;
    padding: 8px 16px 24px;
  }
  .account {
    display: grid;
    gap: 16px;
    max-width: 760px;
  }
  main {
    max-width: 1240px;
    margin: 0 auto;
    padding: 16px;
  }
</style>
