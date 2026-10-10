"""Shared fixtures: a small database with known numbers, in a temp folder (never the real data/pickhelper.db)."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import db  # noqa: E402
import picker  # noqa: E402
import webapp  # noqa: E402

# (champion, opponent, wr, delta_norm, games) for top, from each champion's own counters page
LOLA_TOP = [
    ("Aatrox", "Darius", 46.0, -3.0, 900),
    ("Darius", "Aatrox", 55.0, 3.4, 880),  # with the row above: dnorm -3.2, wr 45.5, games 880 -> Unfavored
    ("Aatrox", "Garen", 53.0, 2.5, 150),  # one direction only, under 200 games -> low sample
    ("Aatrox", "Zaahen", 51.0, 0.5, 50),  # under 100 games -> dropped unless it has a hand label or tip
    ("Garen", "Darius", 50.0, 1.2, 400),  # Even
]


def seed(conn):
    with conn:
        conn.executemany(
            "INSERT INTO lola VALUES ('top', ?, ?, ?, 0, ?, 50, ?, '16.20', 'EMERALD+', 'top', '2026-10-10T00:00Z')",
            LOLA_TOP,
        )
        conn.executemany("INSERT INTO pool VALUES ('top', ?)", [("Aatrox",), ("Darius",), ("Garen",), ("Zaahen",)])
        conn.execute("INSERT INTO reddit_tips VALUES ('Aatrox', 'Darius', 4, 3.2, '2026-01-02')")
        conn.execute(
            "INSERT INTO reddit_snippet VALUES ('Aatrox', 'Darius', 1, 'Aatrox mains on Darius', '2026-01-02', 'u1')"
        )
        conn.execute("INSERT INTO reddit_tips VALUES ('Darius', 'Aatrox', 1, 1.0, '2025-05-01')")
        conn.execute(
            "INSERT INTO reddit_snippet VALUES ('Darius', 'Aatrox', 1, 'Darius mains on Aatrox', '2025-05-01', 'u2')"
        )
        db.touch(conn, "lola_updated:top", "tips_updated")


@pytest.fixture
def conn(tmp_path, monkeypatch):
    """Connection to a fresh seeded database; db.PATH points at it so every module uses it."""
    monkeypatch.setattr(db, "PATH", tmp_path / "test.db")
    monkeypatch.setattr(webapp, "REDDIT_DIR", tmp_path / "reddit")  # empty: no real Reddit files
    picker._CACHE.clear()
    webapp._names_cache.update(stamp=None, names={})
    webapp._tips_cache.update(stamp=None, data={})
    c = db.connect()
    seed(c)
    yield c
    c.close()
