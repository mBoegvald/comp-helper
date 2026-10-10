#!/usr/bin/env python3
"""Start webapp.py on a fresh copy of the fixture database, for the browser tests in frontend/e2e.

  python tests/e2e_server.py --port 8811 [webapp.py options]

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

import db  # noqa: E402
import webapp  # noqa: E402

webapp.REDDIT_DIR = TMP / "reddit"  # empty
conn = db.connect()
fixture_db.seed(conn)
conn.close()
sys.argv = ["webapp.py", "--no-browser", *sys.argv[1:]]
webapp.main()
