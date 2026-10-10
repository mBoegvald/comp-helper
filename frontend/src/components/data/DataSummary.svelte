<script lang="ts">
  import { app } from "../../lib/app.svelte.ts";
  import { ROLE_LABEL } from "../../lib/constants.ts";
  import { ago } from "../../lib/format.ts";

  const meta = $derived(app.meta!); // App renders the tabs only once meta has loaded
</script>

<div class="panel">
  <h2>What's in the data</h2>
  <table>
    <thead>
      <tr><th>Role</th><th class="num">Champions</th><th class="num">Matchups</th><th>Win rates</th></tr>
    </thead>
    <tbody>
      {#each meta.roles as r (r.id)}
        <tr>
          <td>{ROLE_LABEL[r.id]}</td>
          <td class="num">{r.champions.length}</td>
          <td class="num">{r.matchups}</td>
          <td>{ago(r.updated)}</td>
        </tr>
      {/each}
    </tbody>
  </table>
  <p class="small muted">
    Win rates: Lolalytics {meta.patch || "?"}. Reddit: {meta.reddit_champions} champions. Tips rebuilt
    {ago(meta.tips_updated)}.
  </p>
</div>

<style>
  p {
    margin-bottom: 0;
  }
</style>
