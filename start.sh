#!/usr/bin/env bash
# Start the Pick Helper web page (Linux/macOS). Opens in your browser; Ctrl+C stops it.
cd "$(dirname "$0")"
python3 -c "import openpyxl" 2>/dev/null || python3 -m pip install --user openpyxl
exec python3 webapp.py "$@"
