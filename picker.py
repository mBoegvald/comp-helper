#!/usr/bin/env python3
"""Pick helper for any role. Reads data/pickhelper.db (see db.py); hand edits are made on the web page.

Usage:
  python picker.py --role top vs Renekton          # best picks into an enemy laner (role defaults to mid)
  python picker.py --role jungle matchups "Lee Sin"
  python picker.py --role top comp --enemy "Renekton,Mundo,Ahri,Yunara,Milio" --ally "Maokai,Yone,Caitlyn,Morgana" --style wombo
      --role    top | jungle | mid | bot | support (aliases: jg, adc, sup)
      --enemy   enemy champs (any role; the enemy in your role gets the most weight if it's in the data)
      --ally    allied champs (excluded from picks; mids among them count for AP/AD balance)
      --style   wombo | poke | pick | dive | split | scaling  (optional)
      --need    ap | ad  (optional, overrides auto-detect)
      --top N   number of results (default 5)
"""
import argparse
import re
import sys

import db
import role_data

ROLE = "mid"

ALIASES = {
    "tf": "twisted fate", "asol": "aurelion sol", "kass": "kassadin", "vlad": "vladimir",
    "cass": "cassiopeia", "cassio": "cassiopeia", "lb": "leblanc", "kata": "katarina",
    "malz": "malzahar", "ori": "orianna", "vel": "vel'koz", "velkoz": "vel'koz",
    "panth": "pantheon", "liss": "lissandra", "qiy": "qiyana", "naf": "naafiri",
    # other roles
    "mundo": "dr mundo", "drmundo": "dr mundo", "j": "jarvan iv", "jarvan": "jarvan iv", "ww": "warwick",
    "mf": "miss fortune", "tk": "tahm kench", "tahm": "tahm kench", "ksante": "k'sante", "kog": "kog'maw",
    "kogmaw": "kog'maw", "rek": "rek'sai", "reksai": "rek'sai", "nunu": "nunu willump", "xin": "xin zhao",
    "yi": "master yi", "lee": "lee sin", "gp": "gangplank", "noc": "nocturne", "fiddle": "fiddlesticks",
    "heimer": "heimerdinger", "morde": "mordekaiser", "renek": "renekton", "malph": "malphite",
    "naut": "nautilus", "blitz": "blitzcrank", "cait": "caitlyn", "ez": "ezreal", "trist": "tristana",
    "sera": "seraphine", "kha": "kha'zix", "khazix": "kha'zix", "cho": "cho'gath", "chogath": "cho'gath",
    "kai": "kai'sa", "kaisa": "kai'sa", "bel": "bel'veth", "belveth": "bel'veth", "renata": "renata glasc",
    "aph": "aphelios", "sej": "sejuani", "hec": "hecarim", "voli": "volibear", "trynd": "tryndamere",
    "kench": "tahm kench", "vik": "viktor", "wu": "wukong", "monkey": "wukong",
}
STYLE_WORDS = {
    "wombo": ["wombo", "teamfight"], "poke": ["poke", "siege"], "pick": ["pick"],
    "dive": ["dive"], "split": ["split", "flank"], "scaling": ["scaling", "late", "front-to-back"],
}
# archetype -> words that describe it in the "Good into"/"Struggles into" text (mid; other roles come from role_data)
ARCH_WORDS = {
    "Control mage": ["mages", "immobile"], "Artillery": ["mages", "immobile", "long range", "poke"],
    "Utility mage": ["mages"], "AD assassin": ["assassins", "ad assassin", "dive"],
    "AP assassin": ["assassins", "ap assassin", "dive", "ap"], "Melee carry": ["melee", "dash"],
    "Melee skirmisher": ["melee"], "Scaling": ["mages", "scaling"], "Roamer": ["immobile"],
}
for _role, _archs in role_data.ARCHETYPES.items():
    for _a, (_words, _g, _b) in _archs.items():
        ARCH_WORDS.setdefault(_a, _words)
RESULT = {"Favored": 3, "Even / skill": 0, "Unfavored": -3}


def norm(s):
    return re.sub(r"[^a-z']", " ", s.lower()).strip()


def key(s):
    s = norm(s).replace(" ", "")
    return ALIASES.get(s, s).replace(" ", "")


_CACHE = {}


def load_full(role=None):
    """(champs, mu, info) for a role, cached until the database changes.
    champs: key -> Champions row; mu: (champ, opp) -> (score, tip text); info: (champ, opp) -> raw matchup fields."""
    role = role or ROLE
    conn = db.connect()
    try:
        stamp = db.stamp(conn)
        hit = _CACHE.get(role)
        if hit and hit[0] == stamp:
            return hit[1]
        if not conn.execute("SELECT 1 FROM pool WHERE role = ? LIMIT 1", (role,)).fetchone():
            raise FileNotFoundError(f"no {role} data in {db.PATH.name} yet. Fetch it with: python update.py lolalytics")
        comb = db.combined(db.lola_rows(conn, role))
        champs = {key(c["name"]): c for c in db.champions(conn, role, comb)}
        rows = db.matchups(conn, role, comb)
    finally:
        conn.close()
    mu, info = {}, {}  # (champ, opp) -> (score, tip); (champ, opp) -> raw fields
    for row in rows:
        c, o, res, tip = row["champ"], row["opp"], row["result"], row["tip"]
        hand_tip = tip
        v = RESULT.get(res, 0)
        # use the normalised win-rate delta (both directions averaged) when present,
        # scaled so +-2 (the Favored/Unfavored threshold) maps to +-3
        dn, games = row["dnorm"], row["games"]
        if isinstance(dn, (int, float)):
            v = max(-3.0, min(3.0, round(dn * 1.5, 1)))
            if isinstance(games, (int, float)) and games < 200:
                v = round(v * 0.7, 1)  # thin sample: trust it less
            if not tip:
                tip = f"(lolalytics {dn:+.1f}, {int(games) if games else '?'} games)"
        # first Reddit snippet rides along with the hand-written tip
        rt = row["reddit_tips"]
        if rt:
            tip = f"{tip or ''} [reddit] {str(rt).split(' | ')[0][:200]}".strip()
        mu[(key(c), key(o))] = (v, tip)
        mu.setdefault((key(o), key(c)), (-v, f"[{c}'s tip] {tip}"))
        info[(key(c), key(o))] = {"champ": c, "opp": o, "score": v, "result": res, "hand_tip": hand_tip,
                                  "wr": row["wr"], "dnorm": dn, "games": games, "label": row["label"],
                                  "mismatch": row["mismatch"], "reddit_mentions": row["reddit_mentions"],
                                  "reddit_newest": row["reddit_newest"]}
    _CACHE[role] = (stamp, (champs, mu, info))
    return champs, mu, info


def load(role=None):
    try:
        champs, mu, _ = load_full(role)
    except FileNotFoundError as e:
        sys.exit(str(e))
    return champs, mu


def _display(key):
    """best-effort display name for a champion key not in the role data (for damage lookup)"""
    for n in role_data.DAMAGE_OVERRIDE | {c: c for c in role_data.DAMAGE["AP"]}:
        if re.sub(r"[^a-z']", "", n.lower()) == key:
            return n
    return key.title()


def resolve(name, champs):
    k = key(name)
    if k in champs or k in KNOWN:  # an exact champion name never gets prefix-matched into another one (Vi != Viktor)
        return k
    hits = [c for c in champs if c.startswith(k)]
    return hits[0] if len(hits) == 1 else k  # unknown non-mids are kept as raw keys


KNOWN = {key(c) for r in role_data.CHAMPS.values() for c in r} | {key(c) for v in role_data.DAMAGE.values() for c in v} \
    | {key(c) for c in role_data.DAMAGE_OVERRIDE}


def mentions(text, enemy_key, champs):
    t = norm(text or "").replace(" ", "")
    return enemy_key in t


def score(cand, enemies, enemy_mid, allies, style, need, champs, mu, detail=None):
    """detail: optional list that receives one dict per scoring reason (for the web page)."""
    c = champs[cand]
    s, why = 0.0, []
    add = detail.append if detail is not None else (lambda d: None)
    for e in enemies:
        main = e == enemy_mid
        if (cand, e) in mu:
            v, tip = mu[(cand, e)]
            w = v if main else v / 3
            s += w
            ename = champs.get(e, {}).get("name", e)
            why.append(f"{w:+.1f} vs {ename}: {tip}")
            add({"kind": "matchup", "value": w, "enemy": e, "enemy_name": ename, "main": main})
            continue
        en = champs.get(e)
        ename = en["name"] if en else e
        if mentions(c["good"], e, champs):
            s += 2 if main else 1
            why.append(f"good into {ename}")
            add({"kind": "text", "value": 2 if main else 1, "enemy": e, "enemy_name": ename, "main": main, "text": f"listed as good into {ename}"})
        elif mentions(c["bad"], e, champs):
            s -= 2 if main else 1
            why.append(f"struggles into {ename}")
            add({"kind": "text", "value": -2 if main else -1, "enemy": e, "enemy_name": ename, "main": main, "text": f"listed as struggling into {ename}"})
        elif en:
            words = ARCH_WORDS.get(en["arch"], [])
            if any(w in (c["good"] or "").lower() for w in words):
                s += 0.5
                why.append(f"good into {en['arch'].lower()} ({ename})")
                add({"kind": "archetype", "value": 0.5, "enemy": e, "enemy_name": ename, "main": main, "text": f"good into {en['arch'].lower()}s ({ename})"})
            if any(w in (c["bad"] or "").lower() for w in words):
                s -= 0.5
                why.append(f"weak to {en['arch'].lower()} ({ename})")
                add({"kind": "archetype", "value": -0.5, "enemy": e, "enemy_name": ename, "main": main, "text": f"weak to {en['arch'].lower()}s ({ename})"})
    if style and any(w in (c["comps"] or "").lower() for w in STYLE_WORDS[style]):
        s += 2
        why.append(f"fits {style} comp")
        add({"kind": "style", "value": 2, "text": f"fits a {style} comp"})
    if need and need.upper() in (c["dmg"] or "").upper():
        s += 1
        why.append(f"gives {need.upper()} damage")
        add({"kind": "damage", "value": 1, "text": f"gives the team {need.upper()} damage"})
    if not enemy_mid:
        b = {"Yes": 1, "Mostly": 0.5}.get(c["blind"], 0)
        if b:
            s += b
            why.append("blind-safe")
            add({"kind": "blind", "value": b, "text": "safe to blind pick"})
    return s, why


def cmd_vs(args, champs, mu):
    e = resolve(args.name, champs)
    rows = sorted(((score(c, [e], e, [], None, None, champs, mu), c) for c in champs if c != e),
                  key=lambda x: -x[0][0])
    print(f"\nBest picks into {champs.get(e, {}).get('name', args.name)}:")
    for (s, why), c in rows[:args.top]:
        print(f"  {s:+5.1f}  {champs[c]['name']:<14} {'; '.join(why)}")
    print("\nAvoid:")
    for (s, why), c in rows[-3:][::-1]:
        if s < 0:
            print(f"  {s:+5.1f}  {champs[c]['name']:<14} {'; '.join(why)}")


def cmd_matchups(args, champs, mu):
    c = resolve(args.name, champs)
    if c not in champs:
        sys.exit(f"Unknown champion: {args.name}")
    ch = champs[c]
    print(f"\n{ch['name']} ({ch['arch']}, {ch['dmg']}) | comps: {ch['comps']} | pick when: {ch['when']}")
    rows = sorted(((v, o, tip) for (a, o), (v, tip) in mu.items() if a == c), key=lambda x: -x[0])
    for v, o, tip in rows:
        label = "Favored  " if v >= 3 else ("Unfavored" if v <= -3 else "Even     ")
        print(f"  {label} vs {champs.get(o, {}).get('name', o):<14} {tip}")


def cmd_comp(args, champs, mu):
    split = lambda s: [resolve(x, champs) for x in s.split(",") if x.strip()] if s else []
    enemies, allies = split(args.enemy), split(args.ally)
    unknown = [e for e in enemies + allies if e not in champs]
    enemy_mids = [e for e in enemies if e in champs]
    enemy_mid = enemy_mids[0] if enemy_mids else None
    need = args.need
    if not need:
        dmg = [champs[a]["dmg"] if a in champs else role_data.damage_of(_display(a)) for a in allies]
        ap = sum("AP" in d for d in dmg)
        ad = sum(d.startswith("AD") for d in dmg)
        need = "ap" if ad > ap else "ad" if ap > ad + 1 else None
    taken = set(enemies) | set(allies)
    rows = sorted(((score(c, enemies, enemy_mid, allies, args.style, need, champs, mu), c)
                   for c in champs if c not in taken), key=lambda x: -x[0][0])
    if unknown:
        print(f"(not in {ROLE} data, only used as name matches: {', '.join(unknown)})")
    if enemy_mid:
        print(f"Enemy {ROLE} assumed: {champs[enemy_mid]['name']}")
    print(f"\nTop {args.top} picks:")
    for (s, why), c in rows[:args.top]:
        print(f"  {s:+5.1f}  {champs[c]['name']:<14} {'; '.join(why) or '-'}")


def main():
    global ROLE
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--role", default=ROLE, help="top | jungle | mid | bot | support")
    sub = p.add_subparsers(dest="cmd", required=True)
    for n in ("vs", "matchups"):
        sp = sub.add_parser(n)
        sp.add_argument("name")
        sp.add_argument("--top", type=int, default=5)
    sp = sub.add_parser("comp")
    sp.add_argument("--enemy", default="")
    sp.add_argument("--ally", default="")
    sp.add_argument("--style", choices=STYLE_WORDS)
    sp.add_argument("--need", choices=["ap", "ad"])
    sp.add_argument("--top", type=int, default=5)
    args = p.parse_args()
    ROLE = role_data.ROLE_ALIASES.get(args.role.lower(), args.role.lower())
    if ROLE not in role_data.ROLES:
        sys.exit(f"Unknown role {args.role}; use one of {', '.join(role_data.ROLES)}")
    champs, mu = load()
    {"vs": cmd_vs, "matchups": cmd_matchups, "comp": cmd_comp}[args.cmd](args, champs, mu)


if __name__ == "__main__":
    main()
