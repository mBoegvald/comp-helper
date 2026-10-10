<script lang="ts">
  import { errorMessage, stopUpdate } from "../../lib/api.ts";
  import { app, refreshStatus } from "../../lib/app.svelte.ts";
  import ErrorBox from "../common/ErrorBox.svelte";

  let error = $state<string | null>(null);
  let confirming = $state(false);
  let pre = $state<HTMLPreElement>();

  async function stop() {
    if (!confirming) {
      confirming = true;
      return;
    }
    confirming = false;
    try {
      await stopUpdate();
      error = null;
    } catch (e) {
      error = errorMessage(e);
    }
    setTimeout(refreshStatus, 800);
  }

  // follow the end of the log, unless the reader scrolled up
  $effect.pre(() => {
    void app.log;
    const el = pre;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    if (atBottom) queueMicrotask(() => (el.scrollTop = el.scrollHeight));
  });
</script>

<div class="panel">
  <div class="head">
    <h3><span class="dot" class:on={app.running}></span>{app.running ? "Update running" : "Idle"}</h3>
    {#if app.running}
      <div class="row">
        {#if confirming}
          <span class="small muted">Stop it? Finished work is kept.</span>
          <button class="btn" onclick={() => (confirming = false)}>No</button>
        {/if}
        <button class="btn danger" onclick={stop}>{confirming ? "Yes, stop" : "Stop"}</button>
      </div>
    {/if}
  </div>
  <ErrorBox message={error} />
  <pre bind:this={pre}>{app.log || "No log yet."}</pre>
</div>

<style>
  pre {
    background: var(--panel-2);
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 10px;
    font: 12px/1.45 var(--mono);
    max-height: 420px;
    overflow: auto;
    white-space: pre-wrap;
    word-break: break-word;
    margin: 0;
  }
  .dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 99px;
    background: var(--even);
    margin-right: 6px;
    vertical-align: 1px;
  }
  .dot.on {
    background: var(--warn);
    animation: pulse 1.2s infinite;
  }
  @keyframes pulse {
    50% {
      opacity: 0.35;
    }
  }
</style>
