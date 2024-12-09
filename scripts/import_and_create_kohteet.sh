#!/bin/bash
set -e  # Lopeta skripti, jos tapahtuu virhe


# Tarkistetaan onko tarvittavat muuttujat asetettu
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


export PGPASSWORD=$JKR_PASSWORD

# Tarkistetaan, että dvv-aineisto on syötetty
if [ -z "$1" ]; then
    echo "Anna dvv-aineiston tiedostopolku."
    exit 1
fi

# Tarkistetaan, että poimintapäivämäärä annettu
if [ -z "$2" ]; then
    echo "Anna dvv-aineiston poimintapäivämäärä parametrina muodossa P.K.V"
    exit 2
fi

# Asetetaan parametrit muuttujiksi
DVV="$1"
POIMINTAPVM="$2"

# Muutetaan poimintapäivämäärä muotoon VVVVKKPP
day=$(echo $POIMINTAPVM | cut -d'.' -f1)
month=$(echo $POIMINTAPVM | cut -d'.' -f2)
year=$(echo $POIMINTAPVM | cut -d'.' -f3)

# Lisätään tarvittaessa päiville ja kuukausille 0 eteen
if [ "$day" -lt 10 ]; then
    day="0$day"
fi
if [ "$month" -lt 10 ]; then
    month="0$month"
fi

formatted_date="${year}${month}${day}"

# Vaihdetaan terminaalin code page UTF-8:ksi
export LANG="fi_FI.UTF-8"
export LC_ALL="fi_FI.UTF-8"
export PGCLIENTENCODING="UTF8"


echo "Rakennukset"
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$JKR_DB_HOST port=$JKR_DB_PORT dbname=$JKR_DB user=$JKR_USER ACTIVE_SCHEMA=jkr_dvv" -nln rakennus $DVV "R1 rakennus"

echo "Osoitteet"
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$JKR_DB_HOST port=$JKR_DB_PORT dbname=$JKR_DB user=$JKR_USER ACTIVE_SCHEMA=jkr_dvv" -nln osoite $DVV "R3 osoite"

echo "Omistajat"
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$JKR_DB_HOST port=$JKR_DB_PORT dbname=$JKR_DB user=$JKR_USER ACTIVE_SCHEMA=jkr_dvv" -nln omistaja $DVV "R4 omistaja"

echo "Asukkaat"
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$JKR_DB_HOST port=$JKR_DB_PORT dbname=$JKR_DB user=$JKR_USER ACTIVE_SCHEMA=jkr_dvv" -nln vanhin $DVV "R9 huon asukk"

echo "Muunnetaan jkr-muotoon..."
psql -h $JKR_DB_HOST -p $JKR_DB_PORT -d $JKR_DB -U $JKR_USER -v formatted_date="$formatted_date" -f import_dvv.sql
