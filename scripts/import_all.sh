#!/bin/bash

export HOST=$JKR_DB_HOST
export PORT=$JKR_DB_PORT
export DB_NAME=$JKR_DB
export USER=$JKR_USER
export PGPASSWORD=$JKR_PASSWORD
export APPDATA=/usr/local/bin/dotenv

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
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv" -nln rakennus ../data/dvv/DVV_rakennukset0.xlsx "R1 rakennus"

# Osoitteet
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv" -nln osoite ../data/dvv/DVV_rakennukset0.xlsx "R3 osoite"

# Omistajat
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv" -nln omistaja ../data/dvv/DVV_rakennukset0.xlsx "R4 omistaja"

# Asukkaat
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv" -nln vanhin ../data/dvv/DVV_rakennukset0.xlsx "R9 huon asukk"

echo "Muunnetaan jkr-muotoon..."
psql -h $HOST -p $PORT -d $DB_NAME -U $USER -v formatted_date="20220128" -f import_dvv.sql

jkr create_dvv_kohteet 28.1.2022 ../data/Perusmaksu.xlsx

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
psql -h $HOST -p $PORT -d $DB_NAME -U $USER -v formatted_date="20240307" -f import_dvv.sql

jkr create_dvv_kohteet 7.3.2024

# # (Vaihe 3) DVV aineisto Huoneistot
# jkr create_dvv_kohteet $day.$month.$year ../data/Huoneistot.xlsx


# # # (Vaihe 4) Luetaan huoneistomäärät
# echo "Luetaan huoneistomäärät..."
# ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$JKR_DB_HOST port=$JKR_DB_PORT dbname=$JKR_DB user=$JKR_USER ACTIVE_SCHEMA=jkr_dvv" -nln huoneistomaara ../data/Huoneistot.xlsx "Huoneistolkm"

# # Päivitetään huoneistomäärät rakennus-tauluun
# echo "Päivitetään huoneistomäärät rakennus-tauluun..."
# psql -h $JKR_DB_HOST -p $JKR_DB_PORT -d $JKR_DB -U $JKR_USER -f update_huoneistomaara.sql

# jkr tiedontuotattaja add LJS "Lahden Seudun Jätehuolto"

# # (Vaihe 5) HAPA aineisto
# # Aja SQL-komento aineiston tuontiin
# CSV_FILE_PATH = ../data/Hapa-kohteet.xlsx

# psql -h $HOST -p $PORT -d $DB_NAME -U $USER -c "\copy hapa_aineisto(kohde_id, rakennus_id, asiakasnumero, osoite, kiinteistotunnus, omistaja, asukas, rakennusluokka, kohdetyyppi) FROM '$CSV_FILE_PATH' DELIMITER ';' CSV HEADER;"

# # Tarkista, onnistuiko tuonti
# if [ $? -eq 0 ]; then
#   echo "HAPA-aineiston tuonti onnistui."
# else
#   echo "HAPA-aineiston tuonti epäonnistui."
# fi