<script lang="ts">
  import { app } from "../../lib/app.svelte.ts";
  import { errorMessage, getMyNotes } from "../../lib/api.ts";
  import type { Suggestion } from "../../lib/types.ts";
  import ErrorBox from "../common/ErrorBox.svelte";
  import MyNote from "./MyNote.svelte";

  let mine = $state<Suggestion[] | null>(null);
  let error = $state<string | null>(null);

  function load() {
    getMyNotes().then(
      (r) => ([mine, error] = [r.notes, null]),
      (e) => (error = errorMessage(e)),
    );
  }

  // reload each time the tab is opened, so a fresh review shows
  $effect(() => {
    if (app.view === "mine") load();
  });
</script>

<div class="mine">
  <div class="panel">
    <h2>My notes</h2>
    <ErrorBox message={error} />
    {#if mine && !mine.length}
      <p class="muted">
        You have not suggested any notes yet. Open a champion or a matchup in Lookup and choose “Suggest a note”.
      </p>
    {/if}
    {#each mine ?? [] as n (n.id)}
      <MyNote note={n} onchanged={load} />
    {/each}
  </div>
</div>

<style>
  .mine {
    max-width: 760px;
  }
</style>
