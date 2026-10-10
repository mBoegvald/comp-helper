#!/usr/bin/env python3
"""Data refresh for the pick helper. Works the same on Windows and Linux. Safe to rerun: finished Reddit
champions are skipped, so an interrupted run just continues where it stopped.

  python update.py              # everything, all roles: win rates -> Reddit -> tips   (Reddit part can take hours)
  python update.py lolalytics   # only win rates for all roles (~5 min). Do this after each patch.
  python update.py reddit       # only Reddit threads for champions that are missing (1 request per minute)
  python update.py comments     # replies to the best threads per champion (slow, run overnight)
  python update.py tips         # rebuild Reddit tips from data/reddit

Options (or environment variables):
  --roles "top mid"     ROLES                    limit to some roles (default: mid top jungle bot support)
  --delay 60            REDDIT_DELAY             seconds between Reddit requests (Reddit allows about 1 per minute)
  --threads 12          REDDIT_COMMENT_THREADS   threads per champion for the comments stage

Everything is saved in data/pickhelper.db; each run first makes that day's copy in data/backups.
Progress goes to logs/update.log. Only one update runs at a time.
"""
import argparse
import datetime as dt
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG = HERE / "logs" / "update.log"
LOCK = HERE / "logs" / "update.lock"
BACKUPS = HERE / "data" / "backups"
BACKUPS_KEPT = 14
STAGES = ("all", "lolalytics", "reddit", "comments", "tips")


def log(msg: str):
    line = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


class Lock:
    """Exclusive lock on logs/update.lock. The OS drops it when the process exits, even after a crash.
    The PID of the running update is stored at the start of the file; on Windows the lock covers a byte far
    past it, because Windows byte locks also block other processes from reading the locked bytes."""
    OFFSET = 4096

    def __init__(self, path: Path):
        self.path, self.f = path, None

    def acquire(self, write_pid: bool = True) -> bool:
        self.f = self.path.open("a+")
        try:
            if os.name == "nt":
                import msvcrt
                self.f.seek(self.OFFSET)
                msvcrt.locking(self.f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.f.close()
            self.f = None
            return False
        if write_pid:
            self.f.seek(0); self.f.truncate(); self.f.write(str(os.getpid())); self.f.flush()
        return True

    def release(self):
        if not self.f:
            return
        try:
            if os.name == "nt":
                import msvcrt
                self.f.seek(self.OFFSET)
                msvcrt.locking(self.f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.f.fileno(), fcntl.LOCK_UN)
        finally:
            self.f.close()
            self.f = None


def is_running() -> bool:
    """True if another update holds the lock (used by the web page). Never touches the stored PID."""
    if not LOCK.exists():
        return False
    lk = Lock(LOCK)
    if lk.acquire(write_pid=False):
        lk.release()
        return False
    return True


def running_pid():
    try:
        return int(LOCK.read_text(encoding="ascii", errors="ignore").strip()[:12] or 0) or None
    except (OSError, ValueError):
        return None


def run(args, what: str) -> bool:
    """Run one of our scripts with the current Python, output appended to the log."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    with LOG.open("a", encoding="utf-8") as out:
        rc = subprocess.call([sys.executable, "-u", *args], cwd=HERE, stdout=out, stderr=subprocess.STDOUT, env=env)
    if rc != 0:
        log(f"{what} FAILED (exit {rc}), see {LOG.name}")
    return rc == 0


def backup():
    """One copy of the database per day in data/backups (hand edits live there), the last BACKUPS_KEPT kept."""
    import db
    dest = BACKUPS / f"{dt.date.today()}_{db.PATH.name}"
    if db.PATH.exists() and not dest.exists():
        db.backup(dest)
        for old in sorted(BACKUPS.glob(f"*_{db.PATH.name}"))[:-BACKUPS_KEPT]:
            old.unlink()


def reddit_champions(roles) -> str:
    """Union of the roles' champion pools."""
    import db
    conn = db.connect()
    return ",".join(sorted({c for r in roles for c in db.pool(conn, r)}))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("stage", nargs="?", default="all", choices=STAGES)
    p.add_argument("--roles", default=os.environ.get("ROLES", "mid top jungle bot support"))
    p.add_argument("--delay", type=float, default=float(os.environ.get("REDDIT_DELAY", 60)))
    p.add_argument("--threads", type=int, default=int(os.environ.get("REDDIT_COMMENT_THREADS", 12)))
    a = p.parse_args(argv)
    os.chdir(HERE)
    sys.path.insert(0, str(HERE))
    (HERE / "logs").mkdir(exist_ok=True)
    (HERE / "data").mkdir(exist_ok=True)
    import role_data
    roles = [role_data.ROLE_ALIASES.get(r, r) for r in a.roles.replace(",", " ").split()]
    bad = [r for r in roles if r not in role_data.ROLES]
    if bad:
        sys.exit(f"unknown role(s) {', '.join(bad)}; use {', '.join(role_data.ROLES)}")

    lock = Lock(LOCK)
    if not lock.acquire():
        log("another update is already running, exiting")
        return 1
    what = a.stage
    log(f"started ({what}) for roles: {' '.join(roles)}")

    backup()
    if what in ("all", "lolalytics"):
        for r in roles:
            log(f"lolalytics: fetching {r}")
            if run(["build_role.py", r], f"lolalytics {r}"):
                log(f"lolalytics: {r} done")

    if what in ("all", "reddit", "comments"):
        champs = reddit_champions(roles)
        n = len(champs.split(",")) if champs else 0
        extra = []
        if what == "comments":
            extra = ["--comments", "40", "--max-comment-threads", str(a.threads)]
            log(f"reddit: comments for the {a.threads} best threads of {n} champions, {a.delay:.0f}s between requests")
        else:
            log(f"reddit: matchup threads for {n} champions, {a.delay:.0f}s between requests (finished ones are skipped)")
        if run(["fetch_reddit_rss.py", "--champs", champs, "--out", "data/reddit", "--delay", str(a.delay), *extra], "reddit"):
            log(f"reddit: done, {len(list((HERE / 'data' / 'reddit').glob('*.json')))} champion files in data/reddit")

    if what in ("all", "reddit", "comments", "tips"):
        if run(["extract_tips.py", "build", "--reddit", "data/reddit"], "tips build"):
            log("tips: Reddit tips rebuilt")

    log(f"finished ({what})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
