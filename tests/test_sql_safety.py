"""SQL is never built from pieces, except at the reviewed places below, which only paste names fixed in the code.

User input must always reach SQLite as a `?` parameter. This test reads the source and fails on any new f-string,
.format() or % that builds SQL, so such a change cannot slip in unnoticed. If one is ever needed, check that it
pastes only names written in the code, and add it here with the reason."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SQL = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|REPLACE)\b")

REVIEWED = {
    ("db.py", "_rename_old_tables"): "table names from RENAMED_TABLES",
    ("db.py", "set_curated_champion"): "column names from CURATED_CHAMP_FIELDS; the field names a user sends are "
    "checked against that list first",
    ("notes.py", "_rows"): "the _FIELDS column list and WHERE clauses written in notes.py, values as ? parameters",
}


def sql_built_from_pieces():
    """(file, function) for every f-string, .format() or % on a string that looks like SQL."""
    found = set()
    for path in sorted(ROOT.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for fn in ast.walk(tree):
            if not isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef | ast.Module):
                continue
            name = getattr(fn, "name", "<module>")
            for node in ast.walk(fn):
                text = None
                if isinstance(node, ast.JoinedStr):  # f"..."
                    text = "".join(v.value for v in node.values if isinstance(v, ast.Constant))
                elif isinstance(node, ast.Call) and getattr(node.func, "attr", None) == "format":
                    if isinstance(node.func.value, ast.Constant) and isinstance(node.func.value.value, str):
                        text = node.func.value.value
                elif (
                    isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod) and isinstance(node.left, ast.Constant)
                ):
                    text = str(node.left.value)
                if text and SQL.search(text):
                    found.add((path.name, name))
    # a module-level walk also sees every function's strings: keep only the innermost function
    return {f for f in found if f[1] != "<module>" or not any(g[0] == f[0] and g[1] != "<module>" for g in found)}


def test_sql_is_only_built_at_the_reviewed_places():
    assert sql_built_from_pieces() == set(REVIEWED)


def test_the_check_finds_a_new_place(tmp_path, monkeypatch):
    """The check itself works: a function that pastes a value into SQL is reported."""
    (tmp_path / "bad.py").write_text(
        'def find(conn, name):\n    conn.execute(f"SELECT * FROM account WHERE username = {name}")\n'
    )
    monkeypatch.setitem(globals(), "ROOT", tmp_path)
    assert sql_built_from_pieces() == {("bad.py", "find")}
