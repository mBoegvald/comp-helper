"""Accounts for hosted mode: passwords, sessions and rate limits. Local mode (the Windows app) has no accounts.

- Passwords: scrypt with a random salt; the parameters are stored in each hash, so they can be raised later.
- Sessions: a random token in an HttpOnly cookie. Only its SHA-256 is stored, so a copy of the database cannot be
  used to sign in. Sessions expire after SESSION_DAYS; blocking an account ends its sessions.
- Rate limits: attempts per IP address are kept in the database (shared by every server process).
"""

import datetime as dt
import hashlib
import hmac
import re
import secrets
import sqlite3
import time

import db

SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 5  # OWASP's 16 MiB setting
SCRYPT_MAXMEM = 64 * 1024 * 1024
SESSION_DAYS = 30
USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{3,24}$")
MIN_PASSWORD, MAX_PASSWORD = 10, 200
LIMITS = {"login": (10, 15 * 60), "signup": (3, 60 * 60)}  # kind -> (attempts, per seconds), per IP address
ROLES = ("contributor", "admin")


class AuthError(ValueError):
    """A problem the user can fix; the message is shown on the page."""


class RateLimited(Exception):
    """Too many attempts from one address."""


# ---------------------------------------------------------------- passwords


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(password.encode(), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, maxmem=SCRYPT_MAXMEM, dklen=32)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${h.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, n, r, p, salt, want = stored.split("$")
        if algo != "scrypt":
            return False
        got = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p), maxmem=SCRYPT_MAXMEM, dklen=32
        )
    except ValueError:
        return False
    return hmac.compare_digest(got.hex(), want)


_DUMMY_HASH = None


def _dummy_hash():
    """Checked against when a username does not exist, so a wrong name takes as long as a wrong password."""
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password(secrets.token_hex(16))
    return _DUMMY_HASH


def check_new_credentials(username: str, password: str):
    if not USERNAME_RE.match(username or ""):
        raise AuthError("Usernames are 3 to 24 letters, digits, '-' or '_'.")
    if not (MIN_PASSWORD <= len(password or "") <= MAX_PASSWORD):
        raise AuthError(f"Passwords are {MIN_PASSWORD} to {MAX_PASSWORD} characters.")


# ---------------------------------------------------------------- accounts


def create_account(conn, username: str, password: str, role: str = "contributor") -> int:
    check_new_credentials(username, password)
    if role not in ROLES:
        raise ValueError(f"role must be one of {', '.join(ROLES)}")
    try:
        with conn:
            cur = conn.execute(
                "INSERT INTO account (username, pw_hash, role, created_at) VALUES (?, ?, ?, ?)",
                (username, hash_password(password), role, db.now()),
            )
    except sqlite3.IntegrityError:
        raise AuthError("That username is taken.") from None
    return cur.lastrowid


def set_password(conn, username: str, password: str):
    check_new_credentials(username, password)
    with conn:
        cur = conn.execute("UPDATE account SET pw_hash = ? WHERE username = ?", (hash_password(password), username))
        if not cur.rowcount:
            raise AuthError(f"No account named {username}.")
        conn.execute("DELETE FROM session WHERE account_id = (SELECT id FROM account WHERE username = ?)", (username,))


def set_blocked(conn, account_id: int, blocked: bool):
    """Blocking also signs the account out everywhere."""
    with conn:
        cur = conn.execute("UPDATE account SET blocked = ? WHERE id = ?", (int(bool(blocked)), account_id))
        if not cur.rowcount:
            raise AuthError("No such account.")
        if blocked:
            conn.execute("DELETE FROM session WHERE account_id = ?", (account_id,))


def list_accounts(conn):
    return [
        dict(r)
        for r in conn.execute(
            "SELECT id, username, role, blocked, created_at FROM account ORDER BY username COLLATE NOCASE"
        )
    ]


# ---------------------------------------------------------------- sessions


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _expiry() -> str:
    return (dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=SESSION_DAYS)).strftime("%Y-%m-%dT%H:%M:%SZ")


def start_session(conn, account_id: int) -> str:
    token = secrets.token_urlsafe(32)
    with conn:
        conn.execute("DELETE FROM session WHERE expires_at < ?", (db.now(),))
        conn.execute("INSERT INTO session VALUES (?, ?, ?, ?)", (_token_hash(token), account_id, db.now(), _expiry()))
    return token


def login(conn, username: str, password: str) -> str:
    """Session token for a correct username and password; AuthError otherwise (the same message either way)."""
    row = conn.execute("SELECT id, pw_hash, blocked FROM account WHERE username = ?", (username or "",)).fetchone()
    ok = verify_password(password or "", row["pw_hash"] if row else _dummy_hash())
    if not row or not ok:
        raise AuthError("Wrong username or password.")
    if row["blocked"]:
        raise AuthError("This account is blocked.")
    return start_session(conn, row["id"])


def session_account(conn, token: str | None):
    """The signed-in account for a session token, or None (no token, unknown, expired or blocked)."""
    if not token:
        return None
    row = conn.execute(
        "SELECT a.id, a.username, a.role FROM session s JOIN account a ON a.id = s.account_id "
        "WHERE s.token_hash = ? AND s.expires_at > ? AND a.blocked = 0",
        (_token_hash(token), db.now()),
    ).fetchone()
    return dict(row) if row else None


def logout(conn, token: str | None):
    if token:
        with conn:
            conn.execute("DELETE FROM session WHERE token_hash = ?", (_token_hash(token),))


# ---------------------------------------------------------------- rate limits


def rate_limit(conn, ip: str, kind: str):
    """Count one attempt of `kind` from `ip`; RateLimited when the address is over its limit."""
    limit, window = LIMITS[kind]
    now = time.time()
    with conn:
        conn.execute("DELETE FROM attempt WHERE at < ?", (now - 24 * 3600,))
        recent = conn.execute(
            "SELECT count(*) FROM attempt WHERE ip = ? AND kind = ? AND at > ?", (ip, kind, now - window)
        ).fetchone()[0]
        if recent >= limit:
            raise RateLimited(f"Too many {kind} attempts from your address. Try again later.")
        conn.execute("INSERT INTO attempt VALUES (?, ?, ?)", (ip, kind, now))
