# Pick helper: notes

## Lint, tests and CI (2026-10-10)
- ruff (lint + format, 120 columns; E501 off because the formatter owns line length) and pytest, pinned in
  requirements-dev.txt and matched by shell.nix. The one-off reformat is listed in .git-blame-ignore-revs.
- tests/ builds a small database per test with hand-checkable numbers (tests/conftest.py); the Lolalytics parser is
  tested against a trimmed copy of a real counters page (tests/fixtures), so a site wording change shows up there
  first. Real network calls are never made in tests.
- CI (.github/workflows/ci.yml): lint once, tests on ubuntu and windows x Python 3.10 and 3.13. The first run on
  2026-10-10 was the first time the Windows paths ran anywhere: the msvcrt lock passes. Still untested on Windows:
  the .bat itself, DETACHED_PROCESS spawning and taskkill for Stop.
- Found by the new checks: the AP fallback list split multi-word names (Aurelion Sol, Twisted Fate, Nunu & Willump
  fell back to AD), and the page header read mid's patch only.
- Hosting on a server (Docker) was considered and deferred: the page has no login and edits are open to anyone who
  can reach it, so it needs auth or an authenticating reverse proxy before it listens beyond 127.0.0.1.
- GitHub access from the dev machine: push over SSH with a deploy key on this repo only; gh uses a fine-grained
  token owned by mBoegvald (own repos only), needing Pull requests read/write and Actions read.

## SQLite instead of workbooks (2026-10-10)
- All data is in `data/pickhelper.db` (stdlib sqlite3, so the app needs no extra package; `db.py` has the schema).
  Generated tables (`lola`, `reddit_tips`, `reddit_snippet`) are replaced by updates in one transaction each;
  `pool` only grows; the hand layer (`hand_champion`, `hand_matchup`, `role_note`) is written only by people.
  This replaces build_role.py's old merge, which had to guess which workbook cells were hand edits.
- `db.champions(role)` / `db.matchups(role)` rebuild exactly what the workbooks held (verified: every score, label and
  tip identical for all five roles, plus five draft queries). One intended difference: 'Good into' no longer starts
  with '; ' when there is no data list (was the case for 25 champions).
- A hand_champion field that is NULL falls back to role_data.py; the stored hand part of Good/Struggles into is only
  the text after the data-derived names. Mid has no role_data entries, so all its champion text is hand data.
- `migrate_xlsx.py` did the one-off import (48 champion rows, 103 hand labels, 157 lane tips, mid's Comps/Notes);
  it was removed together with the workbooks and CSVs; all of them are in git history (commit 74eaf71 has them all).
- Edits: GET/POST `/api/hand/champion` ({role, champion, fields}; '' or null resets a field to the default) and
  POST `/api/hand/matchup` ({role, champion, opponent, result, tip}; result is Favored, Even, Even / skill,
  Unfavored or empty; both empty deletes the row). The Svelte page (next step) is the UI for these.
- build_role.py refuses to save a fetch with under 60% of the previous row count (site change or outage), so a
  broken scrape cannot wipe a role. update.py makes one database backup per day in data/backups (14 kept).
- `PICKHELPER_DB=/path/copy.db` points everything at another database file (testing).
- Dev on NixOS: `nix-shell` (shell.nix) for python3, ruff and pytest. Python 3.11 packages are no longer prebuilt
  in nixpkgs (openpyxl pulls in pandas, which then builds from source), so shell.nix uses the default python3.

## Web page and Windows (added 2026-10-09)
- `webapp.py` serves `web/index.html` on 127.0.0.1:8765 (stdlib http.server). Launchers:
  `Start Pick Helper.bat` (Windows, checks Python >= 3.10) and `start.sh`. README.md has the
  user-facing setup. JSON endpoints: /api/meta, /api/recommend (POST), /api/champion, /api/matchup, /api/status,
  /api/update and /api/stop (POST, same-origin only).
- Scoring is `picker.score` unchanged; it takes an optional `detail` list for the structured breakdown, and
  `picker.load_full(role)` caches per workbook mtime and also returns raw matchup fields. The page's lane
  opponent is the enemy in your own role slot; other enemies count one third, as in the CLI.
- Name matching: exact name or nickname (picker.ALIASES) across all champions first, then a unique prefix, then a
  unique substring. picker.resolve also refuses to prefix-match an exact champion name (Vi was read as Viktor).
- `update.py` replaces run_all.sh (now a wrapper): same stages, cross-platform file lock (fcntl / msvcrt at
  offset 4096 so the PID at the start stays readable on Windows), log in logs/update.log. Since 2026-10-10 every write is
  a SQLite transaction, so stopping an update cannot corrupt anything.
- The page labels matchups from the normalised delta with direction kept (Favored/Even/Unfavored) and a separate
  low-sample flag, and shows the delta as 'vs usual' because raw WR alone can contradict the label.
- Not yet tested on a real Windows machine; the Windows-only paths are the .bat, msvcrt locking, DETACHED_PROCESS
  spawning and taskkill for Stop.

## All roles (added 2026-10-09, mid aligned the same day; workbook parts replaced by SQLite on 2026-10-10)
- `picker.py --role top|jungle|mid|bot|support` (aliases jg, adc, sup). `mid_picker.py` still works and is a wrapper.
- All five workbooks are built the same way by `build_role.py <role>` (mid -> `midlane_overview.xlsx`, others ->
  `roles/<role>.xlsx`): Lolalytics Emerald+ lane-specific matchups for every pair with >= 100 games, plus the hand
  layer. Champion pool = everyone with >= 150 games against the role's seed champions, plus the hand table in
  `role_data.py`, plus whatever is already in the workbook.
- Hand layer that survives every rebuild: Champions text (archetype, damage, comps, pick when, blind-safe; hand
  'Good into' / 'Struggles into' text is kept after the data-derived list), 'Result for champion' when it differs from
  the Lolalytics label (= a hand label; 'Mismatch' = yes when it disagrees with the data), 'Lane tip', and the Comps and
  Notes sheets. Rows with a hand label or tip are kept even when Lolalytics has no data for the pair ('no data').
- Updating everything is one command: `python update.py` (lolalytics for all roles -> reddit -> tips), or the Data
  tab of the web page. `python update.py lolalytics` alone takes ~5 min and refreshes all win rates. Reddit is resumable and only fetches what is missing.
- Matchup rows under 200 games are labelled 'low sample'; the picker trusts them at 70%.
- Where no hand tip exists the picker shows "(lolalytics +x.x, N games)" as the reason.
- Reddit data is per champion and shared across roles (173 champions as of 2026-10-09). Subreddit lookup:
  r/<champ>mains or SUB_OVERRIDES (TwistedFate, Aurelion_Sol_mains, DirtySionMains, TeemoTalk, RenataMains,
  LeagueOfJinx, TheSecretWeapon for Zac, ...), falling back to r/<champ>.
- Known gaps: no Lolalytics lane data for Maokai/Zac top, Brand/Morgana/Olaf jungle, Akshan/Jayce bot; tiny subs
  (Vel'Koz, Locke, Taliyah). Only Locke (jungle, mid) and Zaahen (top) still have the placeholder 'Flex' archetype;
  everyone else has a hand entry in role_data.py. A workbook Archetype edit wins on rebuild, except the word 'Flex'.
- Archetype names: support uses 'Peel tank' (Riot calls it Warden); mid gained 'Tank / bruiser' and 'Marksman'.

## Files (as of 2026-10-08; the xlsx/CSV parts are history, see the SQLite section)
- `midlane_overview.xlsx`: Champions (51), Matchups (~1740, of which 157 carry hand labels/tips), Comps, Notes. Built by build_role.py since 2026-10-09; backups of the pre-build file are in data/.
- `mid_picker.py`: CLI that scores picks from the xlsx. Since 2026-10-08 it tolerates extra columns, uses
  'Lola dNorm' (x1.5, clamped to +-3) instead of the hand label when present, and appends the first Reddit snippet
  to each tip. Without the extra columns it behaves exactly as before.
- `fetch_lolalytics.py`: pulls Emerald+ matchup win rates from lolalytics.com and merges them into the Matchups sheet.
- `fetch_reddit_rss.py`: pulls matchup threads (+ optional comments) from r/<champion>mains via Reddit's public Atom
  feeds. No login. This is the working Reddit path.
- `extract_tips.py`: deterministic (no LLM) extraction of per-matchup snippets from data/reddit into
  data/reddit_tips.csv, and `apply` to write Reddit tips/mentions/newest columns into the Matchups sheet.
  `python3 extract_tips.py show Zed Viktor` prints every snippet for a pair, newest first.
- `run_all.sh`: unattended pipeline (lolalytics -> reddit -> tips). `./run_all.sh comments` is the optional overnight
  stage that pulls comments for the 12 best threads per champion (answers to 'help vs X' threads live there).
- `fetch_reddit.py`: same via PRAW. Only useful if you already hold Reddit API credentials (see Agent-Reach note).

## Workflow
```
nohup ./run_all.sh >/dev/null 2>&1 &   # everything, unattended; progress in logs/run_all.log; rerun to resume
python3 fetch_lolalytics.py fetch                 # reads Champions sheet, writes data/lolalytics_matchups.csv (~1.5 s per champion)
python3 fetch_lolalytics.py apply                 # adds Lola* columns + Mismatch flag to the Matchups sheet
python3 fetch_lolalytics.py apply --overwrite-result   # also replaces Result; original kept in "Result (Claude)"
python3 fetch_reddit_rss.py                       # writes data/reddit/<champion>.json, 1 request/min (~2 per champion)
python3 fetch_reddit_rss.py --champs Zed --comments 30 --delay 60   # also pull comments, one request per thread
```

## Findings (2026-10-08)
- Anonymous reddit.com HTML and .json return 403 and old.reddit redirects to login, but the Atom feeds work:
  `/r/<sub>/search.rss?q=matchup&restrict_sr=on&sort=top&t=all&limit=50` (50 threads with full self-text),
  `/r/<sub>/top/.rss?t=all&limit=100`, `/r/<sub>/comments/<id>/.rss`. Wiki pages have no feed (400).
  Rate limit is harsh: a second request within ~a minute gets 429, so space requests 60 s apart.
  Verified on r/ZileanMains and r/zedmains on 2026-10-08 (e.g. 'Zed matchup tier list', 'S11 Midlane/Toplane Matchups').
- mobalytics.gg, u.gg and leagueofgraphs.com sit behind a Cloudflare challenge. op.gg serves HTML but the counters are
  client-rendered. lolalytics.com serves the full counters page server-side with no auth: win rate, delta vs the
  champion's average, normalised delta, opponent average and games, for every opponent with >= 100 games.
- Lolalytics raw win rates are inflated: A-vs-B and B-vs-A sum to ~102-103% because everything is measured from the
  perspective of an Emerald+ player (site-wide average 51.31%). Labels therefore use the normalised delta (dNorm),
  averaged over both directions, with +-2 as the Favored/Unfavored threshold. Thresholds live at the top of the script.
- Spot check, patch 16.20 Emerald+: Zed vs Viktor dNorm +1.85 (Even), Zed vs Twisted Fate +3.12 (Favored),
  Zed vs Annie -6.7 but only 146 games (low sample). The earlier Mobalytics figure (Zed 43.8% vs Viktor, 16.13)
  disagrees; sites and patches differ, so treat single-site numbers as indicative.
- Decided: no Riot API for now.

## Agent-Reach (installed 2026-10-08)
- `pip install --user` from github.com/Panniantong/agent-reach; binary at `~/.local/bin/agent-reach`.
  `agent-reach install` (safe mode) reports 4/16 channels, Reddit not among them.
- Its Reddit channel has no anonymous path either. Backends: OpenCLI (desktop, reuses a Chrome session logged in to
  reddit.com) or rdt-cli (imports a `reddit_session` cookie). rdt-cli supports `search`, `read POST_ID`, `sub NAME`;
  no wiki-page command, so wiki pages would need the same cookie via plain requests.
- Agent-reach's notes say Reddit closed self-service API app registration in 2025-11, so `fetch_reddit.py` (PRAW)
  only works with pre-existing credentials.
- To enable rdt-cli (not done, needs your approval to install from git and a browser login):
  `python3 -m pip install --user 'git+https://github.com/public-clis/rdt-cli.git@5e4fb3720d5c174e976cd425ccc3b879d52cac66'`
  then `rdt login` (extracts the cookie from your browser) or write `~/.config/rdt-cli/credential.json` by hand.

## Reddit run 2026-10-08
- 48 champions, 3160 threads (1214 under a year old), 2488 champion/opponent pairs after extraction.
- Subreddit lookup: r/<champ>mains (or SUB_OVERRIDES) first; if that is 403/404 or returns no threads the fetcher falls back to r/<champ> (e.g. r/shen, r/jinx, r/lux, r/janna). The JSON records which sub was used, and a rerun starts from that sub, so fixing a champion costs 2-4 requests. r/velkozmains and r/taliyahmains are tiny.
  Aurelion Sol lives at r/Aurelion_Sol_mains (override added; r/aurelionsolmains is empty).
- Comments were not fetched in the first run. Thread bodies are often the question; the answer is in the comments.

## Rules for turning Reddit threads into lane tips (decided 2026-10-08)
- Prefer newer threads. Each thread carries `recency_weight` (1.0 under 1 year, 0.7 under 2, 0.4 under 4, 0.2 older)
  and the fetcher pulls both the all-time and the last-year top feed so recent posts are not drowned out.
- Item, build and rune advice older than 2 years is not useful (`stale_items: true`); ignore it entirely.
- Lane matchup dynamics (who wins early, trade windows, what to dodge) mostly stay true across patches, so old
  matchup threads still count, just at lower weight. Exception: champions reworked since the thread was written.
  Mid-lane reworks to keep in mind, verify against patch notes before trusting: Viktor (Arcane update, late 2024),
  LeBlanc (Sep 2024), Corki (May 2024), Aurelion Sol (Feb 2023), Syndra, Ahri and Taliyah (2022 mid-scope updates);
  Aurora, Mel, Smolder and Hwei are new since 2024, so only recent threads mention them.
- When old and new threads disagree about a matchup, the newer one wins; when they agree, that is a strong tip.
- The old-format JSON files (no `feeds` key) from the first run are upgraded in place on the next run: one extra
  request per champion for the last-year feed.

## Next
- Run `./run_all.sh` (xlsx is in the repo now), review rows flagged Mismatch and the Reddit tips column.
- Reddit snippets are picked mechanically; expect some noise (item talk, tangents). `python3 extract_tips.py show A B`
  shows everything for a pair. Running `./run_all.sh comments` overnight adds the answers from question threads.
