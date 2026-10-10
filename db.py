"""The pick helper's SQLite database (data/pickhelper.db) and the read model built from it.

Generated tables, replaced by the update stages:
  lola           Lolalytics counters per role, one row per direction (build_role.py)
  reddit_tips    per (champion, opponent): mention count and newest date (extract_tips.py build)
  reddit_snippet the best snippets per (champion, opponent) with date and thread link
Grow-only:
  pool           champions per role (discovered from Lolalytics, plus anyone with curated data)
Accounts (hosted mode only, see auth.py): account, session (hashed tokens), attempt (rate limits).
Community notes (hosted mode, see notes.py): community_note, suggested by accounts, shown once approved.
Curated layer, the admin's own knowledge (web page; first filled from the old workbooks), never touched by an
update (called the hand layer until 2026-10-10; connect() renames old tables):
  curated_champion per role and champion; NULL fields fall back to role_data.py
  curated_matchup  per role and pair: a curated label for 'Result for champion' and/or a lane tip
  role_note      free rows from the old Comps/Notes sheets

champions(role) and matchups(role) rebuild what the workbooks used to hold, so picker.py scores exactly as before.
"""

import datetime as dt
import os
import re
import sqlite3
from pathlib import Path

import role_data

HERE = Path(__file__).resolve().parent
PATH = Path(os.environ.get("PICKHELPER_DB") or HERE / "data" / "pickhelper.db")  # env var: tests, a second copy
MIN_GAMES = 100  # matchup rows kept; label() marks < LOW_SAMPLE_GAMES as 'low sample'
LOW_SAMPLE_GAMES = 200
# Labels use Lolalytics' normalised delta (dNorm), not the raw win rate: the site measures every matchup from the
# perspective of an Emerald+ player, who wins ~51.3% of mixed-rank games, so raw WRs for A vs B and B vs A sum to
# ~102-103%. dNorm is close to antisymmetric, and both directions are averaged when available.
FAVORED_DELTA = 2.0
UNFAVORED_DELTA = -2.0
TOP_N = 5  # data-derived names in Good into / Struggles into
CURATED_CHAMP_FIELDS = ("archetype", "damage", "comps", "good_into", "struggles_into", "pick_when", "blind_safe")

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS pool (role TEXT NOT NULL, champion TEXT NOT NULL, PRIMARY KEY (role, champion));
CREATE TABLE IF NOT EXISTS lola (
  role TEXT NOT NULL, champion TEXT NOT NULL, opponent TEXT NOT NULL, wr REAL, delta_vs_avg REAL, delta_norm REAL,
  opp_avg_wr REAL, games INTEGER, patch TEXT, tier TEXT, lane TEXT, fetched_at TEXT,
  PRIMARY KEY (role, champion, opponent));
CREATE TABLE IF NOT EXISTS reddit_tips (
  champion TEXT NOT NULL, opponent TEXT NOT NULL, mentions INTEGER, weighted REAL, newest TEXT,
  PRIMARY KEY (champion, opponent));
CREATE TABLE IF NOT EXISTS reddit_snippet (
  champion TEXT NOT NULL, opponent TEXT NOT NULL, rank INTEGER NOT NULL, text TEXT, published TEXT, url TEXT,
  PRIMARY KEY (champion, opponent, rank));
CREATE TABLE IF NOT EXISTS curated_champion (
  role TEXT NOT NULL, champion TEXT NOT NULL, archetype TEXT, damage TEXT, comps TEXT, good_into TEXT,
  struggles_into TEXT, pick_when TEXT, blind_safe TEXT, updated_at TEXT, PRIMARY KEY (role, champion));
CREATE TABLE IF NOT EXISTS curated_matchup (
  role TEXT NOT NULL, champion TEXT NOT NULL, opponent TEXT NOT NULL, result TEXT, tip TEXT, updated_at TEXT,
  PRIMARY KEY (role, champion, opponent));
CREATE TABLE IF NOT EXISTS role_note (
  role TEXT NOT NULL, sheet TEXT NOT NULL, idx INTEGER NOT NULL, cells TEXT, PRIMARY KEY (role, sheet, idx));
CREATE TABLE IF NOT EXISTS account (
  id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE COLLATE NOCASE, pw_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'contributor' CHECK (role IN ('contributor', 'admin')),
  blocked INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS session (
  token_hash TEXT PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES account(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL, expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS attempt (ip TEXT NOT NULL, kind TEXT NOT NULL, at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS attempt_by_ip ON attempt (ip, kind, at);
CREATE TABLE IF NOT EXISTS community_note (
  id INTEGER PRIMARY KEY, role TEXT NOT NULL, champion TEXT NOT NULL, opponent TEXT, text TEXT NOT NULL, source TEXT,
  account_id INTEGER REFERENCES account(id) ON DELETE SET NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
  created_at TEXT NOT NULL, reviewed_at TEXT, review_note TEXT);
CREATE INDEX IF NOT EXISTS community_note_by_status ON community_note (status, created_at);
CREATE INDEX IF NOT EXISTS community_note_by_account ON community_note (account_id, status);
"""


def connect(path=None) -> sqlite3.Connection:
    """New connection with the schema in place. Writers use `with conn:` so a stop or crash rolls back."""
    path = Path(path or PATH)
    path.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # e.g. deleting an account deletes its sessions
    _rename_old_tables(conn)
    conn.executescript(SCHEMA)
    return conn


RENAMED_TABLES = (("hand_champion", "curated_champion"), ("hand_matchup", "curated_matchup"))  # 2026-10-10


def _rename_old_tables(conn):
    """Databases from before a table was renamed get the new name in place: no copy, nothing lost."""
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    with conn:
        for old, new in RENAMED_TABLES:
            if old in tables and new not in tables:
                conn.execute(f"ALTER TABLE {old} RENAME TO {new}")


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_meta(conn, key, default=None):
    r = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return r[0] if r else default


def set_meta(conn, key, value):
    conn.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (key, str(value)))


def touch(conn, *keys):
    """Mark data as changed (readers cache on the 'stamp'); extra keys get the current time, e.g. 'lola_updated:top'."""
    set_meta(conn, "stamp", int(get_meta(conn, "stamp", 0)) + 1)
    for k in keys:
        set_meta(conn, k, now())


def stamp(conn) -> int:
    return int(get_meta(conn, "stamp", 0))


def backup(dest: Path):
    """Copy the database (consistent even while others write) to dest."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    src = connect()
    out = sqlite3.connect(dest)
    try:
        src.backup(out)
    finally:
        out.close()
        src.close()


def norm(name) -> str:
    """Key for matching champion names across sources (ignores case, spaces, punctuation)."""
    return re.sub(r"[^a-z0-9]", "", str(name or "").lower())


def label(dnorm: float, games) -> str:
    if games is not None and games < LOW_SAMPLE_GAMES:
        return "low sample"
    if dnorm >= FAVORED_DELTA:
        return "Favored"
    if dnorm <= UNFAVORED_DELTA:
        return "Unfavored"
    return "Even"


def norm_label(x) -> str:
    x = str(x or "").strip().lower()
    if x.startswith("fav"):
        return "Favored"
    if x.startswith("unfav"):
        return "Unfavored"
    if x.startswith("even") or x.startswith("skill") or x.startswith("same"):
        return "Even"
    return x


# ---------------------------------------------------------------- read model


def combined(rows):
    """(champ, opp) -> dict(wr, dnorm, games, patch, tier, source), both directions averaged where present."""
    direct = {(r["champion"], r["opponent"]): r for r in rows}
    out = {}
    for (c, o), fwd in direct.items():
        rev = direct.get((o, c))
        wrs, dns, games = [float(fwd["wr"])], [float(fwd["delta_norm"])], [fwd["games"] or 0]
        if rev:
            wrs.append(100 - float(rev["wr"]))
            dns.append(-float(rev["delta_norm"]))
            games.append(rev["games"] or 0)
        out[(c, o)] = {
            "wr": sum(wrs) / len(wrs),
            "dnorm": sum(dns) / len(dns),
            "games": min(games),
            "patch": fwd["patch"],
            "tier": fwd["tier"],
            "source": "both" if rev else "direct",
        }
    return out


def data_lists(comb, champ):
    """Best and worst opponents by normalised delta: the data part of Good into / Struggles into."""
    pairs = sorted(
        ((v["dnorm"], o) for (c, o), v in comb.items() if c == champ and v["games"] >= MIN_GAMES), reverse=True
    )
    return [o for d, o in pairs[:TOP_N] if d >= 1.0], [o for d, o in pairs[::-1][:TOP_N] if d <= -1.0]


def defaults(role, champ):
    """(archetype, damage, comps, pick when, blind-safe) from role_data.py, before any curated edit."""
    return role_data.CHAMPS.get(role, {}).get(champ, ("Flex", role_data.damage_of(champ), "", "", "Mostly"))


def lola_rows(conn, role):
    return [dict(r) for r in conn.execute("SELECT * FROM lola WHERE role = ?", (role,))]


def pool(conn, role):
    names = {r[0] for r in conn.execute("SELECT champion FROM pool WHERE role = ?", (role,))}
    names |= {r[0] for r in conn.execute("SELECT champion FROM curated_champion WHERE role = ?", (role,))}
    return sorted(names | set(role_data.CHAMPS.get(role, {})))


def champions(conn, role, comb=None):
    """Champions sheet rows: name, arch, dmg, comps, good, bad, when, blind (curated edit > role_data > 'Flex')."""
    comb = comb if comb is not None else combined(lola_rows(conn, role))
    curated = {r["champion"]: dict(r) for r in conn.execute("SELECT * FROM curated_champion WHERE role = ?", (role,))}
    archs = role_data.ARCHETYPES.get(role, {})
    out = []
    for c in pool(conn, role):
        arch, dmg, comps, when, blind = defaults(role, c)
        h = curated.get(c, {})
        arch, dmg, comps, when, blind = (
            h.get("archetype") or arch,
            h.get("damage") or dmg,
            h.get("comps") or comps,
            h.get("pick_when") or when,
            h.get("blind_safe") or blind,
        )
        _words, g_default, b_default = archs.get(arch, ([], "", ""))
        good, bad = data_lists(comb, c)
        good_txt = "; ".join(x for x in (", ".join(good), h.get("good_into") or g_default) if x)
        bad_txt = "; ".join(x for x in (", ".join(bad), h.get("struggles_into") or b_default) if x)
        out.append(
            {
                "name": c,
                "arch": arch,
                "dmg": dmg,
                "comps": comps,
                "good": good_txt,
                "bad": bad_txt,
                "when": when,
                "blind": blind,
            }
        )
    return out


def reddit_tip_rows(conn):
    """norm(champion), norm(opponent) -> {mentions, newest, tips: [{text, date, url}]}"""
    out = {}
    for r in conn.execute("SELECT * FROM reddit_tips"):
        out[(norm(r["champion"]), norm(r["opponent"]))] = {
            "mentions": r["mentions"],
            "newest": r["newest"] or "",
            "tips": [],
        }
    for r in conn.execute("SELECT * FROM reddit_snippet ORDER BY champion, opponent, rank"):
        d = out.get((norm(r["champion"]), norm(r["opponent"])))
        if d is not None:
            d["tips"].append({"text": r["text"], "date": r["published"] or "", "url": r["url"] or ""})
    return out


def matchups(conn, role, comb=None, tips=None):
    """Matchups sheet rows, sorted by (champion, opponent): every pair with >= MIN_GAMES games for a pool
    champion, plus every pair with a curated label or tip (even without data)."""
    comb = comb if comb is not None else combined(lola_rows(conn, role))
    tips = tips if tips is not None else reddit_tip_rows(conn)
    names = set(pool(conn, role))
    curated = {
        (r["champion"], r["opponent"]): dict(r)
        for r in conn.execute("SELECT * FROM curated_matchup WHERE role = ?", (role,))
    }
    out = []
    for c, o in sorted({k for k in comb if k[0] in names} | set(curated)):
        v, h = comb.get((c, o)), curated.get((c, o), {})
        curated_label, tip = h.get("result") or None, h.get("tip") or None
        if (v is None or v["games"] < MIN_GAMES) and not curated_label and not tip:
            continue
        row = {
            "champ": c,
            "opp": o,
            "tip": tip,
            "wr": None,
            "dnorm": None,
            "games": None,
            "label": "no data",
            "patch": None,
            "source": None,
            "mismatch": None,
            "result": curated_label,
            "curated_result": curated_label,  # the stored label itself, also when it agrees with the data
        }
        if v is not None:
            lab = label(v["dnorm"], v["games"])
            row.update(
                wr=round(v["wr"], 2),
                dnorm=round(v["dnorm"], 2),
                games=v["games"],
                label=lab,
                patch=f"{v['patch']} {v['tier']}",
                source=v["source"],
                result=curated_label or lab,
                mismatch="yes"
                if curated_label and norm_label(curated_label) != norm_label(lab) and "low sample" not in lab
                else None,
            )
        # Reddit: this champion's mains about the opponent, then the opponent's mains about this champion
        parts, ment, newest = [], 0, ""
        for t, tag in ((tips.get((norm(c), norm(o))), ""), (tips.get((norm(o), norm(c))), f"[{o} mains] ")):
            if t:
                ment += t["mentions"] or 0
                newest = max(newest, t["newest"])
                parts += [tag + x["text"] for x in t["tips"] if x["text"]]
        row.update(
            reddit_tips=" | ".join(parts)[:4000] if parts else None,
            reddit_mentions=ment if parts else None,
            reddit_newest=newest if parts else None,
        )
        out.append(row)
    return out


def patch(conn):
    """Patch and rank of the most recent Lolalytics fetch, any role (e.g. '16.20 EMERALD+')."""
    r = conn.execute("SELECT patch, tier FROM lola WHERE patch != '' ORDER BY fetched_at DESC LIMIT 1").fetchone()
    return f"{r['patch']} {r['tier']}".strip() if r else ""


# ---------------------------------------------------------------- curated layer writes


def set_curated_champion(conn, role, champion, fields: dict):
    """Upsert curated fields for a champion; a field set to '' or None goes back to the role_data default."""
    bad = set(fields) - set(CURATED_CHAMP_FIELDS)
    if bad:
        raise ValueError(f"unknown field(s) {', '.join(sorted(bad))}")
    with conn:
        cur = dict(
            conn.execute("SELECT * FROM curated_champion WHERE role = ? AND champion = ?", (role, champion)).fetchone()
            or {}
        )
        cur.update({k: (str(v).strip() or None) if v is not None else None for k, v in fields.items()})
        vals = [cur.get(k) for k in CURATED_CHAMP_FIELDS]
        if any(vals):
            conn.execute(
                f"INSERT OR REPLACE INTO curated_champion (role, champion, {', '.join(CURATED_CHAMP_FIELDS)}, updated_at) "
                f"VALUES (?, ?, {', '.join('?' * len(vals))}, ?)",
                (role, champion, *vals, now()),
            )
        else:
            conn.execute("DELETE FROM curated_champion WHERE role = ? AND champion = ?", (role, champion))
        conn.execute("INSERT OR IGNORE INTO pool VALUES (?, ?)", (role, champion))
        touch(conn)


def set_curated_matchup(conn, role, champion, opponent, result=None, tip=None):
    """Curated label ('Favored', 'Even', 'Unfavored' or free text) and lane tip for a pair; both empty removes the row."""
    with conn:
        write_curated_matchup(conn, role, champion, opponent, result, tip)
        touch(conn)


def write_curated_matchup(conn, role, champion, opponent, result, tip):
    """The write itself, inside the caller's transaction (set_curated_matchup, notes.promote_to_tip)."""
    result, tip = (str(result).strip() or None) if result else None, (str(tip).strip() or None) if tip else None
    if result or tip:
        conn.execute(
            "INSERT OR REPLACE INTO curated_matchup VALUES (?, ?, ?, ?, ?, ?)",
            (role, champion, opponent, result, tip, now()),
        )
    else:
        conn.execute(
            "DELETE FROM curated_matchup WHERE role = ? AND champion = ? AND opponent = ?",
            (role, champion, opponent),
        )
