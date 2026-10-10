<script lang="ts">
  import { onMount } from "svelte";
  import AccountDialog from "./components/account/AccountDialog.svelte";
  import AdminView from "./components/admin/AdminView.svelte";
  import MyNotes from "./components/notes/MyNotes.svelte";
  import ErrorBox from "./components/common/ErrorBox.svelte";
  import Header from "./components/common/Header.svelte";
  import DataView from "./components/data/DataView.svelte";
  import DraftView from "./components/draft/DraftView.svelte";
  import LookupView from "./components/lookup/LookupView.svelte";
  import { app, loadMeta, pollStatus } from "./lib/app.svelte.ts";
  import { loadReview } from "./lib/review.svelte.ts";
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

  // signed out while on My notes
  $effect(() => {
    if (session.loaded && app.view === "mine" && !(session.hosted && session.user)) app.view = "draft";
  });

  // signed out of the admin account while on the Admin tab
  $effect(() => {
    if (session.loaded && app.view === "admin" && !(session.hosted && session.admin)) app.view = "draft";
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
      <section hidden={app.view !== "mine"}><MyNotes /></section>
    {/if}
    {#if session.hosted && session.admin}
      <section hidden={app.view !== "admin"}><AdminView /></section>
    {/if}
  {/if}
</main>

<style>
  main {
    max-width: 1240px;
    margin: 0 auto;
    padding: 16px;
  }
</style>
