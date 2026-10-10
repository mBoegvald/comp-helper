#!/usr/bin/env python3
"""Fetch matchup threads from champion "xMains" subreddits via Reddit's public RSS feeds (no login, no API key).

Reddit blocks anonymous HTML and .json access, but the Atom feeds still work:
  /r/<sub>/search.rss?q=...&restrict_sr=on&sort=top&t=all&limit=50   -> up to 50 threads with full self-text
  /r/<sub>/comments/<id>/.rss?limit=N                                 -> a thread's comments (optional, --comments)
Wiki pages have no feed and stay unreachable without a login. Anonymous feeds are rate-limited hard
(HTTP 429 after ~1 request/minute), so the default delay is 60 s and 429s are retried with backoff.

Each query is fetched twice: top of all time and top of the last year, so recent threads are not drowned out by
old high-score ones. Every thread is annotated with age_days, recency_weight (1.0 < 1 y, 0.7 < 2 y, 0.4 < 4 y,
0.2 older), a `topics` list (matchup / items / runes) and stale_items=True when it talks about items or runes
and is older than ITEM_STALE_DAYS (2 years): item and rune advice that old is not useful, lane dynamics mostly are.

Usage:
  python3 fetch_reddit_rss.py [--champs "Zed,Zilean"] [--out data/reddit]    # default: every champion in the database
                              [--queries "matchup"] [--comments 0] [--max-comment-threads 12] [--delay 60]

--comments N fetches up to N comments for the --max-comment-threads most promising threads per champion: threads
whose title names another champion or a matchup word, ranked by recency. One request per thread, so 48 champions
x 12 threads is ~10 hours at the default delay; threads that already have comments are not fetched again.

Output: data/reddit/<Champion>.json
  {champion, subreddit, feeds: [...], threads: [{id, title, url, published, age_days, recency_weight, topics,
   stale_items, body, comments}]}
Existing JSON files are reused: feeds already fetched are skipped, missing ones (e.g. the last-year feed for files
made by an older version) are fetched and merged, and annotations are recomputed. Delete a file to refetch it.
"""
import argparse
import datetime as dt
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
ITEM_STALE_DAYS = 2 * 365
TIME_FILTERS = ("all", "year")
ITEM_RE = re.compile(r"\b(items?|build|builds|mythic|legendary|boots|ludens|luden's|liandry|rylai|zhonya|"
                     r"everfrost|shadowflame|stormsurge|malignance|rabadon|void staff|cryptbloom|nashor|"
                     r"seraph|morello|banshee|lich bane|rod of ages|roa|eclipse|prowler|duskblade|youmuu|"
                     r"edge of night|serylda|collector|hubris|opportunity|voltaic|profane|hydra|ghostblade)\b", re.I)
RUNE_RE = re.compile(r"\b(runes?|keystone|electrocute|conqueror|first strike|phase rush|aery|comet|"
                     r"fleet|press the attack|pta|glacial|hail of blades|dark harvest|predator|grasp|"
                     r"unsealed spellbook|inspiration|domination|sorcery|precision|resolve)\b", re.I)
MATCHUP_RE = re.compile(r"\b(match-?ups?|counter|counters|lane|laning|vs\.?|versus|against|into|poke|trade|"
                        r"trading|all-?in|roam|wave|freeze|prio|priority|dodge|ban)\b", re.I)

SUB_OVERRIDES = {
    "Twisted Fate": "twistedfatemains", "Aurelion Sol": "Aurelion_Sol_mains", "Vel'Koz": "velkozmains",
    "Kai'Sa": "kaisamains", "Cho'Gath": "chogathmains", "Kha'Zix": "khazixmains", "LeBlanc": "leblancmains",
    "Wukong": "wukongmains", "Nunu & Willump": "nunumains", "Dr. Mundo": "drmundomains", "Renata Glasc": "renatamains", "Teemo": ["teemotalk", "teemotalks"], "Sion": "dirtysionmains", "Jinx": "leagueofjinx", "Zac": "thesecretweapon",
}


def sub_name(champ: str) -> str:
    o = SUB_OVERRIDES.get(champ, re.sub(r"[^a-z0-9]", "", champ.lower()) + "mains")
    return o[0] if isinstance(o, list) else o


def all_champions():
    """Every champion in any role's pool in data/pickhelper.db."""
    import db
    import role_data
    conn = db.connect()
    return sorted({c for r in role_data.ROLES for c in db.pool(conn, r)})


def get(url: str, delay: float, tries: int = 5) -> str | None:
    wait = delay
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/atom+xml,*/*"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                body = r.read().decode("utf-8", errors="ignore")
            time.sleep(delay)
            return body
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < tries - 1:
                wait *= 2
                print(f"    429, waiting {wait:.0f}s", file=sys.stderr)
                time.sleep(wait)
                continue
            print(f"    HTTP {e.code} for {url}", file=sys.stderr)
            time.sleep(delay)  # an error still counts against the rate limit
            return "blocked" if e.code in (403, 404) else None
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"    {e} for {url}", file=sys.stderr)
            time.sleep(delay)
            return None


def text(fragment: str) -> str:
    t = html.unescape(html.unescape(fragment))
    t = re.sub(r"<br\s*/?>|</p>|</li>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return re.sub(r"[ \t]+", " ", t).strip()


def entries(atom: str):
    out = []
    for e in re.findall(r"<entry>(.*?)</entry>", atom, flags=re.S):
        title = re.search(r"<title>(.*?)</title>", e, flags=re.S)
        link = re.search(r'<link href="([^"]+)"', e)
        pub = re.search(r"<published>(.*?)</published>", e)
        content = re.search(r"<content[^>]*>(.*?)</content>", e, flags=re.S)
        author = re.search(r"<name>(.*?)</name>", e)
        out.append({
            "title": html.unescape(title.group(1)) if title else "",
            "url": link.group(1) if link else "",
            "published": pub.group(1)[:10] if pub else "",
            "author": html.unescape(author.group(1)) if author else "",
            "body": text(content.group(1)) if content else "",
        })
    return out


def annotate(t: dict, today: dt.date) -> dict:
    """Add age, recency weight and topic tags. Idempotent."""
    try:
        age = (today - dt.date.fromisoformat(t["published"])).days
    except ValueError:
        age = None
    t["age_days"] = age
    if age is None:
        t["recency_weight"] = 0.5
    elif age < 365:
        t["recency_weight"] = 1.0
    elif age < 2 * 365:
        t["recency_weight"] = 0.7
    elif age < 4 * 365:
        t["recency_weight"] = 0.4
    else:
        t["recency_weight"] = 0.2
    blob = t["title"] + "\n" + t["body"]
    topics = []
    if MATCHUP_RE.search(blob):
        topics.append("matchup")
    if ITEM_RE.search(blob):
        topics.append("items")
    if RUNE_RE.search(blob):
        topics.append("runes")
    t["topics"] = topics
    t["stale_items"] = bool({"items", "runes"} & set(topics)) and age is not None and age > ITEM_STALE_DAYS
    return t


TITLE_HINT_RE = re.compile(r"\b(vs\.?|versus|against|into|match-?ups?|counter|help|how (do|to)|tips?|lane)\b", re.I)


def comment_candidates(threads, max_threads: int):
    """Threads most likely to hold matchup answers: question-like or champion-naming titles, newest first."""
    def key(t):
        title = t.get("title", "")
        hint = bool(TITLE_HINT_RE.search(title))
        return (t.get("recency_weight", 0.5) * (2 if hint else 1), t.get("published", ""))
    pool = [t for t in threads if not t.get("comments")]
    pool.sort(key=key, reverse=True)
    return pool[:max_threads]


def thread_id(url: str) -> str:
    m = re.search(r"/comments/([a-z0-9]+)/", url)
    return m.group(1) if m else ""


def sub_candidates(champ: str):
    """r/<champ>mains first; if that is blocked or empty, fall back to r/<champ>."""
    o = SUB_OVERRIDES.get(champ, re.sub(r"[^a-z0-9]", "", champ.lower()) + "mains")
    cands = list(o) if isinstance(o, list) else [o]
    plain = re.sub(r"[^a-z0-9]", "", champ.lower())
    return cands if plain in cands else cands + [plain]


def fetch_sub(champ: str, sub: str, dest: Path, queries, n_comments: int, delay: float, max_threads: int):
    data = {"champion": champ, "subreddit": sub, "feeds": [], "threads": []}
    if dest.exists():
        old = json.loads(dest.read_text(encoding="utf-8"))
        if old.get("subreddit") == sub:
            data.update(old)
            if "feeds" not in old and old.get("threads"):
                data["feeds"] = ["top_all:" + q for q in queries]
    by_id = {t["id"]: t for t in data["threads"]}
    wanted = [f"top_{tf}:{q}" for q in queries for tf in TIME_FILTERS]
    todo = [f for f in wanted if f not in data["feeds"]]
    fetched = 0
    if data.get("blocked"):
        todo = []
    for feed in todo:
        tf, q = feed.split(":", 1)[0].removeprefix("top_"), feed.split(":", 1)[1]
        url = f"https://www.reddit.com/r/{sub}/search.rss?" + urllib.parse.urlencode(
            {"q": q, "restrict_sr": "on", "sort": "top", "t": tf, "limit": 50})
        atom = get(url, delay)
        if atom == "blocked":
            data["blocked"] = "HTTP 403/404: private, banned or nonexistent subreddit"
            break
        if atom is None:
            continue
        data["feeds"].append(feed)
        fetched += 1
        for e in entries(atom):
            tid = thread_id(e["url"])
            if not tid or tid in by_id:
                continue
            e["id"] = tid
            e["body"] = re.sub(r"\s*submitted by\s+/u/\S+\s*(\[link\]\s*\[comments\])?\s*$", "", e["body"]).strip()
            e["comments"] = []
            by_id[tid] = e
            data["threads"].append(e)
    today = dt.date.today()
    for t in data["threads"]:
        annotate(t, today)
    if n_comments:
        for t in comment_candidates(data["threads"], max_threads):
            atom = get(f"https://www.reddit.com/r/{sub}/comments/{t['id']}/.rss?limit={n_comments}", delay)
            if atom is None or atom == "blocked":
                continue
            t["comments"] = [{"author": c["author"], "body": c["body"]} for c in entries(atom)[1:]]
            fetched += 1
    data["threads"].sort(key=lambda t: (t["recency_weight"], t["published"]), reverse=True)
    return data, fetched


def fetch_champ(champ: str, queries, out_dir: Path, n_comments: int, delay: float, max_threads: int = 12):
    dest = out_dir / f"{re.sub(r'[^A-Za-z0-9]', '', champ)}.json"
    cands = sub_candidates(champ)
    if dest.exists():
        old = json.loads(dest.read_text(encoding="utf-8"))
        old_sub = old.get("subreddit")
        if old_sub not in cands:
            print(f"{champ}: subreddit changed r/{old_sub} -> r/{cands[0]}, refetching")
        elif old_sub in cands[1:] and old.get("threads") and not old.get("blocked"):
            cands = cands[cands.index(old_sub):]  # an earlier run already fell back successfully: start there
    fetched = 0
    for i, sub in enumerate(cands):
        data, n = fetch_sub(champ, sub, dest, queries, n_comments, delay, max_threads)
        fetched += n
        if data["threads"] and not data.get("blocked"):
            break
        if i + 1 < len(cands):
            why = "blocked" if data.get("blocked") else "no threads"
            print(f"{champ}: r/{sub} {why}, trying r/{cands[i + 1]}")
        elif data.get("blocked"):
            print(f"{champ}: r/{sub} is blocked ({data['blocked']}); delete {dest.name} to retry")
    out_dir.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    recent = sum(1 for t in data["threads"] if t["age_days"] is not None and t["age_days"] < 365)
    with_c = sum(1 for t in data["threads"] if t.get("comments"))
    print(f"{champ}: r/{data['subreddit']} threads={len(data['threads'])} (<1y: {recent}, with comments: {with_c}) requests now={fetched} -> {dest}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--champs")
    p.add_argument("--out", default="data/reddit")
    p.add_argument("--queries", default="matchup", help="comma-separated search queries; each costs one request per time filter (all, year)")
    p.add_argument("--comments", type=int, default=0, help="also fetch up to N comments for the best threads (one request per thread)")
    p.add_argument("--max-comment-threads", type=int, default=12, help="threads per champion to fetch comments for")
    p.add_argument("--delay", type=float, default=60, help="seconds between requests")
    a = p.parse_args()
    champs = [c.strip() for c in a.champs.split(",") if c.strip()] if a.champs else all_champions()
    queries = [q.strip() for q in a.queries.split(",") if q.strip()]
    for c in champs:
        fetch_champ(c, queries, Path(a.out), a.comments, a.delay, a.max_comment_threads)


if __name__ == "__main__":
    main()
