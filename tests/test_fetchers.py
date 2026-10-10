"""Scrapers and tip extraction, offline: Lolalytics from a saved page, Reddit from a tiny made-up dump."""

import json
from pathlib import Path

import pytest

import extract_tips
import fetch_lolalytics

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_counters_reads_every_opponent():
    rows = fetch_lolalytics.parse_counters((FIXTURES / "lolalytics_counters.html").read_text(encoding="utf-8"))
    assert [r["opponent"] for r in rows] == ["Gangplank", "Vex", "Ekko"]
    gp, vex, ekko = rows
    assert (gp["wr"], gp["delta_vs_avg"], gp["delta_norm"], gp["opp_avg_wr"], gp["games"]) == (
        42.86,
        -4.95,
        -7.82,
        47.81,
        119,
    )
    assert (vex["delta_vs_avg"], vex["delta_norm"]) == (3.12, 0.26)  # 'higher' / 'more often' are positive
    assert ekko["games"] == 1430  # thousands separator
    assert (gp["patch"], gp["tier"]) == ("16.20", "EMERALD+")


@pytest.mark.parametrize("name, slug", [("Nunu & Willump", "nunu"), ("Kai'Sa", "kaisa"), ("Dr. Mundo", "drmundo")])
def test_slug(name, slug):
    assert fetch_lolalytics.slug(name) == slug


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Vi ganks a lot", ["Vi"]),
        ("vi is my editor", []),  # short names only match with a capital letter
        ("tf ult is annoying", ["Twisted Fate"]),
        ("Aurelion Sol outscales", ["Aurelion Sol"]),
        ("Viktor and Zed", ["Viktor", "Zed"]),
    ],
)
def test_mentions(text, expected):
    assert sorted(extract_tips.mentions(text)) == sorted(expected)


def thread(title, body, days, stale=False):
    return {
        "title": title,
        "body": body,
        "published": f"2026-0{days}-01",
        "url": f"https://reddit.example/{days}",
        "recency_weight": 1.0,
        "stale_items": stale,
        "comments": [],
    }


def test_build_ranks_tips_and_drops_stale_item_advice(conn, tmp_path):
    reddit = tmp_path / "reddit_dump"
    reddit.mkdir()
    dump = {
        "champion": "Zed",
        "threads": [
            thread("Zed vs Viktor", "Against Viktor you trade when his W is down and all-in at level 6 in lane.", 1),
            thread("Old build", "Rush items like Eclipse into Viktor, the build that worked back then.", 2, stale=True),
            thread("Help", "Play around the wave against Ahri and look for a short trade after her charm.", 3),
        ],
    }
    (reddit / "Zed.json").write_text(json.dumps(dump), encoding="utf-8")
    extract_tips.build(reddit, per_pair=3)
    tips = {(r["champion"], r["opponent"]): r["mentions"] for r in conn.execute("SELECT * FROM reddit_tips")}
    assert tips == {("Zed", "Viktor"): 1, ("Zed", "Ahri"): 1}  # the stale item paragraph is gone
    snip = conn.execute("SELECT text, url FROM reddit_snippet WHERE opponent = 'Viktor'").fetchone()
    assert snip["text"].startswith("Against Viktor") and snip["url"].endswith("/1")
