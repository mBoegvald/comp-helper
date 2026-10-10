"""Community notes (hosted mode): signed-in users suggest a note on a champion or a matchup, an admin reviews it, and
only approved notes are shown. A matchup note is written from the champion's side, like a curated lane tip.

Spam brakes: length limits, at most MAX_PENDING waiting notes per account, a source that looks like a link must be
http(s), and blocking an account rejects its waiting notes. Notes from admins are approved straight away.
"""

import db

MIN_TEXT, MAX_TEXT = 10, 1000
MAX_SOURCE = 200
MAX_PENDING = 20

_FIELDS = """n.id, n.role, n.champion, n.opponent, n.text, n.source, n.status, n.created_at, n.reviewed_at,
             n.review_note, a.username AS author"""


class NoteError(ValueError):
    """A problem the user can fix; the message is shown on the page."""


def _clean_text(text) -> str:
    text = " ".join(str(text or "").split())  # one line: no layout tricks
    if not (MIN_TEXT <= len(text) <= MAX_TEXT):
        raise NoteError(f"Notes are {MIN_TEXT} to {MAX_TEXT} characters.")
    return text


def _clean_source(source) -> str | None:
    source = " ".join(str(source or "").split())
    if not source:
        return None
    if len(source) > MAX_SOURCE:
        raise NoteError(f"A source is at most {MAX_SOURCE} characters.")
    if "://" in source and not source.lower().startswith(("https://", "http://")):
        raise NoteError("A link as source must start with https:// or http://.")
    return source


def _rows(conn, where, params=()):
    sql = f"SELECT {_FIELDS} FROM community_note n LEFT JOIN account a ON a.id = n.account_id WHERE {where}"
    return [dict(r) for r in conn.execute(sql, params)]


def get(conn, note_id: int) -> dict:
    rows = _rows(conn, "n.id = ?", (note_id,))
    if not rows:
        raise NoteError("No such note.")
    return rows[0]


def suggest(conn, account_id: int, role: str, champion: str, opponent: str | None, text, source=None, *, approve=False):
    """A new note on `champion` (or on champion vs `opponent`), waiting for review unless `approve` (admins)."""
    text, source = _clean_text(text), _clean_source(source)
    with conn:
        waiting = conn.execute(
            "SELECT count(*) FROM community_note WHERE account_id = ? AND status = 'pending'", (account_id,)
        ).fetchone()[0]
        if not approve and waiting >= MAX_PENDING:
            raise NoteError(f"You have {waiting} notes waiting for review. Please wait for those first.")
        now = db.now()
        cur = conn.execute(
            "INSERT INTO community_note (role, champion, opponent, text, source, account_id, status, created_at, "
            "reviewed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (role, champion, opponent, text, source, account_id, "approved" if approve else "pending", now,
             now if approve else None),
        )  # fmt: skip
        db.touch(conn)
    return get(conn, cur.lastrowid)


def for_account(conn, account_id: int) -> list[dict]:
    """An account's own notes, newest first, with status and the reviewer's reason."""
    return _rows(conn, "n.account_id = ? ORDER BY n.created_at DESC, n.id DESC", (account_id,))


def pending(conn) -> list[dict]:
    """Notes waiting for review, oldest first."""
    return _rows(conn, "n.status = 'pending' ORDER BY n.created_at, n.id")


def review(conn, note_id: int, approve: bool, text=None, review_note=None) -> dict:
    """Approve (optionally with the admin's corrected text) or reject (optionally with a reason) a waiting note."""
    note = get(conn, note_id)
    if note["status"] != "pending":
        raise NoteError("That note was already reviewed.")
    new_text = _clean_text(text) if text is not None else note["text"]
    reason = " ".join(str(review_note or "").split())[:MAX_SOURCE] or None
    with conn:
        conn.execute(
            "UPDATE community_note SET status = ?, text = ?, reviewed_at = ?, review_note = ? WHERE id = ?",
            ("approved" if approve else "rejected", new_text, db.now(), reason, note_id),
        )
        db.touch(conn)
    return get(conn, note_id)


def delete(conn, note_id: int):
    with conn:
        if not conn.execute("DELETE FROM community_note WHERE id = ?", (note_id,)).rowcount:
            raise NoteError("No such note.")
        db.touch(conn)


def reject_pending_of(conn, account_id: int, reason: str):
    """When an account is blocked: its waiting notes are rejected, so they leave the review queue."""
    with conn:
        conn.execute(
            "UPDATE community_note SET status = 'rejected', reviewed_at = ?, review_note = ? "
            "WHERE account_id = ? AND status = 'pending'",
            (db.now(), reason, account_id),
        )
        db.touch(conn)


def approved_index(conn) -> dict:
    """(role, norm(champion), norm(opponent) or '') -> approved notes, oldest first, for showing on the page."""
    out = {}
    for n in _rows(conn, "n.status = 'approved' ORDER BY n.reviewed_at, n.id"):
        key = (n["role"], db.norm(n["champion"]), db.norm(n["opponent"]))
        out.setdefault(key, []).append(
            {
                "id": n["id"],
                "author": n["author"],
                "text": n["text"],
                "source": n["source"],
                "approved_at": n["reviewed_at"],
            }
        )
    return out


def promote_to_tip(conn, note_id: int) -> dict:
    """An approved matchup note becomes the curated lane tip for its side, credited to its author, and leaves the
    community notes so it is not shown twice. A curated label on that matchup stays. One transaction."""
    n = get(conn, note_id)
    if n["status"] != "approved" or not n["opponent"]:
        raise NoteError("Only an approved note on a matchup can become its lane tip.")
    tip = n["text"] + (f" (from {n['author']})" if n["author"] else "")
    key = (n["role"], n["champion"], n["opponent"])
    with conn:
        row = conn.execute(
            "SELECT result FROM curated_matchup WHERE role = ? AND champion = ? AND opponent = ?", key
        ).fetchone()
        conn.execute(
            "INSERT OR REPLACE INTO curated_matchup VALUES (?, ?, ?, ?, ?, ?)",
            (*key, row["result"] if row else None, tip, db.now()),
        )
        conn.execute("DELETE FROM community_note WHERE id = ?", (note_id,))
        db.touch(conn)
    return n
