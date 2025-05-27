#!/bin/bash

# Vaihdetaan terminaalin koodisivu UTF-8:ksi (Linuxissä ei tarvita CHCP-komentoa)
export LANG=en_US.UTF-8
export PGCLIENTENCODING=UTF8

# Tarkistetaan .env tiedosto
ENV_FILE="$HOME/.config/jkr/.env"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Virhe: .env-tiedostoa ei löytynyt sijainnista $ENV_FILE"
  exit 1
fi

# Ladataan muuttujat .env tiedostosta
export $(grep -v '^#' "$ENV_FILE" | xargs)

# Tarkistetaan onko tarvittavat muuttujat asetettu
REQUIRED_VARS=(JKR_DB_HOST JKR_TEST_DB_PORT JKR_TEST_DB JKR_USER QGIS_BIN_PATH)
for var in "${REQUIRED_VARS[@]}"; do
  if [[ -z "${!var}" ]]; then
    echo "Virhe: $var ei ole asetettu .env-tiedostossa"
    exit 1
  fi
done

# Asetetaan Postgresin salasana
export PGPASSWORD="$JKR_PASSWORD"

# Luodaan kanta alusta Dockerilla
echo "Pysäytetään ja poistetaan aiemmat kontit ja volyymit..."
docker stop jkr_test_database || true
docker rm jkr_test_database || true
docker volume rm jkr-core_postgis-data-test || true

echo "Käynnistetään testikanta Dockerilla..."
docker compose --env-file "$ENV_FILE" -f ../docker-compose.yml up -d db_test

echo "Suoritetaan Flyway-migraatiot..."
docker compose --env-file "$ENV_FILE" -f ../docker-compose.yml run --rm flyway_test migrate

# Tuodaan kunnilla ja postinumeroilla varustetut tiedot kantaan
echo "Kunnat ja postinumerot"
"$QGIS_BIN_PATH/psql" -h "$JKR_DB_HOST" -p "$JKR_TEST_DB_PORT" -d "$JKR_TEST_DB" -U "$JKR_USER" -f "./scripts/import_posti_test.sql"

INPUT_FILE="./data/test_data_import/DVV_original.xlsx"

# Rakennukset
echo "Rakennukset"
"$QGIS_BIN_PATH/ogr2ogr" -f PostgreSQL -overwrite -progress \
  PG:"host=$JKR_DB_HOST port=$JKR_TEST_DB_PORT dbname=$JKR_TEST_DB user=$JKR_USER ACTIVE_SCHEMA=jkr_dvv" \
  -nln rakennus "$INPUT_FILE" "R1 rakennus"

# Osoitteet
echo "Osoitteet"
"$QGIS_BIN_PATH/ogr2ogr" -f PostgreSQL -overwrite -progress \
  PG:"host=$JKR_DB_HOST port=$JKR_TEST_DB_PORT dbname=$JKR_TEST_DB user=$JKR_USER ACTIVE_SCHEMA=jkr_dvv" \
  -nln osoite "$INPUT_FILE" "R3 osoite"

# Omistajat
echo "Omistajat"
"$QGIS_BIN_PATH/ogr2ogr" -f PostgreSQL -overwrite -progress \
  PG:"host=$JKR_DB_HOST port=$JKR_TEST_DB_PORT dbname=$JKR_TEST_DB user=$JKR_USER ACTIVE_SCHEMA=jkr_dvv" \
  -nln omistaja "$INPUT_FILE" "R4 omistaja"

# Asukkaat
echo "Asukkaat"
"$QGIS_BIN_PATH/ogr2ogr" -f PostgreSQL -overwrite -progress \
  PG:"host=$JKR_DB_HOST port=$JKR_TEST_DB_PORT dbname=$JKR_TEST_DB user=$JKR_USER ACTIVE_SCHEMA=jkr_dvv" \
  -nln vanhin "$INPUT_FILE" "R9 huon asukk"

# Muunnetaan jkr-muotoon
echo "Muunnetaan jkr-muotoon..."
"$QGIS_BIN_PATH/psql" -h "$JKR_DB_HOST" -p "$JKR_TEST_DB_PORT" -d "$JKR_TEST_DB" -U "$JKR_USER" \
  -v formatted_date=20220128 -f "../scripts/import_dvv.sql"

echo "Testikannan alustaminen valmis."