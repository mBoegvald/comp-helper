"""The web page's API: functions directly, plus a real server for routing and the same-origin check."""

import http.client
import json
import threading
import urllib.error
import urllib.request

import pytest

import webapp


def test_recommend_ranks_and_excludes_taken(conn):
    d = webapp.api_recommend({"role": "top", "enemy": {"top": "Darius"}, "unavailable": ["Garen"]})
    names = [p["name"] for p in d["picks"]]
    assert d["enemy_main"] == "Darius"
    assert "Darius" not in names and "Garen" not in names
    assert "Aatrox" in [p["name"] for p in d["avoid"]]  # Unfavored into Darius


def test_matchup_from_either_side(conn):
    a = webapp.api_matchup({"role": "top", "a": "Aatrox", "b": "Darius"})
    b = webapp.api_matchup({"role": "top", "a": "Darius", "b": "Aatrox"})
    assert (a["label"], b["label"]) == ("Unfavored", "Favored")
    assert a["dnorm"] == -b["dnorm"]


def test_curated_champion_round_trip(conn):
    d = webapp.api_curated_champion_set({"role": "top", "champion": "aatrox", "fields": {"pick_when": "Mine"}})
    assert d["champion"] == "Aatrox"
    assert d["curated"]["pick_when"] == "Mine"
    assert d["defaults"]["pick_when"] == "You need a frontline with damage and sustain"
    d = webapp.api_curated_champion_set({"role": "top", "champion": "Aatrox", "fields": {"pick_when": None}})
    assert d["curated"]["pick_when"] is None


def test_curated_matchup_round_trip(conn):
    m = webapp.api_curated_matchup_set({"role": "top", "champion": "Garen", "opponent": "darius", "result": "Favored"})
    assert (m["curated_result"], m["mismatch"]) == ("Favored", True)


@pytest.mark.parametrize(
    "fn, q",
    [
        (webapp.api_curated_champion_set, {"role": "top", "champion": "Nobody", "fields": {}}),
        (webapp.api_curated_champion_set, {"role": "top", "champion": "Aatrox", "fields": {"hack": 1}}),
        (webapp.api_curated_matchup_set, {"role": "top", "champion": "Aatrox", "opponent": "Darius", "result": "<b>"}),
        (webapp.api_recommend, {"role": "nope"}),
    ],
)
def test_bad_input_is_rejected(conn, fn, q):
    with pytest.raises(ValueError):
        fn(q)


@pytest.fixture
def server(conn):
    srv = webapp.Server(("127.0.0.1", 0), webapp.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def call(url, body=None, origin=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None)
    if origin:
        req.add_header("Origin", origin)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read()) if "json" in r.headers["Content-Type"] else None
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_server_routes(server):
    assert call(server + "/")[0] == 200
    assert call(server + "/api/meta")[1]["patch"] == "16.20 EMERALD+"
    assert call(server + "/api/nope")[0] == 404
    assert call(server + "/api/matchup?role=nope&a=x&b=y")[0] == 400


def test_edits_only_from_the_page_itself(server, conn):
    body = {"role": "top", "champion": "Garen", "opponent": "Darius", "tip": "t"}
    assert call(server + "/api/curated/matchup", body, origin="http://evil.example")[0] == 403
    assert conn.execute("SELECT count(*) FROM curated_matchup").fetchone()[0] == 0
    status, d = call(server + "/api/curated/matchup", body, origin=server)
    assert status == 200 and d["tips"][0]["text"] == "t"


def raw_get(base, path):
    """GET without any client-side path cleanup, so '..' reaches the server as typed."""
    host, port = base.removeprefix("http://").split(":")
    c = http.client.HTTPConnection(host, int(port), timeout=10)
    c.request("GET", path)
    r = c.getresponse()
    body = r.read()
    c.close()
    return r.status, r.getheader("Content-Type"), body


def test_serves_the_built_page_and_its_assets(server):
    status, ctype, body = raw_get(server, "/")
    assert status == 200 and ctype.startswith("text/html")
    asset = next(p for p in (webapp.DIST / "assets").iterdir() if p.suffix == ".js")
    assert f"assets/{asset.name}".encode() in body  # the page links the asset it was built with
    status, ctype, _ = raw_get(server, f"/assets/{asset.name}")
    assert status == 200 and ctype.startswith("text/javascript")


@pytest.mark.parametrize(
    "path",
    [
        "/assets/../index.html",
        "/assets/../../webapp.py",
        "/assets/%2e%2e/%2e%2e/data/pickhelper.db",
        "/assets/..%2f..%2fwebapp.py",
        "/assets/missing.js",
    ],
)
def test_assets_never_leave_the_build_folder(server, path):
    assert raw_get(server, path)[0] == 404


def test_champion_outside_the_pool_has_the_full_shape(conn):
    """The page's types expect every field, so a champion outside the role's pool gets them empty."""
    d = webapp.api_champion({"role": "top", "name": "Ahri"})
    assert d["in_role"] is False
    assert set(d["champion"]) == {"name", "arch", "dmg", "comps", "good", "bad", "when", "blind"}


def test_unfinished_names_are_reported_but_not_scored(conn):
    """While typing, "ga" is no champion yet: it must not become the lane opponent or match notes as text."""
    d = webapp.api_recommend({"role": "top", "enemy": {"top": "ga"}})
    assert d["enemy_main"] is None
    assert d["slots"]["enemy.top"]["known"] is False  # the page still marks the box
    assert not any(p.get("enemy") == "ga" for pick in d["picks"] for p in pick["parts"])
    assert webapp.api_recommend({"role": "top", "enemy": {"top": "gar"}})["enemy_main"] == "Garen"  # unique start


def test_a_client_that_hangs_up_is_not_an_error(capsys):
    """A reloaded page or dropped connection, while reading or writing: nothing printed. Real errors still are."""
    srv = webapp.Server(("127.0.0.1", 0), webapp.Handler)
    try:
        for hangup in (BrokenPipeError(), ConnectionResetError(), ConnectionAbortedError(), TimeoutError()):
            try:
                raise hangup
            except OSError:
                srv.handle_error(None, ("127.0.0.1", 0))
        assert capsys.readouterr().err == ""
        try:
            raise ValueError("a real bug")
        except ValueError:
            srv.handle_error(None, ("127.0.0.1", 0))
        assert "a real bug" in capsys.readouterr().err
    finally:
        srv.server_close()


def request_as(base, host, method="GET", path="/api/meta", body=None, origin=None):
    """A request with a chosen Host header, as a DNS-rebinding page would send it."""
    _, port = base.removeprefix("http://").split(":")
    c = http.client.HTTPConnection("127.0.0.1", int(port), timeout=10)
    headers = {"Host": host, "Content-Type": "application/json"}
    if origin:
        headers["Origin"] = origin
    c.request(method, path, body=json.dumps(body) if body is not None else None, headers=headers)
    status = c.getresponse().status
    c.close()
    return status


def test_requests_for_another_host_name_are_refused(server, conn):
    """DNS rebinding: evil.example resolves to 127.0.0.1, so Host and Origin match each other but are not ours."""
    port = server.rsplit(":", 1)[1]
    body = {"role": "top", "champion": "Garen", "opponent": "Darius", "tip": "planted"}
    evil = f"evil.example:{port}"
    assert request_as(server, evil, "POST", "/api/curated/matchup", body, origin=f"http://{evil}") == 421
    assert request_as(server, evil) == 421  # reading too
    assert conn.execute("SELECT count(*) FROM curated_matchup").fetchone()[0] == 0
    assert request_as(server, f"localhost:{port}") == 200


def test_a_configured_public_name_is_answered(server, monkeypatch):
    monkeypatch.setitem(webapp.CONFIG, "public_hosts", {"picks.example.com"})
    assert request_as(server, "picks.example.com") == 200
    assert request_as(server, "other.example.com") == 421


def raw_post(base, length, body=b""):
    """A POST with a hand-written Content-Length, as a broken or hostile client would send it."""
    _, port = base.removeprefix("http://").split(":")
    c = http.client.HTTPConnection("127.0.0.1", int(port), timeout=10)
    c.putrequest("POST", "/api/recommend")
    c.putheader("Content-Type", "application/json")
    c.putheader("Content-Length", length)
    c.endheaders(body)
    status = c.getresponse().status
    c.close()
    return status


@pytest.mark.parametrize("length", ["-1", "abc", "1e3", "+5"])
def test_a_bad_content_length_is_refused_at_once(server, length):
    assert raw_post(server, length) == 400


def test_a_stalled_request_is_dropped(server, monkeypatch):
    """A body that is announced but never sent must not hold a server thread forever."""
    import socket

    monkeypatch.setattr(webapp.Handler, "timeout", 1)
    _, port = server.removeprefix("http://").split(":")
    s = socket.create_connection(("127.0.0.1", int(port)), timeout=10)
    s.sendall(f"POST /api/recommend HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nContent-Length: 1000\r\n\r\n{{}}".encode())
    assert s.recv(1024) == b""  # the server gave up and closed the connection
    s.close()


def test_server_errors_say_what_happened_locally(server, monkeypatch):
    def broken(_q, _ctx=None):
        raise RuntimeError("detail for you")

    monkeypatch.setitem(webapp.ROUTES, ("GET", "/api/meta"), (broken, webapp.PUBLIC))
    status, d = call(server + "/api/meta")
    assert status == 500 and "detail for you" in d["error"]
