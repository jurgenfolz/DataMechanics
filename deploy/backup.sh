#!/usr/bin/env bash
# Dump the database from its Docker container; keep the newest 14 dumps.
set -euo pipefail

cd /srv/datamechanics
set -a; source .env; set +a
mkdir -p backups
file="backups/datamechanics-$(date +%Y-%m-%d-%H%M).dump"
docker exec datamechanics-db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom > "$file"
chmod 600 "$file"
ls -1t backups/*.dump | tail -n +15 | xargs -r rm --
echo "Backed up to $file"
