#!/usr/bin/env python3
"""Start webapp.py on a fresh copy of the fixture database, for the browser tests in frontend/e2e.

  python tests/e2e_server.py --port 8811 [webapp.py options]
  python tests/e2e_server.py --admin boss:password --port 8812 --hosted --insecure-cookies

Each start builds a new database in a temp folder and uses no Reddit files, so the tests see the same known
numbers every run and never touch data/pickhelper.db.
"""

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TMP = Path(tempfile.mkdtemp(prefix="pickhelper-e2e-"))
os.environ["PICKHELPER_DB"] = str(TMP / "e2e.db")  # db.py reads it on import
sys.path[:0] = [str(ROOT), str(Path(__file__).resolve().parent)]

import fixture_db  # noqa: E402

import auth  # noqa: E402
import db  # noqa: E402
import webapp  # noqa: E402

webapp.REDDIT_DIR = TMP / "reddit"  # empty
args = sys.argv[1:]
admin = None
if "--admin" in args:  # NAME:PASSWORD for a hosted-mode admin account
    i = args.index("--admin")
    admin = args[i + 1].split(":", 1)
    del args[i : i + 2]
# the browser tests sign up and in many times from one address; the limits themselves are tested in pytest
auth.LIMITS = {"login": (10_000, 900), "signup": (10_000, 3600)}

conn = db.connect()
fixture_db.seed(conn)
if admin:
    auth.create_account(conn, admin[0], admin[1], role="admin")
conn.close()
sys.argv = ["webapp.py", "--no-browser", *args]
webapp.main()
