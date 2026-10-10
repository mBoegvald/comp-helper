<script lang="ts">
  import { errorMessage, recommend } from "../../lib/api.ts";
  import { app } from "../../lib/app.svelte.ts";
  import { debounce } from "../../lib/format.ts";
  import { prefs } from "../../lib/prefs.svelte.ts";
  import type { DraftRequest, Recommendation } from "../../lib/types.ts";
  import ErrorBox from "../common/ErrorBox.svelte";
  import DraftForm from "./DraftForm.svelte";
  import PickResults from "./PickResults.svelte";

  let result = $state<Recommendation | null>(null);
  let error = $state<string | null>(null);
  let latest = 0; // answers to older requests are dropped

  const ask = debounce(async (body: DraftRequest) => {
    const id = ++latest;
    try {
      const r = await recommend(body);
      if (id === latest) [result, error] = [r, null];
    } catch (e) {
      if (id === latest) error = errorMessage(e);
    }
  }, 250);

  $effect(() => {
    void app.dataVersion; // also ask again when the data changed
    // only the draft fields, so typing in Lookup does not re-run this
    ask({
      role: prefs.role,
      ally: $state.snapshot(prefs.ally),
      enemy: $state.snapshot(prefs.enemy),
      style: prefs.style,
      need: prefs.need,
      unavailable: $state.snapshot(prefs.unavailable),
      top: 8,
    });
  });
</script>

<div class="grid">
  <DraftForm {result} />
  <div>
    <ErrorBox message={error} />
    {#if result}<PickResults {result} needChosen={!!prefs.need} />{/if}
  </div>
</div>
