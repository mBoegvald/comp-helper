#!/usr/bin/env python3
"""Fetch mid-lane matchup win rates from lolalytics.com and merge them into midlane_overview.xlsx.

Usage:
  python fetch_lolalytics.py fetch [--xlsx midlane_overview.xlsx | --champs "Zed,Viktor"] [--out data/lolalytics_matchups.csv]
  python fetch_lolalytics.py apply [--xlsx midlane_overview.xlsx] [--csv data/lolalytics_matchups.csv] [--overwrite-result]

`fetch` downloads one counters page per champion (lane = middle, tier = Emerald+, current patch) and
writes one CSV row per (champion, opponent) with win rate, delta vs the champion's average, normalised
delta, opponent average win rate and game count. Only matchups with >= 100 games appear on the page.

`apply` adds "Lola WR", "Lola dNorm", "Lola games", "Lola label", "Lola patch", "Lola source" and "Mismatch"
columns to the Matchups sheet. Both directions (champion's page and opponent's page) are combined when present;
the label comes from the normalised delta (>= +2 Favored, <= -2 Unfavored), see the note at FAVORED_DELTA.
With --overwrite-result the Result column is replaced by the Lolalytics label where the sample
is large enough; the original is kept in a "Result (Claude)" column.
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
from pathlib import Path

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
SLUG_OVERRIDES = {"Wukong": "wukong", "Nunu & Willump": "nunu", "Renata Glasc": "renata"}
CSV_FIELDS = ["champion", "opponent", "wr", "delta_vs_avg", "delta_norm", "opp_avg_wr", "games", "patch", "tier", "lane", "fetched_at"]

# Labels use Lolalytics' normalised delta (dNorm), not the raw win rate: the site measures every matchup from the
# perspective of an Emerald+ player, who wins ~51.3% of mixed-rank games, so raw WRs for A vs B and B vs A sum to
# ~102-103%. dNorm is close to antisymmetric, and both directions are averaged when available.
FAVORED_DELTA = 2.0
UNFAVORED_DELTA = -2.0
MIN_GAMES = 200


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


def champs_from_xlsx(path: Path):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb["Champions"]
    rows = ws.iter_rows(values_only=True)
    header = [str(c).strip().lower() if c else "" for c in next(rows)]
    col = next((i for i, h in enumerate(header) if h in ("champion", "name", "champ")), 0)
    return [str(r[col]).strip() for r in rows if r and r[col]]


def cmd_fetch(a):
    if a.champs:
        champs = [c.strip() for c in a.champs.split(",") if c.strip()]
    else:
        champs = champs_from_xlsx(Path(a.xlsx))
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    n = 0
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        w.writeheader()
        for c in champs:
            rows = fetch(c, a.delay, a.lane)
            print(f"{c}: {len(rows)} opponents")
            for r in rows:
                w.writerow({"champion": c, "fetched_at": now, "lane": a.lane, **r})
                n += 1
    print(f"wrote {n} rows to {out}")


def label(dnorm: float, games) -> str:
    if games is not None and games < MIN_GAMES:
        return "low sample"
    if dnorm >= FAVORED_DELTA:
        return "Favored"
    if dnorm <= UNFAVORED_DELTA:
        return "Unfavored"
    return "Even"


def cmd_apply(a):
    import openpyxl
    data = {}
    with open(a.csv, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            data[(norm(r["champion"]), norm(r["opponent"]))] = r
    wb = openpyxl.load_workbook(a.xlsx)
    ws = wb["Matchups"]
    header = [str(c.value).strip() if c.value else "" for c in ws[1]]
    hl = [h.lower() for h in header]

    def col(name):
        name = name.lower()
        for i, h in enumerate(hl):
            if h == name or h.startswith(name):
                return i + 1
        raise SystemExit(f"Matchups sheet has no '{name}' column; header is {header}")

    ci, oi, ri = col("Champion"), col("Opponent"), col("Result")
    new_cols = ["Lola WR", "Lola dNorm", "Lola games", "Lola label", "Lola patch", "Lola source", "Mismatch"]
    if a.overwrite_result:
        new_cols.append("Result (Claude)")
    idx = {}
    for name in new_cols:
        if name.lower() in hl:
            idx[name] = hl.index(name.lower()) + 1
        else:
            ws.cell(row=1, column=ws.max_column + 1, value=name)
            header.append(name); hl.append(name.lower())
            idx[name] = len(header)

    stats = {"rows": 0, "matched": 0, "with_reverse": 0, "mismatch": 0, "overwritten": 0}
    for row in range(2, ws.max_row + 1):
        champ, opp = ws.cell(row, ci).value, ws.cell(row, oi).value
        if not champ or not opp:
            continue
        stats["rows"] += 1
        fwd = data.get((norm(champ), norm(opp)))
        rev = data.get((norm(opp), norm(champ)))
        if not fwd and not rev:
            ws.cell(row, idx["Lola label"], value="no data")
            continue
        wrs, dns, games_l = [], [], []
        if fwd:
            wrs.append(float(fwd["wr"])); dns.append(float(fwd["delta_norm"]))
            if fwd["games"]: games_l.append(int(fwd["games"]))
        if rev:
            wrs.append(100 - float(rev["wr"])); dns.append(-float(rev["delta_norm"]))
            if rev["games"]: games_l.append(int(rev["games"]))
            stats["with_reverse"] += 1
        r = fwd or rev
        src = "both" if fwd and rev else ("direct" if fwd else "reverse")
        wr, dn = sum(wrs) / len(wrs), sum(dns) / len(dns)
        stats["matched"] += 1
        games = min(games_l) if games_l else None
        lab = label(dn, games)
        ws.cell(row, idx["Lola WR"], value=round(wr, 2))
        ws.cell(row, idx["Lola dNorm"], value=round(dn, 2))
        ws.cell(row, idx["Lola games"], value=games)
        ws.cell(row, idx["Lola label"], value=lab)
        ws.cell(row, idx["Lola patch"], value=f"{r['patch']} {r['tier']}")
        ws.cell(row, idx["Lola source"], value=src)
        old = str(ws.cell(row, ri).value or "").strip()
        same = old.lower() == lab.lower() or (lab == "Even" and ("even" in old.lower() or "skill" in old.lower()))
        mism = lab in ("Favored", "Unfavored", "Even") and bool(old) and not same
        ws.cell(row, idx["Mismatch"], value="yes" if mism else "")
        if mism:
            stats["mismatch"] += 1
        if a.overwrite_result and lab in ("Favored", "Unfavored", "Even"):
            if ws.cell(row, idx["Result (Claude)"]).value is None:
                ws.cell(row, idx["Result (Claude)"], value=old)
            if not same:
                ws.cell(row, ri, value=lab)
                stats["overwritten"] += 1
    from safe_save import save_workbook; save_workbook(wb, a.xlsx)
    print(stats)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    f = sp.add_parser("fetch")
    f.add_argument("--xlsx", default="midlane_overview.xlsx")
    f.add_argument("--champs", help="comma-separated champion names (overrides --xlsx)")
    f.add_argument("--out", default="data/lolalytics_matchups.csv")
    f.add_argument("--delay", type=float, default=1.5, help="seconds between requests")
    f.add_argument("--lane", default="", help="lolalytics lane: top, jungle, middle, bottom, support (default: champion's main lane)")
    f.set_defaults(fn=cmd_fetch)
    ap = sp.add_parser("apply")
    ap.add_argument("--xlsx", default="midlane_overview.xlsx")
    ap.add_argument("--csv", default="data/lolalytics_matchups.csv")
    ap.add_argument("--overwrite-result", action="store_true")
    ap.set_defaults(fn=cmd_apply)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
