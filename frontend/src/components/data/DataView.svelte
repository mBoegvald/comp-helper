<script lang="ts">
  import DataSummary from "./DataSummary.svelte";
  import UpdateLog from "./UpdateLog.svelte";
  import UpdateStages from "./UpdateStages.svelte";
</script>

<div class="grid">
  <DataSummary />
  <div>
    <UpdateStages />
    <UpdateLog />
  </div>
</div>
