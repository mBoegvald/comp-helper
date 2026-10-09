#!/usr/bin/env bash
# Kept so old commands still work. The real pipeline is update.py (works on Windows too):
#   ./run_all.sh [all|lolalytics|reddit|comments|tips]   ==   python3 update.py [stage]
#   nohup ./run_all.sh reddit >/dev/null 2>&1 &          # background run; progress in logs/update.log
cd "$(dirname "$0")" && exec python3 update.py "$@"
