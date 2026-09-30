#!/bin/sh
set -eu

# The official PostgreSQL image executes files in this directory only on a
# fresh data volume. Apply only goose "up" migrations; mounting the whole
# migrations directory directly would also execute every "down" migration.
for migration in /mago-migrations/*.up.sql; do
  echo "Applying ${migration}"
  psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --set ON_ERROR_STOP=1 --file "$migration"
done
