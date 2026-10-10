"""manage.py: the server-side admin commands."""

import pytest

import db
import manage


def test_backup_is_a_consistent_copy(conn, tmp_path, capsys):
    db.set_curated_matchup(conn, "top", "Garen", "Darius", tip="in the backup")
    dest = tmp_path / "copy.db"
    manage.main(["backup", str(dest)])
    copy = db.connect(dest)
    assert copy.execute("SELECT tip FROM curated_matchup").fetchone()[0] == "in the backup"
    assert (
        copy.execute("SELECT count(*) FROM lola").fetchone()[0]
        == conn.execute("SELECT count(*) FROM lola").fetchone()[0]
    )
    copy.close()
    assert "copied" in capsys.readouterr().out


def test_backup_never_overwrites(conn, tmp_path):
    dest = tmp_path / "exists.db"
    dest.write_text("keep me")
    with pytest.raises(SystemExit, match="exists"):
        manage.main(["backup", str(dest)])
    assert dest.read_text() == "keep me"


def test_delete_account_asks_for_the_name_again(conn, monkeypatch, capsys):
    import auth

    auth.create_account(conn, "asked", "asked password")
    monkeypatch.setattr("builtins.input", lambda _prompt: "typo")
    with pytest.raises(SystemExit, match="Not deleted"):
        manage.main(["delete-account", "asked"])
    assert [a["username"] for a in auth.list_accounts(conn)] == ["asked"]
    monkeypatch.setattr("builtins.input", lambda _prompt: "asked")
    manage.main(["delete-account", "asked"])
    assert auth.list_accounts(conn) == []
    assert "asked deleted" in capsys.readouterr().out
