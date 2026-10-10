"""Update pipeline safety: the lock, the daily backup, and refusing a broken Lolalytics fetch."""

import pytest

import build_role
import db
import update


def test_lock_is_exclusive_and_released(tmp_path):
    path = tmp_path / "update.lock"
    first, second = update.Lock(path), update.Lock(path)
    assert first.acquire()
    try:
        assert not second.acquire()
    finally:
        first.release()
    assert second.acquire()
    second.release()


def test_running_pid_is_readable_while_locked(tmp_path, monkeypatch):
    monkeypatch.setattr(update, "LOCK", tmp_path / "update.lock")
    lk = update.Lock(update.LOCK)
    assert lk.acquire()
    try:
        assert update.is_running()
        assert update.running_pid() == __import__("os").getpid()  # Windows locks a byte far past the PID
    finally:
        lk.release()
    assert not update.is_running()


def test_backup_once_per_day_and_pruned(conn, tmp_path, monkeypatch):
    monkeypatch.setattr(update, "BACKUPS", tmp_path / "backups")
    monkeypatch.setattr(update, "BACKUPS_KEPT", 2)
    update.BACKUPS.mkdir()
    for day in ("2026-01-01", "2026-01-02", "2026-01-03"):
        (update.BACKUPS / f"{day}_{db.PATH.name}").write_bytes(b"old")
    update.backup()
    update.backup()  # second run the same day: no new copy
    names = sorted(p.name for p in update.BACKUPS.iterdir())
    assert len(names) == 2 and names[0].startswith("2026-01-03")  # today's copy sorts last


def fake_fetch(rows_per_champ):
    def fetch(champ, delay, lane=""):
        return [
            {
                "opponent": f"Opp{i}",
                "wr": 50.0,
                "delta_vs_avg": 0.0,
                "delta_norm": 0.0,
                "opp_avg_wr": 50.0,
                "games": 500,
                "patch": "16.21",
                "tier": "EMERALD+",
            }
            for i in range(rows_per_champ)
        ]

    return fetch


def test_build_role_replaces_data_and_keeps_curated_edits(conn, monkeypatch):
    db.set_curated_matchup(conn, "top", "Garen", "Darius", tip="mine")
    monkeypatch.setattr(build_role.lola, "fetch", fake_fetch(3))
    build_role.build("top", delay=0)
    assert conn.execute("SELECT DISTINCT patch FROM lola WHERE role = 'top'").fetchall()[0][0] == "16.21"
    assert conn.execute("SELECT tip FROM curated_matchup").fetchone()[0] == "mine"


def test_build_role_refuses_a_fetch_that_lost_most_rows(conn, monkeypatch):
    monkeypatch.setattr(build_role.lola, "fetch", fake_fetch(0))
    before = conn.execute("SELECT count(*) FROM lola").fetchone()[0]
    with pytest.raises(SystemExit):
        build_role.build("top", delay=0)
    assert conn.execute("SELECT count(*) FROM lola").fetchone()[0] == before
