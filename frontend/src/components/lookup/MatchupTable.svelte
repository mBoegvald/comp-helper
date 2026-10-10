<script lang="ts">
  import { DIFF_HELP } from "../../lib/constants.ts";
  import { percent, signed } from "../../lib/format.ts";
  import { session } from "../../lib/session.svelte.ts";
  import type { MatchupRow } from "../../lib/types.ts";
  import ChampIcon from "../common/ChampIcon.svelte";
  import ResultTag from "../common/ResultTag.svelte";

  /** Every matchup of one champion, sortable by any column; clicking a row selects that opponent. */
  interface Props {
    rows: MatchupRow[];
    filter?: string;
    selected?: string | null;
  }
  let { rows, filter = "", selected = $bindable(null) }: Props = $props();

  type SortKey = "opp" | "score" | "wr" | "dnorm" | "games" | "label" | "reddit";
  interface Column {
    key: SortKey;
    title: string;
    num?: boolean;
    help?: string;
  }
  const COLUMNS: Column[] = [
    { key: "opp", title: "Opponent" },
    { key: "score", title: "Score", num: true },
    { key: "wr", title: "Win rate", num: true },
    { key: "dnorm", title: "vs usual", num: true, help: DIFF_HELP },
    { key: "games", title: "Games", num: true },
    { key: "label", title: "Result" },
    { key: "reddit", title: "Reddit tips", num: true },
  ];

  let sort = $state<{ key: SortKey; dir: number }>({ key: "score", dir: -1 });

  function sortBy(col: Column) {
    sort = { key: col.key, dir: sort.key === col.key ? -sort.dir : col.num ? -1 : 1 };
  }

  const shown = $derived.by(() => {
    const f = filter.trim().toLowerCase();
    const list = rows.filter((m) => !f || m.opp.toLowerCase().includes(f));
    const { key, dir } = sort;
    return list.toSorted((a, b) => {
      const [x, y] = [a[key], b[key]];
      if (x == null) return 1;
      if (y == null) return -1;
      return (typeof x === "string" ? x.localeCompare(String(y)) : x - Number(y)) * dir;
    });
  });
</script>

<div class="wrap">
  <table>
    <thead>
      <tr>
        {#each COLUMNS as col (col.key)}
          <th class:num={col.num} title={col.help}>
            <button onclick={() => sortBy(col)}>
              {col.title}{sort.key === col.key ? (sort.dir > 0 ? " ▴" : " ▾") : ""}
            </button>
          </th>
        {/each}
      </tr>
    </thead>
    <tbody>
      {#each shown as m (m.opp)}
        <tr class:sel={m.opp === selected} onclick={() => (selected = m.opp)}>
          <td>
            <span class="opp">
              <ChampIcon name={m.opp} size="sm" />
              {m.opp}
              {#if m.notes}<span
                  class="small muted"
                  title={session.hosted ? "Has the admin's lane notes" : "Has your lane notes"}>✎</span
                >{/if}
            </span>
          </td>
          <td class="num">{signed(m.score)}</td>
          <td class="num">{percent(m.wr)}</td>
          <td class="num">{signed(m.dnorm)}</td>
          <td class="num">{m.games ?? "–"}</td>
          <td><ResultTag label={m.label} low={m.low_sample} /></td>
          <td class="num">{m.reddit || ""}</td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .wrap {
    max-height: 70vh;
    overflow: auto;
  }
  th button {
    border: 0;
    background: none;
    padding: 0;
    font: inherit;
    color: inherit;
    cursor: pointer;
    user-select: none;
  }
  tbody tr {
    cursor: pointer;
  }
  tbody tr:hover {
    background: var(--panel-2);
  }
  tbody tr.sel {
    background: var(--you);
  }
  .opp {
    display: flex;
    gap: 8px;
    align-items: center;
  }
</style>
