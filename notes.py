"""Community notes (hosted mode): signed-in users suggest a note on a champion or a matchup, an admin reviews it, and
only approved notes are shown. A matchup note is written from the champion's side, like a curated lane tip.

Authors can edit their notes and withdraw them. A waiting or rejected note is changed in place and (again) waits
for review; an edit of an approved note waits as a revision while the approved text stays shown, so fixing a typo
never takes a good note off the site. The admin approves the revision (it replaces the text) or rejects it (the old
text stays, and the author sees why).

Spam brakes: length limits, at most MAX_PENDING waiting notes and revisions per account, a source that looks like a
link must be http(s), and blocking an account rejects its waiting notes and revisions. Notes from admins are approved
straight away, and so are their edits.
"""

import db

MIN_TEXT, MAX_TEXT = 10, 1000
MAX_SOURCE = 200
MAX_PENDING = 20

_FIELDS = """n.id, n.role, n.champion, n.opponent, n.text, n.source, n.status, n.created_at, n.reviewed_at,
             n.review_note, n.revised_text, n.revised_source, n.revised_at, n.account_id, a.username AS author"""
WAITING = "(n.status = 'pending' OR n.revised_text IS NOT NULL)"  # what the admin still has to review
EDIT_REJECTED = "Your edit was not accepted."


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


def _waiting(conn, account_id: int) -> int:
    return conn.execute(
        f"SELECT count(*) FROM community_note n WHERE n.account_id = ? AND {WAITING}", (account_id,)
    ).fetchone()[0]


def get(conn, note_id: int) -> dict:
    rows = _rows(conn, "n.id = ?", (note_id,))
    if not rows:
        raise NoteError("No such note.")
    return rows[0]


def suggest(conn, account_id: int, role: str, champion: str, opponent: str | None, text, source=None, *, approve=False):
    """A new note on `champion` (or on champion vs `opponent`), waiting for review unless `approve` (admins)."""
    text, source = _clean_text(text), _clean_source(source)
    with conn:
        conn.execute("BEGIN IMMEDIATE")  # take the write lock before counting: parallel requests line up at the cap
        waiting = _waiting(conn, account_id)
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


def edit(conn, account_id: int, note_id: int, text, source=None, *, approve=False) -> dict:
    """The author changes their note. Waiting or rejected: changed in place, and it (again) waits for review.
    Approved: the change waits as a revision and the approved text stays shown until an admin decides. With
    `approve` (an admin's own note) the change applies at once."""
    text, source = _clean_text(text), _clean_source(source)
    with conn:
        conn.execute("BEGIN IMMEDIATE")  # read, check the limit and write as one step
        n = get(conn, note_id)
        if n["account_id"] != account_id:
            raise NoteError("You can only edit your own notes.")
        now = db.now()
        if approve:
            conn.execute(
                "UPDATE community_note SET text = ?, source = ?, status = 'approved', reviewed_at = ?, review_note = NULL, "
                "revised_text = NULL, revised_source = NULL, revised_at = NULL WHERE id = ?",
                (text, source, now, note_id),
            )
        else:
            already_waiting = n["status"] == "pending" or n["revised_text"] is not None
            if not already_waiting and _waiting(conn, account_id) >= MAX_PENDING:
                raise NoteError(
                    f"You have {MAX_PENDING} notes and edits waiting for review. Please wait for those first."
                )
            if n["status"] == "approved":
                conn.execute(
                    "UPDATE community_note SET revised_text = ?, revised_source = ?, revised_at = ?, review_note = NULL "
                    "WHERE id = ?",
                    (text, source, now, note_id),
                )
            else:
                conn.execute(
                    "UPDATE community_note SET text = ?, source = ?, status = 'pending', reviewed_at = NULL, "
                    "review_note = NULL WHERE id = ?",
                    (text, source, note_id),
                )
        db.touch(conn)
    return get(conn, note_id)


def withdraw(conn, account_id: int, note_id: int):
    """The author deletes their own note, in any state."""
    with conn:
        if not conn.execute(
            "DELETE FROM community_note WHERE id = ? AND account_id = ?", (note_id, account_id)
        ).rowcount:
            raise NoteError("You can only withdraw your own notes.")
        db.touch(conn)


def for_account(conn, account_id: int) -> list[dict]:
    """An account's own notes, newest first, with status and the reviewer's reason."""
    return _rows(conn, "n.account_id = ? ORDER BY n.created_at DESC, n.id DESC", (account_id,))


def pending(conn) -> list[dict]:
    """New notes and edits of approved notes waiting for review, oldest first."""
    return _rows(conn, f"{WAITING} ORDER BY coalesce(n.revised_at, n.created_at), n.id")


def review(conn, note_id: int, approve: bool, text=None, review_note=None) -> dict:
    """Approve (optionally with the admin's corrected text) or reject (optionally with a reason) a waiting note, or
    a waiting edit of an approved note: approving it replaces the text, rejecting it keeps the old one."""
    reason = " ".join(str(review_note or "").split())[:MAX_SOURCE] or None
    with conn:
        conn.execute("BEGIN IMMEDIATE")  # read and decide as one step: another admin may be reviewing it too
        note = get(conn, note_id)
        now = db.now()
        if note["revised_text"] is not None:
            if approve:
                new_text = _clean_text(text) if text is not None else note["revised_text"]
                conn.execute(
                    "UPDATE community_note SET text = ?, source = ?, reviewed_at = ?, review_note = NULL, "
                    "revised_text = NULL, revised_source = NULL, revised_at = NULL WHERE id = ?",
                    (new_text, note["revised_source"], now, note_id),
                )
            else:
                conn.execute(
                    "UPDATE community_note SET review_note = ?, revised_text = NULL, revised_source = NULL, "
                    "revised_at = NULL WHERE id = ?",
                    (reason or EDIT_REJECTED, note_id),
                )
        elif note["status"] == "pending":
            new_text = _clean_text(text) if text is not None else note["text"]
            conn.execute(
                "UPDATE community_note SET status = ?, text = ?, reviewed_at = ?, review_note = ? WHERE id = ?",
                ("approved" if approve else "rejected", new_text, now, reason, note_id),
            )
        else:
            raise NoteError("That note was already reviewed.")
        db.touch(conn)
    return get(conn, note_id)


def delete(conn, note_id: int):
    with conn:
        if not conn.execute("DELETE FROM community_note WHERE id = ?", (note_id,)).rowcount:
            raise NoteError("No such note.")
        db.touch(conn)


def reject_pending_of(conn, account_id: int, reason: str):
    """When an account is blocked: its waiting notes are rejected and its waiting edits dropped, so they leave the
    review queue. Approved notes stay as they were."""
    with conn:
        conn.execute(
            "UPDATE community_note SET status = 'rejected', reviewed_at = ?, review_note = ? "
            "WHERE account_id = ? AND status = 'pending'",
            (db.now(), reason, account_id),
        )
        conn.execute(
            "UPDATE community_note SET revised_text = NULL, revised_source = NULL, revised_at = NULL "
            "WHERE account_id = ? AND revised_text IS NOT NULL",
            (account_id,),
        )
        db.touch(conn)


def approved_index(conn, key=db.norm) -> dict:
    """(role, key(champion), key(opponent) or '') -> approved notes, oldest first, for showing on the page. `key` must
    be the one the reader looks champions up with (webapp uses picker.key, which keeps apostrophes: Cho'Gath)."""
    out = {}
    for n in _rows(conn, "n.status = 'approved' ORDER BY n.reviewed_at, n.id"):
        k = (n["role"], key(n["champion"]), key(n["opponent"]) if n["opponent"] else "")
        out.setdefault(k, []).append(
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
    community notes so it is not shown twice. A curated label on that matchup stays. One transaction, and the note is
    read inside it: a note another admin deleted or promoted a moment ago cannot become a tip."""
    with conn:
        conn.execute("BEGIN IMMEDIATE")
        n = get(conn, note_id)
        if n["status"] != "approved" or not n["opponent"]:
            raise NoteError("Only an approved note on a matchup can become its lane tip.")
        tip = n["text"] + (f" (from {n['author']})" if n["author"] else "")
        key = (n["role"], n["champion"], n["opponent"])
        row = conn.execute(
            "SELECT result FROM curated_matchup WHERE role = ? AND champion = ? AND opponent = ?", key
        ).fetchone()
        db.write_curated_matchup(conn, *key, row["result"] if row else None, tip)
        conn.execute("DELETE FROM community_note WHERE id = ?", (note_id,))
        db.touch(conn)
    return n
