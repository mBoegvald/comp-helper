# Pick Helper

Draft helper for League of Legends, all five roles. It ranks picks for your draft using lane win rates from
Lolalytics (Emerald+), tips from each champion's mains subreddit, and hand-written champion knowledge.

## Start it

**Windows:** double-click `Start Pick Helper.bat`. The page opens in your browser. Close the black window to stop it.

**Linux:** run `./start.sh`.

The page has three tabs:

- **Draft:** choose your role and fill in what you know of both teams, bans and fearless picks. Picks update as
  you type. Open a pick to see lane notes and Reddit tips with links to the threads.
- **Lookup:** every matchup for one champion in one role. Click a row for the full matchup. This is also where
  you edit your own notes.
- **Data:** what the data covers, and buttons to update it. Updates run in the background and keep going if
  you close the page.

## Set up on Windows

1. Install Python 3.10 or newer from https://www.python.org/downloads/ and tick **Add python.exe to PATH**
   during setup.
2. Copy this whole folder to the Windows PC (about 40 MB). Keep the `data` folder: it holds the database
   (`pickhelper.db`, with your own notes) and the Reddit downloads, so updates only fetch what is new.
3. Double-click `Start Pick Helper.bat`. Nothing else needs installing.

If Windows asks whether to allow Python through the firewall, you can say no. The page only listens on your
own PC (127.0.0.1).

## Keep the data fresh

| When | Data tab button | Command line | Time |
|---|---|---|---|
| After each patch | Refresh win rates | `python update.py lolalytics` | about 5 min |
| New champions released | Fetch missing Reddit | `python update.py reddit` | 2 to 4 min per new champion |
| Once, overnight (optional) | Fetch Reddit comments | `python update.py comments` | many hours |
| Everything | Everything | `python update.py` | depends on what is missing |

Reddit allows about one request per minute without an account, which is why the Reddit steps are slow.
Stopping an update is safe: finished work is kept and the next run continues.

## Edit the knowledge

Everything lives in one file, `data/pickhelper.db`. Your own notes (archetype, comps, pick when, good into,
struggles into for a champion; a label and a lane tip for a matchup) are kept apart from the downloaded data,
so no update ever overwrites them. Each update first saves a copy of the database in `data/backups` (the last 14
days are kept). To undo a bad edit, close the page and copy a backup over `data/pickhelper.db`.

To edit, open a champion in **Lookup**: **Edit notes** on the champion card, or click a matchup and press
**Edit** for your label and lane tip. An empty field means "use the default"; the defaults for champions live in
`role_data.py`. A saved edit shows up in the Draft tab straight away.

`NOTES.md` has the design notes and data caveats.

## Develop

`pip install -r requirements-dev.txt` (or `nix-shell` on NixOS), then:

- `ruff check .` and `ruff format .` for lint and formatting
- `pytest` for the tests (a temp database each time, never `data/pickhelper.db`)

The page is a Svelte app in TypeScript in `frontend/` (needs Node 24). In `frontend/`: `npm ci` once, then

- `npm run dev` for the page with live reload, next to `python webapp.py --no-browser` (it forwards `/api`)
- `npm run lint` (Prettier and the type checks) and `npm run format`
- `npm test` for the unit tests, and `npm run e2e` for the browser tests (they start the Python server on a fresh
  test database and test the built page, so run `npm run build` first). On NixOS, point Playwright at nix's
  browser: `CHROMIUM_PATH=$(command -v chromium) npm run e2e` inside `nix-shell -p chromium`.
- `npm run build` writes `web/dist`. Commit it with your change: that is what the Windows PC runs, and CI fails
  when it does not match the source.

CI runs all of it on every pull request, with the Python tests on Ubuntu and Windows.
