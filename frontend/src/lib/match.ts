// Which champion names to suggest for what has been typed, best first.

const key = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, "");
const words = (name: string) => name.split(/[\s'.&]+/).filter(Boolean);

/** Up to `limit` names for `typed`: an exact match, then names that start with it, then a word that does ("fate" -> Twisted Fate) or the
 * initials ("tf" -> Twisted Fate), then names that contain it (from two letters on: one letter is inside nearly
 * every name). Case, spaces and punctuation are ignored. */
export function suggestNames(names: readonly string[], typed: string, limit = 8): string[] {
  const q = key(typed);
  if (!q) return [];
  const exact: string[] = [];
  const starts: string[] = [];
  const word: string[] = [];
  const inside: string[] = [];
  for (const name of names) {
    const k = key(name);
    const ws = words(name);
    if (k === q) exact.push(name);
    else if (k.startsWith(q)) starts.push(name);
    else if (ws.some((w) => key(w).startsWith(q)) || (ws.length > 1 && key(ws.map((w) => w[0]).join("")) === q))
      word.push(name);
    else if (q.length > 1 && k.includes(q)) inside.push(name);
  }
  return [...exact, ...starts, ...word, ...inside].slice(0, limit);
}
