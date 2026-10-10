#!/usr/bin/env python3
"""Lolalytics counters scraper (Emerald+, current patch), used by build_role.py.

  python fetch_lolalytics.py --champs "Zed,Viktor" --lane middle [--out zed_viktor.csv]   # debug: print or save rows

One counters page per champion gives, for every opponent with >= 100 games: win rate, delta vs the champion's
average, normalised delta, opponent average win rate and game count. Labels and thresholds live in db.py.
"""
import argparse
import csv
import datetime as dt
import html
import re
import sys
import time
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
SLUG_OVERRIDES = {"Wukong": "wukong", "Nunu & Willump": "nunu", "Renata Glasc": "renata"}
CSV_FIELDS = ["champion", "opponent", "wr", "delta_vs_avg", "delta_norm", "opp_avg_wr", "games", "patch", "tier", "lane", "fetched_at"]

def slug(name: str) -> str:
    if name in SLUG_OVERRIDES:
        return SLUG_OVERRIDES[name]
    return re.sub(r"[^a-z0-9]", "", name.lower())


def norm(name: str) -> str:
    """Key for matching champion names between the sheet and Lolalytics (ignores case, spaces, punctuation)."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def page_text(raw: str) -> str:
    h = html.unescape(re.sub(r"<!--.*?-->", "", raw, flags=re.S))
    t = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", t)


def parse_counters(raw: str):
    t = page_text(raw)
    patch_m = re.search(r"Patch (\d+\.\d+)", t)
    tier_m = re.search(r"\b([A-Z]+\+?) Patch \d+\.\d+", t)
    patch = patch_m.group(1) if patch_m else ""
    tier = tier_m.group(1) if tier_m else ""
    rows = []
    sent = re.compile(
        r"wins against (?P<opp>.+?) (?P<wr>\d+\.\d+)% of the time which is (?P<d1>\d+\.\d+)% (?P<dir1>higher|lower) against "
        r"(?P=opp) than the average opponent\. After normalising both champions win rates .+? wins against (?P=opp) "
        r"(?P<d2>\d+\.\d+)% (?P<dir2>more|less) often than would be expected\. The average opponent winrate against "
        r"(?P=opp) is (?P<oppwr>\d+\.\d+)%"
    )
    for m in sent.finditer(t):
        opp = m.group("opp").strip()
        before = t[max(0, m.start() - 400): m.start()]
        g = re.findall(r"([\d,]+) Games vs " + re.escape(opp) + r"\b", before)
        games = int(g[-1].replace(",", "")) if g else None
        d1 = float(m.group("d1")) * (1 if m.group("dir1") == "higher" else -1)
        d2 = float(m.group("d2")) * (1 if m.group("dir2") == "more" else -1)
        rows.append({
            "opponent": opp, "wr": float(m.group("wr")), "delta_vs_avg": d1, "delta_norm": d2,
            "opp_avg_wr": float(m.group("oppwr")), "games": games, "patch": patch, "tier": tier,
        })
    return rows


def fetch(champ: str, delay: float, lane: str = ""):
    url = f"https://lolalytics.com/lol/{slug(champ)}/counters/" + (f"?lane={lane}" if lane else "")
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        print(f"  ! {champ}: HTTP {e.code} for {url}", file=sys.stderr)
        return []
    time.sleep(delay)
    rows = parse_counters(raw)
    if not rows:
        print(f"  ! {champ}: no matchup rows parsed from {url}", file=sys.stderr)
    return rows


def cmd_fetch(a):
    champs = [c.strip() for c in a.champs.split(",") if c.strip()]
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    f = open(a.out, "w", newline="", encoding="utf-8") if a.out else sys.stdout
    w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
    w.writeheader()
    for c in champs:
        for r in fetch(c, a.delay, a.lane):
            w.writerow({"champion": c, "fetched_at": now, "lane": a.lane, **r})
    if a.out:
        f.close()


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--champs", required=True, help="comma-separated champion names")
    p.add_argument("--lane", default="", help="lolalytics lane: top, jungle, middle, bottom, support (default: champion's main lane)")
    p.add_argument("--out", help="CSV file (default: print to the screen)")
    p.add_argument("--delay", type=float, default=1.5, help="seconds between requests")
    cmd_fetch(p.parse_args())


if __name__ == "__main__":
    main()
