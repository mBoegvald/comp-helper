# Pick Helper

Draft helper for League of Legends, all five roles. It ranks picks for your draft using lane win rates from
Lolalytics (Emerald+), tips from each champion's mains subreddit, and hand-written champion knowledge.

## Start it

**Windows:** double-click `Start Pick Helper.bat`. The page opens in your browser. Close the black window to stop it.

**Linux:** run `./start.sh`.

The page has three tabs:

- **Draft:** choose your role and fill in what you know of both teams, bans and fearless picks. Picks update as
  you type. Open a pick to see lane notes and Reddit tips with links to the threads.
- **Lookup:** every matchup for one champion in one role. Click a row for the full matchup.
- **Data:** what the data covers, and buttons to update it. Updates run in the background and keep going if
  you close the page.

## Set up on Windows

1. Install Python 3.10 or newer from https://www.python.org/downloads/ and tick **Add python.exe to PATH**
   during setup.
2. Copy this whole folder to the Windows PC (about 30 MB). Keep the `data` folder: it holds the Reddit
   downloads, so updates only fetch what is new.
3. Double-click `Start Pick Helper.bat`. The first start installs `openpyxl`, the only extra package.

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

Close the workbooks in Excel before updating, because Windows cannot replace a file that is open.

## Edit the knowledge

The workbooks are `midlane_overview.xlsx` (mid) and `roles/<role>.xlsx`. You can edit the Champions sheet
(archetype, comps, pick when, good into, struggles into) and the Matchups sheet (Result for champion, Lane tip).
Your edits survive every update. The defaults for new champions live in `role_data.py`.

`NOTES.md` has the design notes and data caveats.
