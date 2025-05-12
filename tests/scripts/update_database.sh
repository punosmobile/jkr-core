#!/bin/bash

set -e  # Exit on error
set -o pipefail

# Use UTF-8 encoding in terminal and Postgres
export LANG=en_US.UTF-8
export PGCLIENTENCODING=UTF8

# Default .env path
DEFAULT_ENV_PATH="../tests/.env.local"
ENV_FILE="${1:-$DEFAULT_ENV_PATH}" # Use first argument or fallback to default

# Check if .env file exists
if [[ ! -f "$ENV_FILE" ]]; then
  echo "❌ Error: .env file not found at $ENV_FILE"
  exit 1
fi

# Load environment variables from .env
echo "📄 Loading environment from $ENV_FILE..."
export $(grep -v '^#' "$ENV_FILE" | xargs)

# Validate required variables
REQUIRED_VARS=(JKR_DB_HOST JKR_TEST_DB_PORT JKR_TEST_DB JKR_USER QGIS_BIN_PATH)
for var in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!var}" ]]; then
    echo "❌ Error: Required variable $var not set in .env file"
    exit 1
  fi
done

# Set Postgres password
export PGPASSWORD="${JKR_PASSWORD}"

# Define input file
INPUT_FILE="./data/test_data_import/DVV_update.xlsx"

echo "🏗️  Importing Rakennukset..."
"${QGIS_BIN_PATH}/ogr2ogr" -f PostgreSQL -overwrite -progress \
  PG:"host=$JKR_DB_HOST port=$JKR_TEST_DB_PORT dbname=$JKR_TEST_DB user=$JKR_USER ACTIVE_SCHEMA=jkr_dvv" \
  -nln rakennus "$INPUT_FILE" "R1 rakennus"

echo "📫 Importing Osoitteet..."
"${QGIS_BIN_PATH}/ogr2ogr" -f PostgreSQL -overwrite -progress \
  PG:"host=$JKR_DB_HOST port=$JKR_TEST_DB_PORT dbname=$JKR_TEST_DB user=$JKR_USER ACTIVE_SCHEMA=jkr_dvv" \
  -nln osoite "$INPUT_FILE" "R3 osoite"

echo "👤 Importing Omistajat..."
"${QGIS_BIN_PATH}/ogr2ogr" -f PostgreSQL -overwrite -progress \
  PG:"host=$JKR_DB_HOST port=$JKR_TEST_DB_PORT dbname=$JKR_TEST_DB user=$JKR_USER ACTIVE_SCHEMA=jkr_dvv" \
  -nln omistaja "$INPUT_FILE" "R4 omistaja"

echo "🏠 Importing Asukkaat..."
"${QGIS_BIN_PATH}/ogr2ogr" -f PostgreSQL -overwrite -progress \
  PG:"host=$JKR_DB_HOST port=$JKR_TEST_DB_PORT dbname=$JKR_TEST_DB user=$JKR_USER ACTIVE_SCHEMA=jkr_dvv" \
  -nln vanhin "$INPUT_FILE" "R9 huon asukk"

echo "🔄 Muunnetaan jkr-muotoon..."
"${QGIS_BIN_PATH}/psql" -h "$JKR_DB_HOST" -p "$JKR_TEST_DB_PORT" -d "$JKR_TEST_DB" -U "$JKR_USER" \
  -v formatted_date=20230131 -f "../scripts/import_dvv.sql"

echo "✅ Done!"