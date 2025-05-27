#!/bin/bash

export HOST=db
export PORT=$JKR_DB_PORT
export DB_NAME=$JKR_DB
export USER=$JKR_USER
export PGPASSWORD=$JKR_PASSWORD
export APPDATA=/$HOME/.config/jkr/.env

# Haetaan kuluva päivä ja muotoillaan
formatted_date=$(date +"%Y%m%d")
day=$(date +"%d")
month=$(date +"%m")
year=$(date +"%Y")


# (Vaihe 1) Kunnat ja postinumerot
# Kunnat ja postinumerot on tuotava tietokantaan ennen dvv-aineiston tuontia
psql -h $HOST -p $PORT -d $DB_NAME -U $USER -f import_posti.sql




# (Vaihe 2) DVV aineisto Tulostetaan käytettävä päivämäärä
echo "Käytetään poimintapäivämäärää: $formatted_date"

# Rakennukset
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv" -nln rakennus ../data/dvv/DVV_rakennukset.xlsx "R1 rakennus"

# Osoitteet
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv" -nln osoite ../data/dvv/DVV_rakennukset.xlsx "R3 osoite"

# Omistajat
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv" -nln omistaja ../data/dvv/DVV_rakennukset.xlsx "R4 omistaja"

# Asukkaat
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv" -nln vanhin ../data/dvv/DVV_rakennukset.xlsx "R9 huon asukk"

# psql -h $HOST -p $PORT -d $DB_NAME -U $USER -f import_dvv.sql
echo "Muunnetaan jkr-muotoon..."
psql -h $HOST -p $PORT -d $DB_NAME -U $USER -v formatted_date="$formatted_date" -f import_dvv.sql



# (Vaihe 3) DVV aineisto Huoneistot
jkr create_dvv_kohteet $day.$month.$year ../data/Huoneistot.xlsx