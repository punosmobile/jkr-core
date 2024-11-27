#!/bin/bash
set -e  # Lopeta skripti, jos tapahtuu virhe

# Tarkistetaan, että on annettu polku xlsx-tiedostoon
if [ -z "$1" ]; then
    echo "Anna polku xlsx-tiedostoon, joka sisältää huoneistomäärät."
    exit 1
fi

# Vaihdetaan terminaalin koodaus UTF-8:ksi
export LANG="fi_FI.UTF-8"
export LC_ALL="fi_FI.UTF-8"
export PGCLIENTENCODING="UTF8"

# # Tarkistetaan .env-tiedosto
# if [ ! -f "$HOME/.jkr/.env" ]; then
#     echo "Error: .env file not found at $HOME/.jkr/.env"
#     exit 1
# fi

# Ladataan muuttujat .env-tiedostosta
export $(grep -v '^#' $HOME/.jkr/.env | xargs)

# Tarkistetaan, onko tarvittavat muuttujat asetettu
if [ -z "$JKR_DB_HOST" ]; then
    echo "Error: HOST variable not set in .env file"
    exit 1
fi
if [ -z "$JKR_DB_PORT" ]; then
    echo "Error: PORT variable not set in .env file"
    exit 1
fi
if [ -z "$JKR_DB" ]; then
    echo "Error: DB_NAME variable not set in .env file"
    exit 1
fi
if [ -z "$JKR_USER" ]; then
    echo "Error: USER variable not set in .env file"
    exit 1
fi
# if [ -z "$QGIS_BIN_PATH" ]; then
#     echo "Error: QGIS_BIN_PATH variable not set in .env file"
#     exit 1
# fi

export PGPASSWORD=$JKR_PASSWORD

# Asetetaan xlsx-tiedoston polku
EXCEL_FILE="$1"

# Luetaan huoneistomäärät
echo "Luetaan huoneistomäärät..."
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$JKR_DB_HOST port=$JKR_DB_PORT dbname=$JKR_DB user=$JKR_USER ACTIVE_SCHEMA=jkr_dvv" -nln huoneistomaara "$EXCEL_FILE" "Huoneistolkm"

# Päivitetään huoneistomäärät rakennus-tauluun
echo "Päivitetään huoneistomäärät rakennus-tauluun..."
psql -h $JKR_DB_HOST -p $JKR_DB_PORT -d $JKR_DB -U $JKR_USER -f update_huoneistomaara.sql
