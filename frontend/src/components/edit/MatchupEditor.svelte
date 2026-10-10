<script lang="ts">
  import { untrack } from "svelte";
  import { errorMessage, saveHandMatchup } from "../../lib/api.ts";
  import { HAND_RESULTS } from "../../lib/constants.ts";
  import type { Matchup, Role } from "../../lib/types.ts";
  import ErrorBox from "../common/ErrorBox.svelte";

  /** Edit your label and lane tip for a matchup, from `m.champ`'s side. */
  interface Props {
    role: Role;
    m: Matchup;
    onsaved?: (m: Matchup) => void;
    oncancel?: () => void;
  }
  let { role, m, onsaved, oncancel }: Props = $props();

  // the form starts from the saved note once; the parent creates a new editor per matchup
  const saved = untrack(() => ({
    result: m.hand_result ?? "",
    tip: m.tips.find((t) => t.from === "notes" && t.who === m.champ)?.text ?? "",
  }));
  let result = $state(saved.result);
  let tip = $state(saved.tip);
  let error = $state<string | null>(null);
  let saving = $state(false);

  async function save(e: SubmitEvent) {
    e.preventDefault();
    saving = true;
    try {
      onsaved?.(await saveHandMatchup(role, m.champ, m.opp, result, tip));
    } catch (err) {
      error = errorMessage(err);
    } finally {
      saving = false;
    }
  }
</script>

<form onsubmit={save}>
  <ErrorBox message={error} />
  <div class="field">
    <label for="edit-result">Result for {m.champ}</label>
    <select id="edit-result" bind:value={result}>
      <option value="">From the win rates ({m.label ?? "no data"})</option>
      {#each HAND_RESULTS as r (r)}<option value={r}>{r}</option>{/each}
    </select>
    <p class="small muted">The win rates decide the score when there are any; your label counts when there are none.</p>
  </div>
  <div class="field">
    <label for="edit-tip">Lane tip</label>
    <textarea id="edit-tip" rows="3" placeholder="e.g. Trade when his W is down" bind:value={tip}></textarea>
  </div>
  <div class="row actions">
    <button class="btn primary" disabled={saving}>{saving ? "Saving…" : "Save"}</button>
    <button type="button" class="btn" onclick={oncancel}>Cancel</button>
    <span class="small muted">Leave both empty to remove your note.</span>
  </div>
</form>

<style>
  form {
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid var(--line);
  }
  p {
    margin: 3px 0 0;
  }
  textarea {
    resize: vertical;
  }
  .actions {
    margin-top: 12px;
  }
</style>
