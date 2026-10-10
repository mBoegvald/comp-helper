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
    srv = webapp.ThreadingHTTPServer(("127.0.0.1", 0), webapp.Handler)
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
    for method, path in [("GET", "/api/status"), ("GET", "/api/hand/champion?role=top&name=Aatrox")]:
        assert request(hosted, method, path)[0] == 401
    body = {"role": "top", "champion": "Garen", "opponent": "Darius", "tip": "x"}
    assert request(hosted, "POST", "/api/hand/matchup", body)[0] == 401
    assert request(hosted, "POST", "/api/update", {"stage": "tips"})[0] == 401


def test_contributors_cannot_do_admin_things(hosted):
    token = sign_in(hosted, "pleb", "contributor pw")
    body = {"role": "top", "champion": "Garen", "opponent": "Darius", "tip": "x"}
    assert request(hosted, "POST", "/api/hand/matchup", body, cookie=token)[0] == 403
    assert request(hosted, "GET", "/api/admin/accounts", cookie=token)[0] == 403
    assert request(hosted, "POST", "/api/stop", {}, cookie=token)[0] == 403


def test_admin_can_edit_and_manage_accounts(hosted, conn):
    token = sign_in(hosted, "boss", "admin password")
    body = {"role": "top", "champion": "Garen", "opponent": "Darius", "tip": "admin tip"}
    assert request(hosted, "POST", "/api/hand/matchup", body, cookie=token)[0] == 200
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
    assert request(hosted, "POST", "/api/hand/matchup", body, cookie=token, **kwargs)[0] == status


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
