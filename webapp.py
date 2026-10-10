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
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.chdir(HERE)
sys.path.insert(0, str(HERE))

import db
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
_tips_cache = {"stamp": None, "data": {}}
_names_cache = {"stamp": None, "names": {}}


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
    d["hand_result"] = (fwd or {}).get("result") if fwd and fwd.get("result") != fwd.get("label") else None
    d["mismatch"] = bool((fwd or {}).get("mismatch"))
    d["tips"] = []
    if fwd and fwd.get("hand_tip"):
        d["tips"].append({"from": "notes", "who": display(a), "text": fwd["hand_tip"]})
    if rev and rev.get("hand_tip"):
        d["tips"].append({"from": "notes", "who": display(b), "text": rev["hand_tip"]})
    rt = reddit_tips()
    d["reddit"] = []
    for x, y in ((a, b), (b, a)):
        r = rt.get((x, y))
        if r:
            d["reddit"].append({"who": display(x), "mentions": r["mentions"], "newest": r["newest"], "tips": r["tips"]})
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


def api_meta(_q):
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


def api_recommend(q):
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


def api_champion(q):
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
    }


def api_matchup(q):
    role = role_of(q.get("role"))
    champs = load(role)[0]
    return matchup(role, find(q.get("a", ""), champs), find(q.get("b", ""), champs))


def api_status(_q):
    lines = []
    if update.LOG.exists():
        with update.LOG.open(encoding="utf-8", errors="replace") as f:
            lines = f.readlines()[-80:]
    return {"running": update.is_running(), "log": "".join(lines)}


def api_update(q):
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


def api_stop(_q):
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


# ---------------------------------------------------------------- hand edits

HAND_RESULTS = ("Favored", "Even", "Even / skill", "Unfavored")


def pool_name(role, name):
    """Exact champion name as stored for this role, for typed or key-shaped input."""
    champs = load(role)[0]
    k = find(str(name or ""), champs)
    if k not in champs:
        raise ValueError(f"{name!r} is not a {role} champion")
    return champs[k]["name"]


def api_hand_champion_get(q):
    """What a champion's edit form needs: the hand edits, the role_data defaults they override, the archetypes."""
    role = role_of(q.get("role"))
    name = pool_name(role, q.get("name"))
    conn = db.connect()
    try:
        r = conn.execute("SELECT * FROM hand_champion WHERE role = ? AND champion = ?", (role, name)).fetchone()
    finally:
        conn.close()
    arch, dmg, comps, when, blind = db.defaults(role, name)
    archs = role_data.ARCHETYPES.get(role, {})
    _w, g_def, b_def = archs.get((r and r["archetype"]) or arch, ([], "", ""))
    return {
        "role": role,
        "champion": name,
        "hand": {k: (r[k] if r else None) for k in db.HAND_CHAMP_FIELDS},
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


def api_hand_champion_set(q):
    role = role_of(q.get("role"))
    name = pool_name(role, q.get("champion"))
    fields = q.get("fields") or {}
    if not isinstance(fields, dict):
        raise ValueError("fields must be an object")
    conn = db.connect()
    try:
        db.set_hand_champion(conn, role, name, fields)
    finally:
        conn.close()
    return api_hand_champion_get({"role": role, "name": name})


def api_hand_matchup_set(q):
    """Hand label and/or lane tip for champion vs opponent in a role; empty values remove them."""
    role = role_of(q.get("role"))
    champ = pool_name(role, q.get("champion"))
    opp = display(find(str(q.get("opponent") or ""), load(role)[0]))
    if picker.key(opp) not in all_names():
        raise ValueError(f"unknown opponent {q.get('opponent')!r}")
    result = (q.get("result") or "").strip() or None
    if result and result not in HAND_RESULTS:
        raise ValueError(f"result must be one of {', '.join(HAND_RESULTS)} or empty")
    conn = db.connect()
    try:
        db.set_hand_matchup(conn, role, champ, opp, result, q.get("tip"))
    finally:
        conn.close()
    return matchup(role, picker.key(champ), picker.key(opp))


ROUTES = {
    ("GET", "/api/meta"): api_meta,
    ("POST", "/api/recommend"): api_recommend,
    ("GET", "/api/champion"): api_champion,
    ("GET", "/api/matchup"): api_matchup,
    ("GET", "/api/status"): api_status,
    ("POST", "/api/update"): api_update,
    ("POST", "/api/stop"): api_stop,
    ("GET", "/api/hand/champion"): api_hand_champion_get,
    ("POST", "/api/hand/champion"): api_hand_champion_set,
    ("POST", "/api/hand/matchup"): api_hand_matchup_set,
}


class Handler(BaseHTTPRequestHandler):
    server_version = "PickHelper/1"

    def log_message(self, fmt, *args):  # quiet console
        pass

    def send(self, code, body: bytes, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_asset(self, path):
        """A file from web/dist/assets, never anything outside it (no '..' tricks)."""
        f = (DIST / urllib.parse.unquote(path).lstrip("/")).resolve()
        if (DIST / "assets").resolve() not in f.parents or f.suffix not in ASSET_TYPES or not f.is_file():
            return self.send(404, b'{"error":"not found"}', "application/json")
        return self.send(200, f.read_bytes(), ASSET_TYPES[f.suffix])

    def handle_any(self, method):
        u = urllib.parse.urlparse(self.path)
        if method == "GET" and u.path in ("/", "/index.html"):
            return self.send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        if method == "GET" and u.path.startswith("/assets/"):
            return self.send_asset(u.path)
        fn = ROUTES.get((method, u.path))
        if not fn:
            return self.send(404, b'{"error":"not found"}', "application/json")
        if method == "POST":
            # only accept requests from our own page (blocks other websites from poking the local server)
            origin = self.headers.get("Origin")
            if origin and urllib.parse.urlparse(origin).netloc != self.headers.get("Host"):
                return self.send(403, b'{"error":"forbidden"}', "application/json")
            n = int(self.headers.get("Content-Length") or 0)
            q = json.loads(self.rfile.read(n) or b"{}") if n else {}
        else:
            q = {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}
        try:
            out = fn(q)
            code = 200
        except FileNotFoundError as e:
            out, code = {"error": str(e)}, 404
        except (ValueError, KeyError) as e:
            out, code = {"error": str(e)}, 400
        except Exception as e:  # noqa: BLE001 - e.g. a workbook half-written by a running update
            out, code = {"error": f"{type(e).__name__}: {e}. If an update is running, try again in a moment."}, 500
        self.send(code, json.dumps(out, default=str).encode("utf-8"), "application/json")

    def do_GET(self):
        self.handle_any("GET")

    def do_POST(self):
        self.handle_any("POST")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--no-browser", action="store_true")
    a = p.parse_args()
    srv = None
    for port in range(a.port, a.port + 20):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            continue
    if not srv:
        sys.exit(f"no free port between {a.port} and {a.port + 19}")
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    print(f"Pick helper running at {url}  (close this window or press Ctrl+C to stop)", flush=True)
    if not a.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    with contextlib.suppress(KeyboardInterrupt):
        srv.serve_forever()


if __name__ == "__main__":
    main()
