#!/usr/bin/env python3
"""Download matchup wiki pages and matchup threads from champion "xMains" subreddits (read-only, via PRAW).

Setup (one time):
  1. Create a "script" app at https://www.reddit.com/prefs/apps (redirect uri can be http://localhost:8080).
  2. export REDDIT_CLIENT_ID=... REDDIT_CLIENT_SECRET=...   (or put them in ~/.config/praw.ini under [comp-helper])
  3. pip install praw

Usage:
  python fetch_reddit.py [--champs "Zed,Viktor"] [--out data/reddit] [--threads 15] [--comments 40]

Output: data/reddit/<champion>.json with the subreddit's wiki pages (those whose name mentions matchup,
counter, guide, faq or index) and the top matchup threads with their highest-scored top-level comments.
Anonymous access to reddit.com is blocked (HTTP 403), so credentials are required.
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

SUB_OVERRIDES = {
    "Twisted Fate": "twistedfatemains",
    "Aurelion Sol": "aurelionsolmains",
    "Vel'Koz": "velkozmains",
    "Kai'Sa": "kaisamains",
    "Cho'Gath": "chogathmains",
    "Kha'Zix": "khazixmains",
    "LeBlanc": "leblancmains",
    "Wukong": "wukongmains",
    "Nunu & Willump": "nunumains",
    "Dr. Mundo": "drmundomains",
}
WIKI_RE = re.compile(r"matchup|counter|guide|faq|index|tips", re.I)
QUERIES = ["matchup", "matchups", "how to play against", "counter"]


def sub_name(champ: str) -> str:
    return SUB_OVERRIDES.get(champ, re.sub(r"[^a-z0-9]", "", champ.lower()) + "mains")


def make_reddit():
    import praw

    cid, sec = os.environ.get("REDDIT_CLIENT_ID"), os.environ.get("REDDIT_CLIENT_SECRET")
    ua = "linux:comp-helper:0.1 (mid lane matchup research)"
    if cid and sec:
        return praw.Reddit(client_id=cid, client_secret=sec, user_agent=ua)
    try:
        return praw.Reddit("comp-helper", user_agent=ua)
    except Exception as e:
        sys.exit(
            f"No Reddit credentials: set REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET or a [comp-helper] praw.ini section ({e})"
        )


def dump_champ(reddit, champ: str, out: Path, n_threads: int, n_comments: int):
    name = sub_name(champ)
    sub = reddit.subreddit(name)
    try:
        sub.id  # noqa: B018 - PRAW loads lazily; this raises if the subreddit does not exist or is private
    except Exception as e:
        print(f"  ! r/{name}: {type(e).__name__}: {e}", file=sys.stderr)
        return None
    result = {"champion": champ, "subreddit": name, "wiki": [], "threads": []}
    try:
        for page in sub.wiki:
            if WIKI_RE.search(page.name):
                result["wiki"].append(
                    {"name": page.name, "revised": getattr(page, "revision_date", None), "content": page.content_md}
                )
    except Exception as e:
        print(f"  ! r/{name} wiki: {type(e).__name__}: {e}", file=sys.stderr)
    seen = set()
    for q in QUERIES:
        try:
            for s in sub.search(q, sort="top", time_filter="all", limit=n_threads):
                if s.id in seen:
                    continue
                seen.add(s.id)
                s.comments.replace_more(limit=0)
                comments = sorted(s.comments, key=lambda c: c.score, reverse=True)[:n_comments]
                result["threads"].append(
                    {
                        "id": s.id,
                        "title": s.title,
                        "score": s.score,
                        "created_utc": s.created_utc,
                        "url": "https://www.reddit.com" + s.permalink,
                        "selftext": s.selftext,
                        "comments": [
                            {"score": c.score, "body": c.body}
                            for c in comments
                            if c.body not in ("[deleted]", "[removed]")
                        ],
                    }
                )
        except Exception as e:
            print(f"  ! r/{name} search '{q}': {type(e).__name__}: {e}", file=sys.stderr)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{re.sub(r'[^A-Za-z0-9]', '', champ)}.json").write_text(
        json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--champs")
    p.add_argument("--out", default="data/reddit")
    p.add_argument("--threads", type=int, default=15, help="threads per search query")
    p.add_argument("--comments", type=int, default=40, help="top-level comments kept per thread")
    a = p.parse_args()
    champs = [c.strip() for c in a.champs.split(",")] if a.champs else __import__("fetch_reddit_rss").all_champions()
    reddit = make_reddit()
    reddit.read_only = True
    for c in champs:
        r = dump_champ(reddit, c, Path(a.out), a.threads, a.comments)
        if r:
            print(f"{c}: r/{r['subreddit']} wiki pages={len(r['wiki'])} threads={len(r['threads'])}")
        time.sleep(1)


if __name__ == "__main__":
    main()
