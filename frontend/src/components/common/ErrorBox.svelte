<script lang="ts">
  let { message }: { message: string | null } = $props();
</script>

{#if message}<div class="err" role="alert">{message}</div>{/if}

<style>
  .err {
    color: var(--bad);
    background: var(--bad-bg);
    border-radius: 8px;
    padding: 8px 12px;
    margin-bottom: 10px;
  }
</style>
