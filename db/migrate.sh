#!/bin/sh
# Entrypoint of the migration image. Builds the Flyway connection from the same
# JKR_* variables the backend uses. Without arguments it runs migrate only when
# there are pending migrations, so running it again does not rerun
# afterMigrate.sql. Arguments are passed to Flyway as is, e.g. "info" or "repair".
#
#   JKR_DB_HOST, JKR_DB_PORT (default 5432), JKR_DB, JKR_USER, JKR_PASSWORD
#   JKR_DB_OWNER  optional: role that owns the database objects. Flyway runs
#                 SET ROLE to it, so new objects get the same owner as the old ones.
set -eu

: "${JKR_DB_HOST:?JKR_DB_HOST missing}" "${JKR_DB:?JKR_DB missing}"
: "${JKR_USER:?JKR_USER missing}" "${JKR_PASSWORD:?JKR_PASSWORD missing}"
export FLYWAY_URL="jdbc:postgresql://$JKR_DB_HOST:${JKR_DB_PORT:-5432}/$JKR_DB"
export FLYWAY_USER="$JKR_USER"
export FLYWAY_PASSWORD="$JKR_PASSWORD"
[ -z "${JKR_DB_OWNER:-}" ] || export FLYWAY_INIT_SQL="SET ROLE $JKR_DB_OWNER"

if [ "$#" -gt 0 ]; then
  exec flyway "$@"
fi

info=$(flyway info -outputType=json)
pending=$(printf '%s' "$info" | grep -o '"state" *: *"Pending"' | wc -l | tr -d ' ')
if [ "$pending" -eq 0 ]; then
  echo "No pending migrations."
  exit 0
fi
echo "$pending pending migration(s), running migrate."
exec flyway migrate
