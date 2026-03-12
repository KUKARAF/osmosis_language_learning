#!/bin/bash
# Reset the SQLite database (delete and recreate via app init)
cd "$(dirname "$0")/../backend" || exit 1
rm -f osmosis.db osmosis.db-journal osmosis.db-wal osmosis.db-shm
echo "Database deleted. It will be recreated on next server start."
