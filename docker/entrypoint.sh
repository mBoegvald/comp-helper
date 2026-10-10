#!/bin/sh
# First start: the data volume is empty, so fill it from the copy in the image. Later starts keep what is there (the
# live database with accounts and notes, Reddit downloads, backups) and never overwrite it.
set -eu
if [ ! -f /app/data/pickhelper.db ]; then
  cp /app/seed/pickhelper.db /app/data/pickhelper.db
  echo "first start: database copied into the data volume"
fi
if [ ! -d /app/data/reddit ]; then
  cp -r /app/seed/reddit /app/data/reddit
fi
exec "$@"
