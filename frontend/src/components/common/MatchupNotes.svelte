<script lang="ts">
  import { safeRedditUrl } from "../../lib/format.ts";
  import type { Matchup } from "../../lib/types.ts";
  import CommunityNotes from "../notes/CommunityNotes.svelte";

  /** Hand-written lane notes and Reddit snippets for a matchup, seen from `champ`'s side. */
  let { m, champ }: { m: Matchup; champ: string } = $props();
</script>

<div class="notes">
  {#if m.tips.length || m.hand_result}
    <section>
      <h5>Lane notes</h5>
      {#each m.tips as t, i (i)}
        <div class="note">{t.who !== champ ? `${t.who}'s side: ` : ""}{t.text}</div>
      {/each}
      {#if m.hand_result}
        <p class="small muted">
          Hand label: {m.hand_result}{m.mismatch ? " (disagrees with the win rate)" : ""}
        </p>
      {/if}
    </section>
  {/if}

  <CommunityNotes notes={m.community} {champ} />

  {#each m.reddit as r (r.who)}
    <section>
      <h5>From {r.who} mains · {r.mentions} mentions · newest {r.newest || "?"}</h5>
      <div class="snips">
        {#each r.tips as t, i (i)}
          {@const url = safeRedditUrl(t.url)}
          <div class="snip">
            {t.text}
            <div class="meta">
              {t.date}{#if url}{" · "}<a href={url} target="_blank" rel="noopener noreferrer">thread</a>{/if}
            </div>
          </div>
        {/each}
      </div>
    </section>
  {/each}

  {#if !m.tips.length && !m.reddit.length && !m.community.length}
    <p class="small muted">No notes or Reddit tips for this matchup yet.</p>
  {/if}
</div>

<style>
  .notes {
    display: grid;
    gap: 12px;
  }
  h5 {
    margin: 0 0 4px;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--muted);
  }
  p {
    margin: 4px 0 0;
  }
  .note {
    background: var(--panel-2);
    border-left: 3px solid var(--accent);
    padding: 6px 10px;
    border-radius: 0 6px 6px 0;
    font-size: 13px;
  }
  .note + .note {
    margin-top: 4px;
  }
  .snips {
    display: grid;
    gap: 6px;
  }
  .snip {
    font-size: 13px;
    padding: 7px 10px;
    border: 1px solid var(--line);
    border-radius: 8px;
    background: var(--panel);
  }
  .meta {
    font-size: 11px;
    color: var(--muted);
    margin-top: 3px;
  }
</style>
