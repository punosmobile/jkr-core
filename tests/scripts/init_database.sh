#!/bin/bash

set -e
set -o pipefail

# === CONFIG ===
DEFAULT_ENV_PATH="../tests/.env.local"
ENV_FILE="${1:-$DEFAULT_ENV_PATH}"  # Use first argument or fallback to default

echo "📄 Using .env file: $ENV_FILE"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "❌ Error: .env file not found at $ENV_FILE"
  exit 1
fi

# === Load environment variables ===
export $(grep -v '^#' "$ENV_FILE" | xargs)

REQUIRED_VARS=(JKR_DB_HOST JKR_TEST_DB_PORT JKR_TEST_DB JKR_USER QGIS_BIN_PATH)
for var in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!var}" ]]; then
    echo "❌ Error: Required variable $var is not set in $ENV_FILE"
    exit 1
  fi
done

export PGPASSWORD="${JKR_PASSWORD}"

# === Docker setup ===
echo "🧹 Cleaning up existing containers..."
docker stop jkr_test_database || true
docker rm jkr_test_database || true
docker volume rm jkr-core_postgis-data-test || true

echo "🐳 Starting test database container..."
docker compose --env-file "$ENV_FILE" -f ../dev.docker-compose.yml up -d db_test

echo "🛠️ Running Flyway migrations..."
docker compose --env-file "$ENV_FILE" -f ../dev.docker-compose.yml run --rm flyway_test migrate

# === Data import steps ===
echo "📥 Importing Kunnat ja postinumerot..."
"${QGIS_BIN_PATH}/psql" -h "$JKR_DB_HOST" -p "$JKR_TEST_DB_PORT" -d "$JKR_TEST_DB" -U "$JKR_USER" -f "./scripts/import_posti_test.sql"

declare -A TABLES=(
  [rakennus]="R1 rakennus"
  [osoite]="R3 osoite"
  [omistaja]="R4 omistaja"
  [vanhin]="R9 huon asukk"
)

for table in "${!TABLES[@]}"; do
  echo "📄 Importing: $table (${TABLES[$table]})"
  "${QGIS_BIN_PATH}/ogr2ogr" -f PostgreSQL -overwrite -progress \
    PG:"host=$JKR_DB_HOST port=$JKR_TEST_DB_PORT dbname=$JKR_TEST_DB user=$JKR_USER ACTIVE_SCHEMA=jkr_dvv" \
    -nln "$table" "./data/test_data_import/DVV_original.xlsx" "${TABLES[$table]}"
done

echo "🧩 Finalizing with import_dvv.sql..."
"${QGIS_BIN_PATH}/psql" -h "$JKR_DB_HOST" -p "$JKR_TEST_DB_PORT" -d "$JKR_TEST_DB" -U "$JKR_USER" \
  -v formatted_date=20220128 -f "../scripts/import_dvv.sql"

echo "✅ Done!"