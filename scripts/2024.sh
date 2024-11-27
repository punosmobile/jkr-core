#!/bin/bash
rm *.log

export HOST=$JKR_DB_HOST
export PORT=$JKR_DB_PORT
export DB_NAME=$JKR_DB
export USER=$JKR_USER
export PGPASSWORD=$JKR_PASSWORD
export APPDATA=/usr/local/bin/dotenv

echo "Tuodaan DVV 2024 aineisto..."
# DVV-aineisto 2024
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv" -nln rakennus ../data/DVV/DVV-aineisto_2024.xlsx "R1 rakennus"
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv" -nln osoite ../data/DVV/DVV-aineisto_2024.xlsx "R3 osoite" 
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv" -nln omistaja ../data/DVV/DVV-aineisto_2024.xlsx "R4 omistaja"
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv" -nln vanhin ../data/DVV/DVV-aineisto_2024.xlsx "R9 huon asukk"

echo "Muunnetaan jkr-muotoon..."
psql -h $HOST -p $PORT -d $DB_NAME -U $USER -v formatted_date="20240127" -f import_dvv.sql

# Päivitetään huoneistomäärät
echo "Tuodaan huoneistomäärät..."
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER ACTIVE_SCHEMA=jkr_dvv" -nln huoneistomaara ../data/Huoneistomäärät_2024.xlsx "Huoneistolkm"
psql -h $HOST -p $PORT -d $DB_NAME -U $USER -f update_huoneistomaara.sql

# Tuodaan HAPA-aineisto
echo "Tuodaan HAPA-aineisto 2024..."
export CSV_FILE_PATH='../data/Hapa-kohteet_aineisto_2024.csv'
psql -h $HOST -p $PORT -d $DB_NAME -U $USER -c "\copy jkr.hapa_aineisto(rakennus_id_tunnus, kohde_tunnus, sijaintikunta, asiakasnro, rakennus_id_tunnus2, katunimi_fi, talon_numero, postinumero, postitoimipaikka_fi, kohdetyyppi) FROM '${CSV_FILE_PATH}' WITH (FORMAT csv, DELIMITER ';', HEADER true, ENCODING 'UTF8', NULL '');"

# Luodaan kohteet perusmaksuaineistosta (Perusmaksuaineistoa ei lueta kuin alussa)
echo "Luodaan kohteet..."
jkr create_dvv_kohteet 28.1.2024

# Päivitetään velvoitteet
echo "Ajetaan velvoitepäivitys..."
psql -h $HOST -p $PORT -d $DB_NAME -U $USER -c "SELECT jkr.update_velvoitteet();"

# Tuodaan päätökset ja ilmoitukset
echo "Tuodaan päätökset ja ilmoitukset 2024..."
# Päätökset ja ilmoitukset Q1 2024
jkr import_paatokset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2024/Q1/Paatokset_2024Q1.xlsx
jkr import_ilmoitukset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2024/Q1/Kompostointi-ilmoitus_2024Q1.xlsx
jkr import_lopetusilmoitukset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2024/Q1/Kompostoinnin_lopettaminen_2024Q1.xlsx
jkr import --luo_uudet ../data/Kuljetustiedot/Kuljetustiedot_2024/Q1 LSJ 1.1.2024 31.3.2024
psql -h $HOST -p $PORT -d $DB_NAME -U $USER -c "select jkr.tallenna_velvoite_status('2024-03-31');"

# Q2 2024
jkr import_paatokset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2024/Q2/Paatokset_2024Q2.xlsx
jkr import_ilmoitukset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2024/Q2/Kompostointi-ilmoitus_2024Q2.xlsx
jkr import_lopetusilmoitukset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2024/Q2/Kompostoinnin_lopettaminen_2024Q2.xlsx
jkr import --luo_uudet ../data/Kuljetustiedot/Kuljetustiedot_2024/Q2 LSJ 1.4.2024 30.6.2024
psql -h $HOST -p $PORT -d $DB_NAME -U $USER -c "select jkr.tallenna_velvoite_status('2024-06-30');"

# Q3 2024
jkr import_paatokset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2024/Q3/Paatokset_2024Q3.xlsx
jkr import_ilmoitukset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2024/Q3/Kompostointi-ilmoitus_2024Q3.xlsx
jkr import_lopetusilmoitukset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2024/Q3/Kompostoinnin_lopettaminen_2024Q3.xlsx
jkr import --luo_uudet ../data/Kuljetustiedot/Kuljetustiedot_2024/Q3 LSJ 1.7.2024 30.9.2024
psql -h $HOST -p $PORT -d $DB_NAME -U $USER -c "select jkr.tallenna_velvoite_status('2024-09-30');"

# Q4 2024  
jkr import_paatokset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2024/Q4/Paatokset_2024Q4.xlsx
jkr import_ilmoitukset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2024/Q4/Kompostointi-ilmoitus_2024Q4.xlsx
jkr import_lopetusilmoitukset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2024/Q4/Kompostoinnin_lopettaminen_2024Q4.xlsx
jkr import --luo_uudet ../data/Kuljetustiedot/Kuljetustiedot_2024/Q4 LSJ 1.10.2024 31.12.2024
psql -h $HOST -p $PORT -d $DB_NAME -U $USER -c "select jkr.tallenna_velvoite_status('2024-12-31');"
