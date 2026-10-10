"""Accounts, sessions and rate limits (auth.py)."""

import pytest

import auth
import db


@pytest.fixture(autouse=True)
def fast_scrypt(monkeypatch):
    """Cheap hashing so the tests run fast; test_real_scrypt_settings checks the real ones."""
    monkeypatch.setattr(auth, "SCRYPT_N", 2**8)
    monkeypatch.setattr(auth, "SCRYPT_P", 1)
    monkeypatch.setattr(auth, "_DUMMY_HASH", None)


def test_real_scrypt_settings(monkeypatch):
    monkeypatch.undo()
    h = auth.hash_password("correct horse battery")
    assert h.startswith(f"scrypt${2**14}$8$5$")
    assert auth.verify_password("correct horse battery", h)


def test_hashes_are_salted_and_checked():
    a, b = auth.hash_password("same password"), auth.hash_password("same password")
    assert a != b
    assert auth.verify_password("same password", a)
    assert not auth.verify_password("other password", a)
    assert not auth.verify_password("same password", "garbage")


def test_old_parameters_still_verify(monkeypatch):
    h = auth.hash_password("long enough pw")  # made with the cheap settings
    monkeypatch.setattr(auth, "SCRYPT_N", 2**9)  # settings raised later
    assert auth.verify_password("long enough pw", h)


@pytest.mark.parametrize(
    "username, password",
    [("ab", "long enough pw"), ("has space", "long enough pw"), ("x" * 25, "long enough pw"), ("okname", "short")],
)
def test_bad_credentials_are_refused(conn, username, password):
    with pytest.raises(auth.AuthError):
        auth.create_account(conn, username, password)


def test_usernames_are_unique_ignoring_case(conn):
    auth.create_account(conn, "Mikkel", "long enough pw")
    with pytest.raises(auth.AuthError, match="taken"):
        auth.create_account(conn, "mikkel", "another long pw")


def test_login_and_session(conn):
    auth.create_account(conn, "alice", "long enough pw")
    token = auth.login(conn, "alice", "long enough pw")
    assert auth.session_account(conn, token)["username"] == "alice"
    assert auth.session_account(conn, "made-up") is None
    assert auth.session_account(conn, None) is None


def test_only_the_token_hash_is_stored(conn):
    auth.create_account(conn, "alice", "long enough pw")
    token = auth.login(conn, "alice", "long enough pw")
    stored = conn.execute("SELECT token_hash FROM session").fetchone()[0]
    assert token not in stored
    assert auth.session_account(conn, stored) is None  # a copied database row cannot be used as a token


@pytest.mark.parametrize("username, password", [("alice", "wrong password!"), ("nobody", "long enough pw")])
def test_wrong_login_says_the_same_thing(conn, username, password):
    auth.create_account(conn, "alice", "long enough pw")
    with pytest.raises(auth.AuthError, match="Wrong username or password"):
        auth.login(conn, username, password)


def test_logout_ends_the_session(conn):
    auth.create_account(conn, "alice", "long enough pw")
    token = auth.login(conn, "alice", "long enough pw")
    auth.logout(conn, token)
    assert auth.session_account(conn, token) is None


def test_expired_sessions_do_not_count(conn):
    account = auth.create_account(conn, "alice", "long enough pw")
    token = auth.start_session(conn, account)
    with conn:
        conn.execute("UPDATE session SET expires_at = '2000-01-01T00:00:00Z'")
    assert auth.session_account(conn, token) is None


def test_blocking_signs_out_and_stops_login(conn):
    account = auth.create_account(conn, "spammer", "long enough pw")
    token = auth.login(conn, "spammer", "long enough pw")
    auth.set_blocked(conn, account, True)
    assert auth.session_account(conn, token) is None
    with pytest.raises(auth.AuthError, match="blocked"):
        auth.login(conn, "spammer", "long enough pw")
    auth.set_blocked(conn, account, False)
    assert auth.login(conn, "spammer", "long enough pw")


def test_new_password_signs_out_everywhere(conn):
    auth.create_account(conn, "alice", "long enough pw")
    token = auth.login(conn, "alice", "long enough pw")
    auth.set_password(conn, "alice", "a new long password")
    assert auth.session_account(conn, token) is None
    assert auth.login(conn, "alice", "a new long password")


def test_deleting_an_account_deletes_its_sessions(conn):
    account = auth.create_account(conn, "alice", "long enough pw")
    auth.start_session(conn, account)
    with conn:
        conn.execute("DELETE FROM account WHERE id = ?", (account,))
    assert conn.execute("SELECT count(*) FROM session").fetchone()[0] == 0


def test_rate_limit_per_address(conn, monkeypatch):
    monkeypatch.setitem(auth.LIMITS, "login", (3, 60))
    for _ in range(3):
        auth.rate_limit(conn, "1.2.3.4", "login")
    with pytest.raises(auth.RateLimited):
        auth.rate_limit(conn, "1.2.3.4", "login")
    auth.rate_limit(conn, "5.6.7.8", "login")  # other addresses are not affected


def test_rate_limit_window_passes(conn, monkeypatch):
    monkeypatch.setitem(auth.LIMITS, "signup", (1, 60))
    auth.rate_limit(conn, "1.2.3.4", "signup")
    with conn:
        conn.execute("UPDATE attempt SET at = at - 120")
    auth.rate_limit(conn, "1.2.3.4", "signup")


def test_accounts_live_in_the_test_database(conn):
    assert str(db.PATH).endswith("test.db")
