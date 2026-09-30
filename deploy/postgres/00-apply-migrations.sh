#!/bin/sh
set -eu

# The official PostgreSQL image executes files in this directory only on a
# fresh data volume.
#
# The migrations are goose-formatted single files: each carries a
# `-- +goose Up` section followed by a `-- +goose Down` section, and the
# PostgreSQL image would happily run BOTH if the file were piped in whole.
# Apply only the Up section of each migration so a fresh volume is migrated
# exactly like `goose ... up` would do it.
for migration in /mago-migrations/*.sql; do
  echo "Applying ${migration}"
  # Everything after the "-- +goose Down" marker is the rollback path and must
  # NOT be applied on a fresh database.
  sed -n '/^-- +goose Up/,/^-- +goose Down/p' "$migration" \
    | sed 's/^-- +goose Down$//' \
    | psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set ON_ERROR_STOP=1
done
