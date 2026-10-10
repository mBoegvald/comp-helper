<script lang="ts">
  import { errorMessage, startUpdate } from "../../lib/api.ts";
  import { app, refreshStatus } from "../../lib/app.svelte.ts";
  import { type Stage, STAGES } from "../../lib/constants.ts";
  import ErrorBox from "../common/ErrorBox.svelte";

  let error = $state<string | null>(null);
  let confirming = $state<string | null>(null); // stage id waiting for a second click

  async function run(stage: Stage) {
    if (stage.confirm && confirming !== stage.id) {
      confirming = stage.id;
      return;
    }
    confirming = null;
    try {
      await startUpdate(stage.id);
      error = null;
    } catch (e) {
      error = errorMessage(e);
    }
    setTimeout(refreshStatus, 800);
  }
</script>

<div class="panel">
  <h2>Update</h2>
  <ErrorBox message={error} />
  <div class="stages">
    {#each STAGES as stage (stage.id)}
      <div class="stage">
        <div>
          <b>{stage.title}</b>
          <p>{confirming === stage.id ? stage.confirm : stage.desc}</p>
        </div>
        <div class="row">
          {#if confirming === stage.id}
            <button class="btn" onclick={() => (confirming = null)}>Cancel</button>
          {/if}
          <button
            class="btn"
            class:primary={stage.id === "lolalytics" || confirming === stage.id}
            disabled={app.running}
            onclick={() => run(stage)}>{confirming === stage.id ? "Start" : "Run"}</button
          >
        </div>
      </div>
    {/each}
  </div>
  <p class="small muted">
    Updates run in the background and keep going if you close this page. Only one runs at a time. Stopping is safe:
    finished work is kept and the next run continues.
  </p>
</div>

<style>
  .stages {
    display: grid;
    gap: 8px;
  }
  .stage {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 10px;
    align-items: center;
    padding: 10px 12px;
    border: 1px solid var(--line);
    border-radius: 8px;
  }
  .stage p {
    margin: 2px 0 0;
    font-size: 12px;
    color: var(--muted);
  }
</style>
