"""Hosted mode over real HTTP: who may do what, cookies, and requests from other sites."""

import http.client
import json
import threading

import pytest

import auth
import webapp


@pytest.fixture
def hosted(conn, monkeypatch):
    """A hosted-mode server with an admin and a contributor. Returns its address."""
    monkeypatch.setattr(auth, "SCRYPT_N", 2**8)
    monkeypatch.setattr(auth, "SCRYPT_P", 1)
    monkeypatch.setattr(auth, "_DUMMY_HASH", None)
    monkeypatch.setitem(webapp.CONFIG, "hosted", True)
    auth.create_account(conn, "boss", "admin password", role="admin")
    auth.create_account(conn, "pleb", "contributor pw")
    srv = webapp.Server(("127.0.0.1", 0), webapp.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def request(host, method, path, body=None, cookie=None, origin="same", ctype="application/json"):
    """(status, json, set-cookie header). origin='same' sends our own Origin, None sends none."""
    c = http.client.HTTPConnection(host, timeout=10)
    headers = {}
    if body is not None:
        headers["Content-Type"] = ctype
    if origin:
        headers["Origin"] = f"http://{host}" if origin == "same" else origin
    if cookie:
        headers["Cookie"] = f"{webapp.SESSION_COOKIE}={cookie}"
    data = json.dumps(body).encode() if isinstance(body, dict) else body
    c.request(method, path, body=data, headers=headers)
    r = c.getresponse()
    raw = r.read()
    c.close()
    return r.status, json.loads(raw) if raw else None, r.getheader("Set-Cookie")


def token_from(set_cookie):
    return set_cookie.split(";")[0].split("=", 1)[1]


def sign_in(host, username, password):
    status, d, cookie = request(host, "POST", "/api/login", {"username": username, "password": password})
    assert status == 200, d
    return token_from(cookie)


def test_signed_out_visitors_can_read_but_not_edit(hosted):
    assert request(hosted, "GET", "/api/me")[1] == {"hosted": True, "user": None, "admin": False}
    assert request(hosted, "POST", "/api/recommend", {"role": "top"})[0] == 200
    assert request(hosted, "GET", "/api/matchup?role=top&a=Aatrox&b=Darius")[0] == 200
    for method, path in [("GET", "/api/status"), ("GET", "/api/curated/champion?role=top&name=Aatrox")]:
        assert request(hosted, method, path)[0] == 401
    body = {"role": "top", "champion": "Garen", "opponent": "Darius", "tip": "x"}
    assert request(hosted, "POST", "/api/curated/matchup", body)[0] == 401
    assert request(hosted, "POST", "/api/update", {"stage": "tips"})[0] == 401


def test_contributors_cannot_do_admin_things(hosted):
    token = sign_in(hosted, "pleb", "contributor pw")
    body = {"role": "top", "champion": "Garen", "opponent": "Darius", "tip": "x"}
    assert request(hosted, "POST", "/api/curated/matchup", body, cookie=token)[0] == 403
    assert request(hosted, "GET", "/api/admin/accounts", cookie=token)[0] == 403
    assert request(hosted, "POST", "/api/stop", {}, cookie=token)[0] == 403


def test_admin_can_edit_and_manage_accounts(hosted, conn):
    token = sign_in(hosted, "boss", "admin password")
    body = {"role": "top", "champion": "Garen", "opponent": "Darius", "tip": "admin tip"}
    assert request(hosted, "POST", "/api/curated/matchup", body, cookie=token)[0] == 200
    status, d, _ = request(hosted, "GET", "/api/admin/accounts", cookie=token)
    assert status == 200 and [a["username"] for a in d["accounts"]] == ["boss", "pleb"]


def test_session_cookie_flags(hosted):
    _, _, cookie = request(hosted, "POST", "/api/login", {"username": "pleb", "password": "contributor pw"})
    flags = [f.strip() for f in cookie.split(";")]
    assert {"HttpOnly", "SameSite=Lax", "Path=/", "Secure"} <= set(flags)


def test_signup_signin_signout(hosted):
    status, d, cookie = request(hosted, "POST", "/api/signup", {"username": "newbie", "password": "a good password"})
    assert status == 200 and d["user"]["username"] == "newbie" and d["user"]["role"] == "contributor"
    token = token_from(cookie)
    assert request(hosted, "GET", "/api/me", cookie=token)[1]["user"]["username"] == "newbie"
    _, d, cookie = request(hosted, "POST", "/api/logout", {}, cookie=token)
    assert d["user"] is None and "Max-Age=0" in cookie
    assert request(hosted, "GET", "/api/me", cookie=token)[1]["user"] is None  # the old token is dead


def test_wrong_password_is_refused(hosted):
    status, d, cookie = request(hosted, "POST", "/api/login", {"username": "boss", "password": "not it at all"})
    assert status == 400 and cookie is None and "Wrong" in d["error"]


def test_signup_is_rate_limited(hosted, monkeypatch):
    monkeypatch.setitem(auth.LIMITS, "signup", (2, 3600))
    for i in range(2):
        assert request(hosted, "POST", "/api/signup", {"username": f"bot{i}", "password": "a good password"})[0] == 200
    assert request(hosted, "POST", "/api/signup", {"username": "bot9", "password": "a good password"})[0] == 429


def test_blocked_contributor_is_signed_out(hosted, conn):
    token = sign_in(hosted, "pleb", "contributor pw")
    admin = sign_in(hosted, "boss", "admin password")
    pleb_id = conn.execute("SELECT id FROM account WHERE username = 'pleb'").fetchone()[0]
    assert request(hosted, "POST", "/api/admin/block", {"id": pleb_id, "blocked": True}, cookie=admin)[0] == 200
    assert request(hosted, "GET", "/api/me", cookie=token)[1]["user"] is None


def test_admin_cannot_block_themselves(hosted, conn):
    admin = sign_in(hosted, "boss", "admin password")
    boss_id = conn.execute("SELECT id FROM account WHERE username = 'boss'").fetchone()[0]
    assert request(hosted, "POST", "/api/admin/block", {"id": boss_id, "blocked": True}, cookie=admin)[0] == 400


@pytest.mark.parametrize(
    "kwargs, status",
    [
        ({"origin": "http://evil.example"}, 403),  # another website
        ({"origin": None}, 403),  # no Origin at all: refused in hosted mode
        ({"ctype": "text/plain"}, 415),  # what a plain cross-site form could send
    ],
)
def test_posts_must_come_from_the_page(hosted, kwargs, status):
    token = sign_in(hosted, "boss", "admin password")
    body = {"role": "top", "champion": "Garen", "opponent": "Darius", "tip": "x"}
    assert request(hosted, "POST", "/api/curated/matchup", body, cookie=token, **kwargs)[0] == status


def test_oversized_and_malformed_bodies(hosted):
    assert request(hosted, "POST", "/api/login", b"x" * (webapp.MAX_BODY + 1))[0] == 413
    assert request(hosted, "POST", "/api/login", b"{not json")[0] == 400
    assert request(hosted, "POST", "/api/login", b"[1, 2]")[0] == 400


def test_security_headers(hosted):
    c = http.client.HTTPConnection(hosted, timeout=10)
    c.request("GET", "/")
    r = c.getresponse()
    r.read()
    assert r.getheader("X-Frame-Options") == "DENY"
    assert r.getheader("X-Content-Type-Options") == "nosniff"


def test_local_mode_has_no_accounts(conn):
    assert webapp.api_me({}, None) == {
        "hosted": False,
        "user": webapp.LOCAL_ADMIN,
        "admin": True,
    }
    with pytest.raises(ValueError, match="hosted site"):
        webapp.api_login({"username": "x", "password": "y"}, webapp.Ctx("127.0.0.1"))


# ---------------------------------------------------------------- community notes

NOTE = {
    "role": "top",
    "champion": "Darius",
    "opponent": "Garen",
    "text": "Trade when his Q is dwn.",
    "source": "my games",
}


def test_signed_out_visitors_cannot_suggest(hosted):
    assert request(hosted, "POST", "/api/notes", NOTE)[0] == 401


def test_a_suggestion_is_hidden_until_approved(hosted):
    pleb = sign_in(hosted, "pleb", "contributor pw")
    status, d, _ = request(hosted, "POST", "/api/notes", NOTE, cookie=pleb)
    assert status == 200 and d["note"]["status"] == "pending"
    assert request(hosted, "GET", "/api/matchup?role=top&a=Darius&b=Garen")[1]["community"] == []
    mine = request(hosted, "GET", "/api/notes/mine", cookie=pleb)[1]["notes"]
    assert [(n["text"], n["status"]) for n in mine] == [("Trade when his Q is dwn.", "pending")]

    boss = sign_in(hosted, "boss", "admin password")
    queue = request(hosted, "GET", "/api/admin/review", cookie=boss)[1]["notes"]
    assert [(n["author"], n["champion"], n["opponent"]) for n in queue] == [("pleb", "Darius", "Garen")]
    fixed = {"id": queue[0]["id"], "approve": True, "text": "Trade when his Q is down."}
    assert request(hosted, "POST", "/api/admin/review", fixed, cookie=boss)[1]["notes"] == []

    m = request(hosted, "GET", "/api/matchup?role=top&a=Darius&b=Garen")[1]  # signed out: visible to everyone
    assert [(n["who"], n["author"], n["text"], n["source"]) for n in m["community"]] == [
        ("Darius", "pleb", "Trade when his Q is down.", "my games")
    ]
    flipped = request(hosted, "GET", "/api/matchup?role=top&a=Garen&b=Darius")[1]["community"]
    assert [n["who"] for n in flipped] == ["Darius"]  # still marked as Darius's side


def test_champion_notes_show_on_the_champion(hosted):
    boss = sign_in(hosted, "boss", "admin password")
    body = {"role": "top", "champion": "darius", "text": "Hold W for the slow after Q."}
    status, d, _ = request(hosted, "POST", "/api/notes", body, cookie=boss)
    assert status == 200 and d["note"]["status"] == "approved"  # admins skip the queue
    lookup = request(hosted, "GET", "/api/champion?role=top&name=Darius")[1]
    assert [n["text"] for n in lookup["community"]] == ["Hold W for the slow after Q."]


def test_rejected_notes_tell_their_author_why(hosted):
    pleb = sign_in(hosted, "pleb", "contributor pw")
    note_id = request(hosted, "POST", "/api/notes", NOTE, cookie=pleb)[1]["note"]["id"]
    boss = sign_in(hosted, "boss", "admin password")
    request(hosted, "POST", "/api/admin/review", {"id": note_id, "approve": False, "note": "Too vague."}, cookie=boss)
    mine = request(hosted, "GET", "/api/notes/mine", cookie=pleb)[1]["notes"]
    assert (mine[0]["status"], mine[0]["review_note"]) == ("rejected", "Too vague.")


def test_contributors_cannot_review(hosted):
    pleb = sign_in(hosted, "pleb", "contributor pw")
    note_id = request(hosted, "POST", "/api/notes", NOTE, cookie=pleb)[1]["note"]["id"]
    assert request(hosted, "GET", "/api/admin/review", cookie=pleb)[0] == 403
    assert request(hosted, "POST", "/api/admin/review", {"id": note_id, "approve": True}, cookie=pleb)[0] == 403
    assert request(hosted, "POST", "/api/admin/notes/delete", {"id": note_id}, cookie=pleb)[0] == 403


@pytest.mark.parametrize(
    "change, message",
    [
        ({"champion": "Nobody"}, "not a top champion"),
        ({"opponent": "Notachamp"}, "unknown opponent"),
        ({"text": "hi"}, "10 to"),
    ],
)
def test_bad_suggestions_are_refused(hosted, change, message):
    pleb = sign_in(hosted, "pleb", "contributor pw")
    status, d, _ = request(hosted, "POST", "/api/notes", {**NOTE, **change}, cookie=pleb)
    assert status == 400 and message in d["error"]


def test_blocking_empties_the_account_from_the_queue(hosted, conn):
    pleb = sign_in(hosted, "pleb", "contributor pw")
    request(hosted, "POST", "/api/notes", NOTE, cookie=pleb)
    boss = sign_in(hosted, "boss", "admin password")
    pleb_id = conn.execute("SELECT id FROM account WHERE username = 'pleb'").fetchone()[0]
    request(hosted, "POST", "/api/admin/block", {"id": pleb_id, "blocked": True}, cookie=boss)
    assert request(hosted, "GET", "/api/admin/review", cookie=boss)[1]["notes"] == []


def test_admin_can_delete_an_approved_note(hosted):
    boss = sign_in(hosted, "boss", "admin password")
    note_id = request(hosted, "POST", "/api/notes", NOTE, cookie=boss)[1]["note"]["id"]
    assert request(hosted, "POST", "/api/admin/notes/delete", {"id": note_id}, cookie=boss)[0] == 200
    assert request(hosted, "GET", "/api/matchup?role=top&a=Darius&b=Garen")[1]["community"] == []


def test_local_mode_does_not_take_suggestions(conn):
    with pytest.raises(ValueError, match="hosted site"):
        webapp.api_notes_suggest(NOTE, webapp.Ctx("127.0.0.1", user=webapp.LOCAL_ADMIN))
    assert webapp.api_matchup({"role": "top", "a": "Darius", "b": "Garen"})["community"] == []


def test_admin_turns_a_note_into_the_lane_tip(hosted):
    pleb = sign_in(hosted, "pleb", "contributor pw")
    note_id = request(hosted, "POST", "/api/notes", NOTE, cookie=pleb)[1]["note"]["id"]
    assert request(hosted, "POST", "/api/admin/notes/promote", {"id": note_id}, cookie=pleb)[0] == 403
    boss = sign_in(hosted, "boss", "admin password")
    request(hosted, "POST", "/api/admin/review", {"id": note_id, "approve": True}, cookie=boss)
    assert request(hosted, "POST", "/api/admin/notes/promote", {"id": note_id}, cookie=boss)[:2] == (200, {"ok": True})
    m = request(hosted, "GET", "/api/matchup?role=top&a=Darius&b=Garen")[1]
    assert m["community"] == []
    assert [(t["who"], t["text"]) for t in m["tips"]] == [("Darius", "Trade when his Q is dwn. (from pleb)")]
    assert request(hosted, "POST", "/api/admin/notes/promote", {"id": note_id}, cookie=boss)[0] == 400  # gone


def test_server_errors_show_no_internals_when_hosted(hosted, monkeypatch, capsys):
    def broken(_q, _ctx=None):
        raise RuntimeError("secret detail: /srv/pickhelper/data/pickhelper.db")

    monkeypatch.setitem(webapp.ROUTES, ("GET", "/api/meta"), (broken, webapp.PUBLIC))
    status, d, _ = request(hosted, "GET", "/api/meta")
    assert status == 500 and "secret detail" not in d["error"]
    assert "secret detail" in capsys.readouterr().err  # but it is in the server log


@pytest.mark.parametrize("others", ['theme={"x":1}', "x=a b", "_ga=GA1.2.3, consent=yes"])
def test_other_cookies_do_not_sign_you_out(hosted, others):
    """Cookies set by other apps on the same domain can have values Python's cookie parser rejects."""
    token = sign_in(hosted, "pleb", "contributor pw")
    c = http.client.HTTPConnection(hosted, timeout=10)
    c.request("GET", "/api/me", headers={"Cookie": f"{others}; {webapp.SESSION_COOKIE}={token}; last=1"})
    me = json.loads(c.getresponse().read())
    c.close()
    assert me["user"]["username"] == "pleb"


def test_notes_show_for_champions_with_an_apostrophe(hosted):
    """Cho'Gath, Kai'Sa, Kha'Zix...: the notes index and the page's lookups must spell the key the same way."""
    boss = sign_in(hosted, "boss", "admin password")
    for body in (
        {"role": "top", "champion": "Cho'Gath", "text": "Stack R on minions and monsters."},
        {"role": "top", "champion": "Aatrox", "opponent": "Cho'Gath", "text": "Dodge his Q with your E."},
    ):
        assert request(hosted, "POST", "/api/notes", body, cookie=boss)[0] == 200
    lookup = request(hosted, "GET", "/api/champion?role=top&name=Cho%27Gath")[1]
    assert [n["text"] for n in lookup["community"]] == ["Stack R on minions and monsters."]
    m = request(hosted, "GET", "/api/matchup?role=top&a=Aatrox&b=Cho%27Gath")[1]
    assert [n["text"] for n in m["community"]] == ["Dodge his Q with your E."]


SQL_ATTACKS = [
    "'); DROP TABLE account; --",
    "x' OR '1'='1",
    "Robert'); UPDATE account SET role='admin' WHERE username='pleb'; --",
    '" UNION SELECT pw_hash FROM account --',
]


def test_sql_in_notes_and_lookups_is_only_text(hosted, conn):
    """SQL injection: whatever a contributor types is stored as typed and never runs."""
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    pleb = sign_in(hosted, "pleb", "contributor pw")
    for attack in SQL_ATTACKS:
        body = {"role": "top", "champion": "Darius", "opponent": "Garen", "text": f"note {attack}", "source": attack}
        assert request(hosted, "POST", "/api/notes", body, cookie=pleb)[0] == 200
    assert request(hosted, "GET", "/api/champion?role=top&name=Darius'%20OR%20'1'='1")[0] == 200
    assert request(hosted, "GET", "/api/matchup?role=top&a=Darius&b=x'%3B%20DROP%20TABLE%20lola%3B--")[0] == 200
    assert request(hosted, "POST", "/api/login", {"username": "boss' --", "password": "anything at all"})[0] == 400

    assert {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")} == tables
    assert conn.execute("SELECT count(*) FROM lola").fetchone()[0] == 5
    assert [tuple(r) for r in conn.execute("SELECT username, role FROM account ORDER BY username")] == [
        ("boss", "admin"),
        ("pleb", "contributor"),
    ]
    assert [r[0] for r in conn.execute("SELECT source FROM community_note ORDER BY id")] == SQL_ATTACKS


def signup_from(hosted, name, forwarded=None):
    c = http.client.HTTPConnection(hosted, timeout=10)
    headers = {"Content-Type": "application/json", "Origin": f"http://{hosted}"}
    if forwarded:
        headers["X-Forwarded-For"] = forwarded
    c.request(
        "POST", "/api/signup", body=json.dumps({"username": name, "password": "a good password"}), headers=headers
    )
    status = c.getresponse().status
    c.close()
    return status


def test_behind_the_proxy_each_visitor_has_their_own_limit(hosted, monkeypatch):
    """Caddy puts the visitor's address last in X-Forwarded-For; a visitor's own value in front is ignored."""
    monkeypatch.setitem(webapp.CONFIG, "behind_proxy", True)
    monkeypatch.setitem(auth.LIMITS, "signup", (1, 3600))
    assert signup_from(hosted, "visitor1", "203.0.113.5") == 200
    assert signup_from(hosted, "visitor1b", "203.0.113.5") == 429  # same visitor again
    assert signup_from(hosted, "visitor2", "198.51.100.7") == 200  # someone else
    assert signup_from(hosted, "visitor1c", "198.51.100.99, 203.0.113.5") == 429  # faked first entry: still visitor 1


def test_without_the_proxy_option_the_header_is_ignored(hosted, monkeypatch):
    """Anyone can send X-Forwarded-For; trusting it without a proxy would let them dodge the limits."""
    monkeypatch.setitem(auth.LIMITS, "signup", (1, 3600))
    assert signup_from(hosted, "dodger1", "203.0.113.1") == 200
    assert signup_from(hosted, "dodger2", "203.0.113.2") == 429
