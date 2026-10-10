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
