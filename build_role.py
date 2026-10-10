#!/usr/bin/env python3
"""Refresh a role's Lolalytics data in data/pickhelper.db.

  python3 build_role.py top            # discover the champion pool, fetch every counters page, replace the role's rows
  python3 build_role.py all            # every role

Champion pool: every champion with >= POOL_MIN_GAMES games against one of the role's seed champions on Lolalytics
(Emerald+, current patch), plus every champion listed for the role in role_data.CHAMPS, plus whoever is already in
the pool (it only grows). The role's lola rows are replaced in one transaction, so stopping halfway keeps the old
data; a fetch that returns far fewer rows than before (site change, outage) is refused instead of saved.
Curated edits live in their own tables and are never touched here; db.py combines both when the picker reads.
"""

import datetime as dt
import sys

import db
import fetch_lolalytics as lola
import role_data

POOL_MIN_GAMES = 150
KEEP_RATIO = 0.6  # refuse to save a fetch with fewer rows than this share of the previous one


def pool_for(role: str, delay: float):
    lane = role_data.ROLES[role]["lane"]
    pool = set()
    for seed in role_data.ROLES[role]["seeds"]:
        pool |= {r["opponent"] for r in lola.fetch(seed, delay, lane) if r["games"] and r["games"] >= POOL_MIN_GAMES}
    return pool


def build(role: str, delay: float):
    lane = role_data.ROLES[role]["lane"]
    conn = db.connect()
    print(f"== {role}: discovering champion pool")
    champs = sorted(pool_for(role, delay) | set(db.pool(conn, role)))
    print(f"   {len(champs)} champions")
    print(f"== {role}: fetching counters ({len(champs)} requests, {delay}s apart)")
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    rows = []
    for c in champs:
        got = lola.fetch(c, delay, lane)
        rows += [
            (
                role,
                c,
                r["opponent"],
                r["wr"],
                r["delta_vs_avg"],
                r["delta_norm"],
                r["opp_avg_wr"],
                r["games"],
                r["patch"],
                r["tier"],
                lane,
                now,
            )
            for r in got
        ]
        print(f"  {c}: {len(got)} opponents", flush=True)
    before = conn.execute("SELECT count(*) FROM lola WHERE role = ?", (role,)).fetchone()[0]
    if len(rows) < before * KEEP_RATIO:
        sys.exit(
            f"== {role}: only {len(rows)} rows fetched against {before} before; keeping the old data. "
            f"Check that lolalytics.com still works and rerun."
        )
    with conn:
        conn.executemany("INSERT OR IGNORE INTO pool VALUES (?, ?)", [(role, c) for c in champs])
        conn.execute("DELETE FROM lola WHERE role = ?", (role,))
        conn.executemany("INSERT OR REPLACE INTO lola VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        db.touch(conn, f"lola_updated:{role}")
    print(f"== {role}: {len(champs)} champions, {len(rows)} Lolalytics rows saved")


def main():
    roles = [a for a in sys.argv[1:] if not a.startswith("--")] or ["all"]
    if roles == ["all"]:
        roles = list(role_data.ROLES)
    for r in roles:
        r = role_data.ROLE_ALIASES.get(r, r)
        if r not in role_data.ROLES:
            sys.exit(f"unknown role {r}; use {', '.join(role_data.ROLES)} or all")
        build(r, delay=1.5)


if __name__ == "__main__":
    main()
