#!/bin/bash
# init_database_container.sh
# Alustaa testikannan kun ajetaan Docker-kontainerissa.
# Kanta ja migraatiot ovat jo valmiina (docker-compose hoitaa ketjun).
# Tämä skripti tuo DVV-testidatan ja postinumerot kantaan.

set -e
export LANG=en_US.UTF-8
export PGCLIENTENCODING=UTF8

# Kontainerissa ympäristömuuttujat ovat jo asetettu docker-composesta
: "${JKR_DB_HOST:?JKR_DB_HOST ei ole asetettu}"
: "${JKR_DB_PORT:?JKR_DB_PORT ei ole asetettu}"
: "${JKR_DB:?JKR_DB ei ole asetettu}"
: "${JKR_USER:?JKR_USER ei ole asetettu}"
: "${JKR_PASSWORD:?JKR_PASSWORD ei ole asetettu}"

export PGPASSWORD="$JKR_PASSWORD"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TESTS_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_DIR="$(cd "$TESTS_DIR/.." && pwd)"

PG_CONN="host=$JKR_DB_HOST port=$JKR_DB_PORT dbname=$JKR_DB user=$JKR_USER"
OGR_DSN="PG:host=$JKR_DB_HOST port=$JKR_DB_PORT dbname=$JKR_DB user=$JKR_USER ACTIVE_SCHEMA=jkr_dvv"

INPUT_FILE="$TESTS_DIR/data/test_data_import/DVV_original.xlsx"

echo "Tuodaan postinumerot ja kunnat..."
psql -h "$JKR_DB_HOST" -p "$JKR_DB_PORT" -d "$JKR_DB" -U "$JKR_USER" \
  -f "$SCRIPT_DIR/import_posti_test.sql"

echo "Tuodaan rakennukset (DVV)..."
ogr2ogr -f PostgreSQL -overwrite -progress \
  "$OGR_DSN" \
  -nln rakennus "$INPUT_FILE" "R1 rakennus"

echo "Tuodaan osoitteet (DVV)..."
ogr2ogr -f PostgreSQL -overwrite -progress \
  "$OGR_DSN" \
  -nln osoite "$INPUT_FILE" "R3 osoite"

echo "Tuodaan omistajat (DVV)..."
ogr2ogr -f PostgreSQL -overwrite -progress \
  "$OGR_DSN" \
  -nln omistaja "$INPUT_FILE" "R4 omistaja"

echo "Tuodaan asukkaat (DVV)..."
ogr2ogr -f PostgreSQL -overwrite -progress \
  "$OGR_DSN" \
  -nln vanhin "$INPUT_FILE" "R9 huon asukk"

echo "Muunnetaan jkr-muotoon..."
psql -h "$JKR_DB_HOST" -p "$JKR_DB_PORT" -d "$JKR_DB" -U "$JKR_USER" \
  -v formatted_date=20220128 -f "$PROJECT_DIR/scripts/import_dvv.sql"

echo "Testikannan alustaminen valmis."
