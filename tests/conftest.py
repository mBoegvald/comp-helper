"""Shared fixtures: a small database with known numbers, in a temp folder (never the real data/pickhelper.db)."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from fixture_db import seed  # noqa: E402

import db  # noqa: E402
import picker  # noqa: E402
import webapp  # noqa: E402


@pytest.fixture
def conn(tmp_path, monkeypatch):
    """Connection to a fresh seeded database; db.PATH points at it so every module uses it."""
    monkeypatch.setattr(db, "PATH", tmp_path / "test.db")
    monkeypatch.setattr(webapp, "REDDIT_DIR", tmp_path / "reddit")  # empty: no real Reddit files
    picker._CACHE.clear()
    webapp._names_cache.update(stamp=None, names={})
    webapp._tips_cache.update(stamp=None, data={})
    webapp._notes_cache.update(stamp=None, data={})  # keyed on the stamp, which restarts in every test database
    c = db.connect()
    seed(c)
    yield c
    c.close()


@pytest.fixture(autouse=True)
def local_mode(monkeypatch):
    """Every test starts in local mode (no accounts); hosted tests switch it on themselves."""
    monkeypatch.setitem(webapp.CONFIG, "hosted", False)
    monkeypatch.setitem(webapp.CONFIG, "secure_cookies", True)
    monkeypatch.setitem(webapp.CONFIG, "behind_proxy", False)
