"""Community notes: suggesting, reviewing and what gets shown (notes.py)."""

import pytest

import auth
import db
import notes


@pytest.fixture
def people(conn, monkeypatch):
    """(contributor id, second contributor id) with cheap password hashing."""
    monkeypatch.setattr(auth, "SCRYPT_N", 2**8)
    monkeypatch.setattr(auth, "SCRYPT_P", 1)
    return auth.create_account(conn, "pleb", "contributor pw"), auth.create_account(conn, "other", "contributor pw")


def test_a_suggestion_waits_for_review(conn, people):
    n = notes.suggest(conn, people[0], "top", "Darius", "Garen", "Trade when his Q is down.", "my games")
    assert (n["status"], n["author"], n["opponent"], n["source"]) == ("pending", "pleb", "Garen", "my games")
    assert notes.approved_index(conn) == {}  # nothing shown yet
    assert [p["id"] for p in notes.pending(conn)] == [n["id"]]


def test_admin_notes_are_approved_at_once(conn, people):
    n = notes.suggest(conn, people[0], "top", "Darius", None, "A note from the admin.", approve=True)
    assert n["status"] == "approved"
    assert notes.pending(conn) == []


def test_approve_with_corrected_text(conn, people):
    n = notes.suggest(conn, people[0], "top", "Darius", "Garen", "Trade when his Q is dwn.")
    done = notes.review(conn, n["id"], approve=True, text="Trade when his Q is down.")
    assert (done["status"], done["text"]) == ("approved", "Trade when his Q is down.")
    shown = notes.approved_index(conn)[("top", "darius", "garen")]
    assert [s["text"] for s in shown] == ["Trade when his Q is down."]
    assert shown[0]["author"] == "pleb"


def test_reject_with_a_reason(conn, people):
    n = notes.suggest(conn, people[0], "top", "Darius", None, "Darius is broken lol.")
    done = notes.review(conn, n["id"], approve=False, review_note="Not a tip.")
    assert (done["status"], done["review_note"]) == ("rejected", "Not a tip.")
    assert notes.approved_index(conn) == {}
    assert notes.for_account(conn, people[0])[0]["review_note"] == "Not a tip."


def test_a_note_is_reviewed_once(conn, people):
    n = notes.suggest(conn, people[0], "top", "Darius", None, "A perfectly fine note.")
    notes.review(conn, n["id"], approve=True)
    with pytest.raises(notes.NoteError, match="already reviewed"):
        notes.review(conn, n["id"], approve=False)


def test_champion_and_matchup_notes_are_kept_apart(conn, people):
    for opp in (None, "Garen"):
        n = notes.suggest(conn, people[0], "top", "Darius", opp, f"Note about {opp or 'Darius alone'}.")
        notes.review(conn, n["id"], approve=True)
    idx = notes.approved_index(conn)
    assert [n["text"] for n in idx[("top", "darius", "")]] == ["Note about Darius alone."]
    assert [n["text"] for n in idx[("top", "darius", "garen")]] == ["Note about Garen."]


@pytest.mark.parametrize(
    "text, source, message",
    [
        ("short", None, "10 to 1000"),
        ("x" * 1001, None, "10 to 1000"),
        ("A fine note.", "javascript:alert(1)//x://", "https://"),
        ("A fine note.", "ftp://files.example/x", "https://"),
        ("A fine note.", "s" * 201, "at most"),
    ],
)
def test_bad_notes_are_refused(conn, people, text, source, message):
    with pytest.raises(notes.NoteError, match=message):
        notes.suggest(conn, people[0], "top", "Darius", None, text, source)


def test_text_is_kept_on_one_line(conn, people):
    n = notes.suggest(conn, people[0], "top", "Darius", None, "  Line one\n\n\nline   two  ")
    assert n["text"] == "Line one line two"


def test_links_and_plain_sources_are_fine(conn, people):
    for source in ("https://www.reddit.com/r/DariusMains/", "http://example.com/guide", "a streamer called X"):
        assert (
            notes.suggest(conn, people[0], "top", "Darius", None, "A perfectly fine note.", source)["source"] == source
        )


def test_waiting_notes_are_capped_per_account(conn, people, monkeypatch):
    monkeypatch.setattr(notes, "MAX_PENDING", 2)
    for i in range(2):
        notes.suggest(conn, people[0], "top", "Darius", None, f"Waiting note number {i}.")
    with pytest.raises(notes.NoteError, match="waiting for review"):
        notes.suggest(conn, people[0], "top", "Darius", None, "One note too many.")
    notes.suggest(conn, people[1], "top", "Darius", None, "Someone else can still post.")


def test_blocking_rejects_waiting_notes_only(conn, people):
    kept = notes.suggest(conn, people[0], "top", "Darius", None, "Approved before the block.")
    notes.review(conn, kept["id"], approve=True)
    notes.suggest(conn, people[0], "top", "Darius", None, "Still waiting at the block.")
    notes.reject_pending_of(conn, people[0], "account blocked")
    assert notes.pending(conn) == []
    assert [n["text"] for n in notes.approved_index(conn)[("top", "darius", "")]] == ["Approved before the block."]


def test_delete_removes_a_note(conn, people):
    n = notes.suggest(conn, people[0], "top", "Darius", None, "Will be deleted soon.", approve=True)
    notes.delete(conn, n["id"])
    assert notes.approved_index(conn) == {}
    with pytest.raises(notes.NoteError):
        notes.delete(conn, n["id"])


def test_a_deleted_account_leaves_its_notes_without_author(conn, people):
    n = notes.suggest(conn, people[0], "top", "Darius", None, "Outlives its author.", approve=True)
    with conn:
        conn.execute("DELETE FROM account WHERE id = ?", (people[0],))
    assert notes.get(conn, n["id"])["author"] is None


def test_writes_bump_the_stamp(conn, people):
    before = db.stamp(conn)
    notes.suggest(conn, people[0], "top", "Darius", None, "Bumps the stamp once.")
    assert db.stamp(conn) == before + 1
