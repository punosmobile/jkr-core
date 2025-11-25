#!/bin/bash

# Exit immediately on error
set -e

# Check if environment file parameter is provided
if [ -z "$1" ]; then
  echo "Usage: $0 path_to_env_file"
  exit 1
fi

# Load environment variables from the specified .env file
set -o allexport
source "$1"
set +o allexport

# Define the current directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

## Uncomment these only if you think there are no serious problems with migration
#docker run --rm \
#  --network host \
#  -v "${SCRIPT_DIR}/db/migrations":/flyway/sql \
#  -v "${SCRIPT_DIR}/db/flyway.conf":/flyway/conf/flyway.conf \
#  flyway/flyway \
#  -url="jdbc:postgresql://${JKR_DB_HOST}:${JKR_DB_PORT}/${JKR_DB}" \
#  -user="${JKR_USER}" \
#  -password="${JKR_PASSWORD}" \
#  repair

# Run migrations
docker run --rm \
  --network host \
  -v "${SCRIPT_DIR}/db/migrations":/flyway/sql \
  -v "${SCRIPT_DIR}/db/flyway.conf":/flyway/conf/flyway.conf \
  flyway/flyway \
  -url="jdbc:postgresql://${JKR_DB_HOST}:${JKR_DB_PORT}/${JKR_DB}" \
  -user="${JKR_USER}" \
  -password="${JKR_PASSWORD}" \
  migrate \
  -outOfOrder=true
# -outOfOrder allows migrations to be run if there are some skipped migration files

# Show migration status
docker run --rm \
  --network host \
  -v "${SCRIPT_DIR}/db/migrations":/flyway/sql \
  -v "${SCRIPT_DIR}/db/flyway.conf":/flyway/conf/flyway.conf \
  flyway/flyway \
  -url="jdbc:postgresql://${JKR_DB_HOST}:${JKR_DB_PORT}/${JKR_DB}" \
  -user="${JKR_USER}" \
  -password="${JKR_PASSWORD}" \
  info