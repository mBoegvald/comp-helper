<script lang="ts">
  import { onMount } from "svelte";
  import ErrorBox from "./components/common/ErrorBox.svelte";
  import Header from "./components/common/Header.svelte";
  import DataView from "./components/data/DataView.svelte";
  import DraftView from "./components/draft/DraftView.svelte";
  import LookupView from "./components/lookup/LookupView.svelte";
  import { app, loadMeta, pollStatus } from "./lib/app.svelte.ts";

  onMount(() => {
    loadMeta();
    return pollStatus(() => app.view === "data");
  });
</script>

<Header bind:view={app.view} />

<main>
  <ErrorBox message={app.error} />
  {#if app.meta}
    <!-- all tabs stay mounted, so switching keeps each tab's state -->
    <section hidden={app.view !== "draft"}><DraftView /></section>
    <section hidden={app.view !== "lookup"}><LookupView /></section>
    <section hidden={app.view !== "data"}><DataView /></section>
  {/if}
</main>

<datalist id="champ-list">
  {#each app.meta?.names ?? [] as name (name)}<option value={name}></option>{/each}
</datalist>

<style>
  main {
    max-width: 1240px;
    margin: 0 auto;
    padding: 16px;
  }
</style>
