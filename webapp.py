#!/usr/bin/env python3
"""Local web page for the pick helper. Runs on Windows and Linux; only needs Python 3.10+ (no extra packages).

  python webapp.py              # opens http://127.0.0.1:8765 in your browser
  python webapp.py --port 9000 --no-browser

Everything stays on this computer: the page reads and edits data/pickhelper.db, and the Data tab starts
update.py in the background (it keeps running if you close the page or this window).
"""

import argparse
import contextlib
import datetime as dt
import json
import os
import signal
import subprocess
import sys
import threading
import traceback
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.chdir(HERE)
sys.path.insert(0, str(HERE))

import auth
import db
import notes
import picker
import role_data
import update

DIST = HERE / "web" / "dist"  # the built Svelte page (frontend/), committed so no Node is needed to run
PAGE = DIST / "index.html"
ASSET_TYPES = {
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".woff2": "font/woff2",
}
REDDIT_DIR = HERE / "data" / "reddit"
_lock = threading.Lock()
# set by main(): --hosted, --insecure-cookies, --public-host, --behind-proxy
CONFIG = {"hosted": False, "secure_cookies": True, "public_hosts": set(), "behind_proxy": False}
LOCAL_ADMIN = {"id": None, "username": "you", "role": "admin"}  # local mode: no accounts, you are admin
SESSION_COOKIE = "ph_session"
_tips_cache = {"stamp": None, "data": {}}
_names_cache = {"stamp": None, "names": {}}
_notes_cache = {"stamp": None, "data": {}}


# ---------------------------------------------------------------- data access


def role_of(r: str) -> str:
    r = (r or "mid").lower()
    r = role_data.ROLE_ALIASES.get(r, r)
    if r not in role_data.ROLES:
        raise ValueError(f"unknown role {r}")
    return r


def load(role):
    with _lock:
        return picker.load_full(role)


def db_stamp():
    conn = db.connect()
    try:
        return db.stamp(conn)
    finally:
        conn.close()


def all_names():
    """champion key -> display name, from every role plus the Reddit files."""
    stamp = (db_stamp(), len(list(REDDIT_DIR.glob("*.json"))))
    if _names_cache["stamp"] == stamp:
        return _names_cache["names"]
    names = {}
    for r in role_data.ROLES:
        try:
            champs, mu, info = load(r)
        except FileNotFoundError:
            continue
        for k, c in champs.items():
            names.setdefault(k, c["name"])
        for d in info.values():
            names.setdefault(picker.key(d["opp"]), d["opp"])
    for f in REDDIT_DIR.glob("*.json"):
        try:
            n = json.loads(f.read_text(encoding="utf-8"))["champion"]
            names.setdefault(picker.key(n), n)
        except (OSError, ValueError, KeyError):
            pass
    _names_cache.update(stamp=stamp, names=names)
    return names


def display(k):
    return all_names().get(k, k)


def reddit_tips():
    """(champ key, opp key) -> list of snippets written by champ's mains about the matchup."""
    conn = db.connect()
    try:
        stamp = db.get_meta(conn, "tips_updated")
        if _tips_cache["stamp"] == stamp:
            return _tips_cache["data"]
        data = {}
        for r in conn.execute("SELECT * FROM reddit_tips"):
            data[(picker.key(r["champion"]), picker.key(r["opponent"]))] = {
                "mentions": r["mentions"] or 0,
                "newest": r["newest"] or "",
                "tips": [],
            }
        for r in conn.execute("SELECT * FROM reddit_snippet ORDER BY champion, opponent, rank"):
            d = data.get((picker.key(r["champion"]), picker.key(r["opponent"])))
            if d is not None and (r["text"] or "").strip():
                d["tips"].append({"text": r["text"].strip(), "date": r["published"] or "", "url": r["url"] or ""})
    finally:
        conn.close()
    _tips_cache.update(stamp=stamp, data=data)
    return data


def community_notes():
    """(role, champion key, opponent key or '') -> approved community notes, cached until the database changes."""
    conn = db.connect()
    try:
        stamp = db.stamp(conn)
        if _notes_cache["stamp"] != stamp:
            _notes_cache.update(stamp=stamp, data=notes.approved_index(conn, key=picker.key))
    finally:
        conn.close()
    return _notes_cache["data"]


def matchup(role, a, b):
    """Everything we know about champion a vs champion b in this role, from a's point of view."""
    champs, mu, info = load(role)
    fwd, rev = info.get((a, b)), info.get((b, a))
    d = {"champ": display(a), "opp": display(b), "score": mu.get((a, b), (None, None))[0]}
    src = fwd or rev
    if src and isinstance(src.get("wr"), (int, float)):
        flip = src is rev
        d.update(
            wr=round(100 - src["wr"], 2) if flip else src["wr"],
            dnorm=round(-src["dnorm"], 2) if flip else src["dnorm"],
            games=src["games"],
        )
    dn, games = d.get("dnorm"), d.get("games")
    if isinstance(dn, (int, float)):  # same thresholds as fetch_lolalytics.label, but keep the direction
        d["label"] = "Favored" if dn >= 2 else "Unfavored" if dn <= -2 else "Even"
        d["low_sample"] = isinstance(games, (int, float)) and games < 200
    else:
        d["label"], d["low_sample"] = None, False
    # the stored label as is: hiding it when it agreed with the data made the editor save it away
    d["curated_result"] = (fwd or {}).get("curated_result")
    d["mismatch"] = bool((fwd or {}).get("mismatch"))
    d["tips"] = []
    if fwd and fwd.get("curated_tip"):
        d["tips"].append({"from": "notes", "who": display(a), "text": fwd["curated_tip"]})
    if rev and rev.get("curated_tip"):
        d["tips"].append({"from": "notes", "who": display(b), "text": rev["curated_tip"]})
    rt = reddit_tips()
    d["reddit"] = []
    for x, y in ((a, b), (b, a)):
        r = rt.get((x, y))
        if r:
            d["reddit"].append({"who": display(x), "mentions": r["mentions"], "newest": r["newest"], "tips": r["tips"]})
    cn = community_notes()  # each side's notes, like the lane tips
    d["community"] = [{**n, "who": display(x)} for x, y in ((a, b), (b, a)) for n in cn.get((role, x, y), [])]
    return d


def find(n, champs=None):
    """champion key for typed text: exact name or nickname first (any role), then a unique prefix,
    then a unique substring, preferring this role's pool."""
    names = all_names()
    q = picker.key(n)
    if q in names or (champs and q in champs):
        return q
    for test in (lambda x: x.startswith(q), lambda x: q in x):
        for pool in (champs or {}, names):
            hits = [x for x in pool if test(x)]
            if len(hits) == 1:
                return hits[0]
    return q


def champ_card(c):
    return {
        "name": c["name"],
        "arch": c["arch"],
        "dmg": c["dmg"],
        "comps": c["comps"],
        "good": c["good"],
        "bad": c["bad"],
        "when": c["when"],
        "blind": c["blind"],
    }


def empty_card(name):
    """Same shape as champ_card for a champion outside the role's pool."""
    return {"name": name, **dict.fromkeys(("arch", "dmg", "comps", "good", "bad", "when", "blind"))}


def damage_of(name, role_hint=None):
    k = picker.key(name)
    roles = [role_hint] if role_hint else []
    for r in roles + [r for r in role_data.ROLES if r not in roles]:
        try:
            champs = load(r)[0]
        except FileNotFoundError:
            continue
        if k in champs and champs[k].get("dmg"):
            return champs[k]["dmg"]
    return role_data.damage_of(display(k))


# ---------------------------------------------------------------- API


def api_meta(_q, ctx=None):
    conn = db.connect()
    try:
        updated = {r: epoch(db.get_meta(conn, f"lola_updated:{r}")) for r in role_data.ROLES}
        patch, tips_updated = db.patch(conn), epoch(db.get_meta(conn, "tips_updated"))
    finally:
        conn.close()
    roles = []
    for r in role_data.ROLES:
        try:
            champs, mu, info = load(r)
            roles.append(
                {
                    "id": r,
                    "champions": sorted(c["name"] for c in champs.values()),
                    "matchups": len(info),
                    "updated": updated[r],
                }
            )
        except FileNotFoundError:
            roles.append({"id": r, "champions": [], "matchups": 0, "updated": None})
    reddit_files = list(REDDIT_DIR.glob("*.json"))
    return {
        "roles": roles,
        "names": sorted(set(all_names().values()), key=str.lower),
        "styles": list(picker.STYLE_WORDS),
        "patch": patch,
        "reddit_champions": len(reddit_files),
        "tips_updated": tips_updated,
    }


def epoch(iso):
    """'2026-10-09T20:17:03Z' -> seconds since 1970 (what the page's 'ago' expects), or None."""
    if not iso:
        return None
    return dt.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).timestamp()


def api_recommend(q, ctx=None):
    role = role_of(q.get("role"))
    champs, mu, info = load(role)
    names = all_names()
    enemy_in, ally_in = q.get("enemy") or {}, q.get("ally") or {}
    slots = {}

    def resolve(n):
        return find(n, champs)

    enemies, allies = [], []
    for side, src, out in (("enemy", enemy_in, enemies), ("ally", ally_in, allies)):
        for r, n in src.items():
            if not n or not str(n).strip() or (side == "ally" and r == role):
                continue
            k = resolve(str(n))
            if k in names:  # unfinished or misspelled names ("ga") are reported in slots but not scored
                out.append((r, k))
            slots[f"{side}.{r}"] = {"name": names.get(k), "known": k in names, "in_role": k in champs}
    enemy_main = next((k for r, k in enemies if r == role), None)
    enemy_keys = [k for _, k in enemies]
    if enemy_main:  # main enemy first so the 'vs' reason leads
        enemy_keys = [enemy_main] + [k for k in enemy_keys if k != enemy_main]

    need = (q.get("need") or "").lower() or None
    detected = None
    if not need:
        dmg = [damage_of(display(k), r) for r, k in allies]
        ap = sum("AP" in d for d in dmg)
        ad = sum(d.startswith("AD") for d in dmg)
        detected = "ap" if ad > ap else "ad" if ap > ad + 1 else None
        need = detected
    style = q.get("style") or None
    if style not in picker.STYLE_WORDS:
        style = None
    unavailable = {resolve(n) for n in q.get("unavailable") or [] if str(n).strip()}
    taken = set(enemy_keys) | {k for _, k in allies} | unavailable

    rows = []
    for c in champs:
        if c in taken:
            continue
        parts = []
        s, _why = picker.score(c, enemy_keys, enemy_main, [k for _, k in allies], style, need, champs, mu, parts)
        rows.append((s, c, parts))
    rows.sort(key=lambda x: (-x[0], champs[x[1]]["name"]))

    def card(s, c, parts, full):
        out = {"key": c, **champ_card(champs[c]), "score": round(s, 2), "parts": parts}
        for p in parts:
            if p["kind"] == "matchup":
                m = matchup(role, c, p["enemy"])
                p.update({k: m.get(k) for k in ("wr", "dnorm", "games", "label", "low_sample")})
        if enemy_main:
            out["lane"] = matchup(role, c, enemy_main) if full else None
        return out

    top = max(1, min(int(q.get("top") or 8), 30))
    best = [card(s, c, p, True) for s, c, p in rows[:top]]
    worst = [card(s, c, p, False) for s, c, p in rows[::-1][:3] if s < 0]
    return {
        "role": role,
        "enemy_main": display(enemy_main) if enemy_main else None,
        "need": need,
        "need_detected": detected,
        "style": style,
        "slots": slots,
        "picks": best,
        "avoid": worst,
        "candidates": len(rows),
    }


def api_champion(q, ctx=None):
    role = role_of(q.get("role"))
    champs, mu, info = load(role)
    k = find(q.get("name", ""), champs)
    opps = sorted({o for (a, o) in mu if a == k})
    rows = []
    for o in opps:
        m = matchup(role, k, o)
        rows.append(
            {
                "opp": display(o),
                "score": m["score"],
                "wr": m.get("wr"),
                "dnorm": m.get("dnorm"),
                "games": m.get("games"),
                "label": m.get("label"),
                "low_sample": m.get("low_sample"),
                "notes": len(m["tips"]),
                "reddit": sum(len(x["tips"]) for x in m["reddit"]),
            }
        )
    rows.sort(key=lambda r: -(r["score"] or 0))
    return {
        "role": role,
        "champion": champ_card(champs[k]) if k in champs else empty_card(display(k)),
        "in_role": k in champs,
        "matchups": rows,
        "community": community_notes().get((role, k, ""), []),
    }


def api_matchup(q, ctx=None):
    role = role_of(q.get("role"))
    champs = load(role)[0]
    return matchup(role, find(q.get("a", ""), champs), find(q.get("b", ""), champs))


def api_status(_q, ctx=None):
    lines = []
    if update.LOG.exists():
        with update.LOG.open(encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-80:]
    return {"running": update.is_running(), "log": "".join(lines)}


def api_update(q, ctx=None):
    stage = q.get("stage") or "all"
    if stage not in update.STAGES:
        raise ValueError(f"unknown stage {stage}")
    if update.is_running():
        return {"ok": False, "error": "An update is already running."}
    cmd = [sys.executable, str(HERE / "update.py"), stage]
    kw = dict(cwd=HERE, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.name == "nt":  # own process group, no console window, survives closing the web page
        kw["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | 0x00000008  # DETACHED_PROCESS
    else:
        kw["start_new_session"] = True
    subprocess.Popen(cmd, **kw)
    return {"ok": True}


def api_stop(_q, ctx=None):
    if not update.is_running():
        return {"ok": False, "error": "Nothing is running."}
    pid = update.running_pid()
    if not pid:
        return {"ok": False, "error": "Could not find the update process."}
    if os.name == "nt":
        subprocess.call(
            ["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    else:
        subprocess.call(["pkill", "-TERM", "-P", str(pid)])
        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, signal.SIGTERM)
    update.log("stopped from the web page (rerun to continue; finished champions are kept)")
    return {"ok": True}


# ---------------------------------------------------------------- curated edits (the admin's own knowledge)

CURATED_RESULTS = ("Favored", "Even", "Even / skill", "Unfavored")


def pool_name(role, name):
    """Exact champion name as stored for this role, for typed or key-shaped input."""
    champs = load(role)[0]
    k = find(str(name or ""), champs)
    if k not in champs:
        raise ValueError(f"{name!r} is not a {role} champion")
    return champs[k]["name"]


def api_curated_champion_get(q, ctx=None):
    """What a champion's edit form needs: the curated edits, the role_data defaults they override, the archetypes."""
    role = role_of(q.get("role"))
    name = pool_name(role, q.get("name"))
    conn = db.connect()
    try:
        r = conn.execute("SELECT * FROM curated_champion WHERE role = ? AND champion = ?", (role, name)).fetchone()
    finally:
        conn.close()
    arch, dmg, comps, when, blind = db.defaults(role, name)
    archs = role_data.ARCHETYPES.get(role, {})
    _w, g_def, b_def = archs.get((r and r["archetype"]) or arch, ([], "", ""))
    return {
        "role": role,
        "champion": name,
        "curated": {k: (r[k] if r else None) for k in db.CURATED_CHAMP_FIELDS},
        "defaults": {
            "archetype": arch,
            "damage": dmg,
            "comps": comps,
            "good_into": g_def,
            "struggles_into": b_def,
            "pick_when": when,
            "blind_safe": blind,
        },
        "archetypes": sorted(archs),
        "updated_at": r["updated_at"] if r else None,
    }


def api_curated_champion_set(q, ctx=None):
    role = role_of(q.get("role"))
    name = pool_name(role, q.get("champion"))
    fields = q.get("fields") or {}
    if not isinstance(fields, dict):
        raise ValueError("fields must be an object")
    conn = db.connect()
    try:
        db.set_curated_champion(conn, role, name, fields)
    finally:
        conn.close()
    return api_curated_champion_get({"role": role, "name": name})


def api_curated_matchup_set(q, ctx=None):
    """Curated label and/or lane tip for champion vs opponent in a role; empty values remove them."""
    role = role_of(q.get("role"))
    champ = pool_name(role, q.get("champion"))
    opp = display(find(str(q.get("opponent") or ""), load(role)[0]))
    if picker.key(opp) not in all_names():
        raise ValueError(f"unknown opponent {q.get('opponent')!r}")
    result = (q.get("result") or "").strip() or None
    if result and result not in CURATED_RESULTS:
        raise ValueError(f"result must be one of {', '.join(CURATED_RESULTS)} or empty")
    conn = db.connect()
    try:
        db.set_curated_matchup(conn, role, champ, opp, result, q.get("tip"))
    finally:
        conn.close()
    return matchup(role, picker.key(champ), picker.key(opp))


# ---------------------------------------------------------------- accounts (hosted mode)


def _hosted_only():
    if not CONFIG["hosted"]:
        raise ValueError("Accounts are only used on the hosted site.")


def _session_cookie(token, max_age):
    c = f"{SESSION_COOKIE}={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age={max_age}"
    return c + ("; Secure" if CONFIG["secure_cookies"] else "")


def _with_db(fn):
    conn = db.connect()
    try:
        return fn(conn)
    finally:
        conn.close()


def api_me(_q, ctx=None):
    user = ctx.user if ctx else LOCAL_ADMIN
    return {"hosted": CONFIG["hosted"], "user": user, "admin": bool(user and user["role"] == "admin")}


def api_signup(q, ctx):
    _hosted_only()

    def run(conn):
        auth.rate_limit(conn, ctx.ip, "signup")
        account_id = auth.create_account(conn, str(q.get("username") or ""), str(q.get("password") or ""))
        return auth.start_session(conn, account_id)

    token = _with_db(run)
    ctx.cookies.append(_session_cookie(token, auth.SESSION_DAYS * 86400))
    ctx.user = _with_db(lambda conn: auth.session_account(conn, token))
    return api_me({}, ctx)


def api_login(q, ctx):
    _hosted_only()

    def run(conn):
        auth.rate_limit(conn, ctx.ip, "login")
        return auth.login(conn, str(q.get("username") or ""), str(q.get("password") or ""))

    token = _with_db(run)
    ctx.cookies.append(_session_cookie(token, auth.SESSION_DAYS * 86400))
    ctx.user = _with_db(lambda conn: auth.session_account(conn, token))
    return api_me({}, ctx)


def api_logout(_q, ctx):
    _hosted_only()
    _with_db(lambda conn: auth.logout(conn, ctx.token))
    ctx.cookies.append(_session_cookie("", 0))
    ctx.user = None
    return api_me({}, ctx)


def api_admin_accounts(_q, ctx=None):
    _hosted_only()
    return {"accounts": _with_db(auth.list_accounts)}


def api_admin_block(q, ctx):
    _hosted_only()
    account_id = int(q.get("id") or 0)
    if ctx.user and account_id == ctx.user["id"]:
        raise ValueError("You cannot block yourself.")
    _with_db(lambda conn: auth.set_blocked(conn, account_id, bool(q.get("blocked"))))
    if q.get("blocked"):
        _with_db(lambda conn: notes.reject_pending_of(conn, account_id, "account blocked"))
    return api_admin_accounts({}, ctx)


# ---------------------------------------------------------------- community notes (hosted mode)


def api_notes_suggest(q, ctx):
    """A note on a champion (no opponent) or on champion vs opponent. Admins' notes are approved at once."""
    _hosted_only()
    role = role_of(q.get("role"))
    champ = pool_name(role, q.get("champion"))
    opp = None
    if q.get("opponent"):
        opp = display(find(str(q["opponent"]), load(role)[0]))
        if picker.key(opp) not in all_names():
            raise ValueError(f"unknown opponent {q['opponent']!r}")
    admin = ctx.user["role"] == ADMIN
    note = _with_db(
        lambda conn: notes.suggest(
            conn, ctx.user["id"], role, champ, opp, q.get("text"), q.get("source"), approve=admin
        )
    )
    return {"note": note}


def api_notes_mine(_q, ctx):
    _hosted_only()
    return {"notes": _with_db(lambda conn: notes.for_account(conn, ctx.user["id"]))}


def api_admin_review_list(_q, ctx=None):
    _hosted_only()
    return {"notes": _with_db(notes.pending)}


def api_admin_review(q, ctx):
    """Approve (with `text` to correct it) or reject (with an optional `note` as reason) a waiting note."""
    _hosted_only()
    note_id, approve = int(q.get("id") or 0), bool(q.get("approve"))
    _with_db(lambda conn: notes.review(conn, note_id, approve, q.get("text"), q.get("note")))
    return api_admin_review_list({}, ctx)


def api_admin_note_promote(q, ctx=None):
    """An approved matchup note becomes the curated lane tip for its side. The page reloads its matchup itself
    (the note's side need not be the side it is looking from)."""
    _hosted_only()
    _with_db(lambda conn: notes.promote_to_tip(conn, int(q.get("id") or 0)))
    return {"ok": True}


def api_admin_note_delete(q, ctx=None):
    _hosted_only()
    _with_db(lambda conn: notes.delete(conn, int(q.get("id") or 0)))
    return {"ok": True}


# ---------------------------------------------------------------- HTTP

# who may call a route: everyone, a signed-in account, or an admin. In local mode every request is the admin.
PUBLIC, USER, ADMIN = "public", "user", "admin"
ROUTES = {
    ("GET", "/api/me"): (api_me, PUBLIC),
    ("GET", "/api/meta"): (api_meta, PUBLIC),
    ("POST", "/api/recommend"): (api_recommend, PUBLIC),
    ("GET", "/api/champion"): (api_champion, PUBLIC),
    ("GET", "/api/matchup"): (api_matchup, PUBLIC),
    ("POST", "/api/signup"): (api_signup, PUBLIC),
    ("POST", "/api/login"): (api_login, PUBLIC),
    ("POST", "/api/logout"): (api_logout, PUBLIC),
    ("GET", "/api/status"): (api_status, ADMIN),
    ("POST", "/api/update"): (api_update, ADMIN),
    ("POST", "/api/stop"): (api_stop, ADMIN),
    ("GET", "/api/curated/champion"): (api_curated_champion_get, ADMIN),
    ("POST", "/api/curated/champion"): (api_curated_champion_set, ADMIN),
    ("POST", "/api/curated/matchup"): (api_curated_matchup_set, ADMIN),
    ("GET", "/api/admin/accounts"): (api_admin_accounts, ADMIN),
    ("POST", "/api/admin/block"): (api_admin_block, ADMIN),
    ("POST", "/api/notes"): (api_notes_suggest, USER),
    ("GET", "/api/notes/mine"): (api_notes_mine, USER),
    ("GET", "/api/admin/review"): (api_admin_review_list, ADMIN),
    ("POST", "/api/admin/review"): (api_admin_review, ADMIN),
    ("POST", "/api/admin/notes/delete"): (api_admin_note_delete, ADMIN),
    ("POST", "/api/admin/notes/promote"): (api_admin_note_promote, ADMIN),
}
MAX_BODY = 64 * 1024
# What the page may load: its own scripts and styles, and champion icons from Riot. An injected script could
# neither run nor send data elsewhere. Styles allow inline because Svelte sets style properties.
CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' https://ddragon.leagueoflegends.com; connect-src 'self' https://ddragon.leagueoflegends.com; "
    "object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
)


class Ctx:
    """One request: who is asking (None when signed out), from where, and cookies to set on the answer."""

    def __init__(self, ip, token=None, user=None):
        self.ip, self.token, self.user, self.cookies = ip, token, user, []


def allowed(user, access):
    if access == PUBLIC:
        return True
    return bool(user) and (access == USER or user["role"] == ADMIN)


class Handler(BaseHTTPRequestHandler):
    server_version = "PickHelper/1"
    timeout = 30  # seconds a connection may stall (a body announced but never sent) before it is dropped

    def log_message(self, fmt, *args):  # quiet console
        pass

    def send(self, code, body: bytes, ctype, cookies=()):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("X-Frame-Options", "DENY")
        if ctype.startswith("text/html"):
            self.send_header("Content-Security-Policy", CSP)
        for c in cookies:
            self.send_header("Set-Cookie", c)
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, code, out, cookies=()):
        self.send(code, json.dumps(out, default=str).encode("utf-8"), "application/json", cookies)

    def send_asset(self, path):
        """A file from web/dist/assets, never anything outside it (no '..' tricks)."""
        f = (DIST / urllib.parse.unquote(path).lstrip("/")).resolve()
        if (DIST / "assets").resolve() not in f.parents or f.suffix not in ASSET_TYPES or not f.is_file():
            return self.send_json(404, {"error": "not found"})
        return self.send(200, f.read_bytes(), ASSET_TYPES[f.suffix])

    def session_token(self):
        """Our cookie, read by hand: Python's cookie parser drops the whole header at the first cookie it cannot parse
        (a JSON value or a space, e.g. from analytics on the same domain), which signed users out."""
        for part in (self.headers.get("Cookie") or "").split(";"):
            name, _, value = part.strip().partition("=")
            if name == SESSION_COOKIE and value:
                return value
        return None

    def addressed_to_us(self):
        """Only requests for this server's own address. Without this, a website that points its own name at
        127.0.0.1 (DNS rebinding) would pass the Origin check: its pages and this server then share a host name."""
        host = (self.headers.get("Host") or "").lower()
        port = self.server.server_address[1]
        return host in {f"127.0.0.1:{port}", f"localhost:{port}", *CONFIG["public_hosts"]}

    def client_ip(self):
        """The visitor's address. Behind the reverse proxy (--behind-proxy) every connection comes from the proxy,
        which puts the visitor's address last in X-Forwarded-For. Without the option the header is ignored, since
        anyone can send it."""
        if CONFIG["behind_proxy"]:
            forwarded = [p.strip() for p in (self.headers.get("X-Forwarded-For") or "").split(",") if p.strip()]
            if forwarded:
                return forwarded[-1]
        return self.client_address[0]

    def same_origin(self):
        """Only our own page may send POSTs. Hosted mode also requires the Origin header, which browsers always
        send on fetch POSTs, so another website cannot act for a signed-in visitor."""
        origin = self.headers.get("Origin")
        if not origin:
            return not CONFIG["hosted"]
        return urllib.parse.urlparse(origin).netloc == self.headers.get("Host")

    def handle_any(self, method):
        if not self.addressed_to_us():
            return self.send_json(421, {"error": "This server does not answer for that address."})
        u = urllib.parse.urlparse(self.path)
        if method == "GET" and u.path in ("/", "/index.html"):
            return self.send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        if method == "GET" and u.path.startswith("/assets/"):
            return self.send_asset(u.path)
        route = ROUTES.get((method, u.path))
        if not route:
            return self.send_json(404, {"error": "not found"})
        fn, access = route

        if method == "POST":
            if not self.same_origin():
                return self.send_json(403, {"error": "forbidden"})
            if CONFIG["hosted"] and not (self.headers.get("Content-Type") or "").startswith("application/json"):
                return self.send_json(415, {"error": "send JSON"})
            length = (self.headers.get("Content-Length") or "0").strip()
            if not length.isdigit():  # negative or junk: reading it would hang or crash
                return self.send_json(400, {"error": "bad Content-Length"})
            n = int(length)
            if n > MAX_BODY:
                return self.send_json(413, {"error": "request too large"})
            try:
                q = json.loads(self.rfile.read(n) or b"{}") if n else {}
            except ValueError:
                return self.send_json(400, {"error": "invalid JSON"})
            if not isinstance(q, dict):
                return self.send_json(400, {"error": "send a JSON object"})
        else:
            q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}

        ctx = Ctx(ip=self.client_ip())
        if CONFIG["hosted"]:
            ctx.token = self.session_token()
            ctx.user = _with_db(lambda conn: auth.session_account(conn, ctx.token))
        else:
            ctx.user = LOCAL_ADMIN
        if not allowed(ctx.user, access):
            return self.send_json(403 if ctx.user else 401, {"error": "Sign in as an admin to do that."})

        try:
            out, code = fn(q, ctx), 200
        except auth.RateLimited as e:
            out, code = {"error": str(e)}, 429
        except FileNotFoundError as e:
            out, code = {"error": str(e)}, 404
        except (ValueError, KeyError) as e:
            out, code = {"error": str(e)}, 400
        except Exception as e:  # noqa: BLE001 - e.g. the database busy during an update
            if CONFIG["hosted"]:  # visitors get no internals (paths, SQL); the admin finds them in the server log
                traceback.print_exc()
                out = {"error": "Something went wrong on the server. Please try again in a moment."}
            else:
                out = {"error": f"{type(e).__name__}: {e}. If an update is running, try again in a moment."}
            code = 500
        self.send_json(code, out, ctx.cookies)

    def do_GET(self):
        self.handle_any("GET")

    def do_POST(self):
        self.handle_any("POST")


class Server(ThreadingHTTPServer):
    """The HTTP server. A client that hangs up or stalls (a reloaded page, a dropped connection) is normal, not an
    error to print; it can happen while reading the request or writing the answer."""

    def handle_error(self, request, client_address):
        if isinstance(sys.exc_info()[1], ConnectionError | TimeoutError):  # broken pipe, reset, aborted
            return
        super().handle_error(request, client_address)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true")
    p.add_argument(
        "--hosted",
        action="store_true",
        default=os.environ.get("PICKHELPER_HOSTED") == "1",
        help="accounts and sign-in (for running on a server); also PICKHELPER_HOSTED=1",
    )
    p.add_argument("--host", default="127.0.0.1", help="address to listen on (hosted mode behind a proxy)")
    p.add_argument(
        "--public-host",
        action="append",
        default=[h for h in os.environ.get("PICKHELPER_PUBLIC_HOSTS", "").split(",") if h.strip()],
        help="name the site is reached by, e.g. picks.example.com (repeatable; also PICKHELPER_PUBLIC_HOSTS)",
    )
    p.add_argument(
        "--behind-proxy",
        action="store_true",
        default=os.environ.get("PICKHELPER_BEHIND_PROXY") == "1",
        help="hosted behind a reverse proxy that sets X-Forwarded-For (Caddy in docker-compose.yml); "
        "the app port must then only be reachable through the proxy",
    )
    p.add_argument(
        "--insecure-cookies",
        action="store_true",
        help="hosted mode without HTTPS, for testing only: session cookies without the Secure flag",
    )
    a = p.parse_args()
    CONFIG.update(
        hosted=a.hosted,
        secure_cookies=not a.insecure_cookies,
        public_hosts={h.strip().lower() for h in a.public_host},
        behind_proxy=a.behind_proxy,
    )
    srv = None
    ports = [a.port] if a.hosted else range(a.port, a.port + 20)  # a server keeps its port or fails loudly
    for port in ports:
        try:
            srv = Server((a.host, port), Handler)
            break
        except OSError:
            continue
    if not srv:
        sys.exit(f"no free port at {a.port}" + ("" if a.hosted else f" to {a.port + 19}"))
    url = f"http://{a.host}:{srv.server_address[1]}/"
    mode = "hosted mode (accounts on)" if a.hosted else "close this window or press Ctrl+C to stop"
    print(f"Pick helper running at {url}  ({mode})", flush=True)
    if not a.no_browser and not a.hosted:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    with contextlib.suppress(KeyboardInterrupt):
        srv.serve_forever()


if __name__ == "__main__":
    main()
