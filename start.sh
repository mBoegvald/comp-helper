#!/usr/bin/env bash
# Start the Pick Helper web page (Linux/macOS). Opens in your browser; Ctrl+C stops it.
cd "$(dirname "$0")"
exec python3 webapp.py "$@"
