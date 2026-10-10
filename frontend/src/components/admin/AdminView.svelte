<script lang="ts">
  import AccountList from "./AccountList.svelte";
  import ReviewQueue from "./ReviewQueue.svelte";
</script>

<div class="admin">
  <ReviewQueue />
  <AccountList />
</div>

<style>
  .admin {
    max-width: 760px;
  }
</style>
