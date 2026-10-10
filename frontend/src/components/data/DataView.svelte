<script lang="ts">
  import { session } from "../../lib/session.svelte.ts";
  import DataSummary from "./DataSummary.svelte";
  import UpdateLog from "./UpdateLog.svelte";
  import UpdateStages from "./UpdateStages.svelte";
</script>

<div class="grid">
  <DataSummary />
  {#if session.admin}
    <div>
      <UpdateStages />
      <UpdateLog />
    </div>
  {/if}
</div>
