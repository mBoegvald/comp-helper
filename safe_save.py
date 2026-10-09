"""Save a workbook without ever leaving a half-written file behind (stop button, crash, power cut)."""
import os
from pathlib import Path


def save_workbook(wb, path):
    path = Path(path)
    tmp = path.with_name(f".{path.name}.tmp")
    wb.save(tmp)
    try:
        os.replace(tmp, path)
    except PermissionError:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"Could not write {path.name}: close it in Excel and run the update again.")
