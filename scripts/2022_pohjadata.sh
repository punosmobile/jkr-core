#!/bin/bash
rm *.log

export HOST=$JKR_DB_HOST
export PORT=$JKR_DB_PORT
export DB_NAME=$JKR_DB
export USER=$JKR_USER
export PGPASSWORD=$JKR_PASSWORD
export APPDATA=/usr/local/bin/dotenv


# Tarkista että tiedontuottaja on olemassa
jkr tiedontuottaja list | grep -q "LSJ" || \
jkr tiedontuottaja add LSJ "Lahden Seudun Jätehuolto"

# (Vaihe 1) Taajamarajaukset
sh import_taajama.sh 2020-01-01

# (Vaihe 2) Kunnat ja postinumerot
# Kunnat ja postinumerot on tuotava tietokantaan ennen dvv-aineiston tuontia
psql -h $HOST -p $PORT -d $DB_NAME -U $USER -f import_posti.sql


# (Vaihe 3) DVV aineisto 2022
# Rakennukset
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv" -nln rakennus ../data/DVV/DVV-aineisto_2022.xlsx "R1 rakennus"

# Osoitteet
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv" -nln osoite ../data/DVV/DVV-aineisto_2022.xlsx "R3 osoite"

# Omistajat
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv" -nln omistaja ../data/DVV/DVV-aineisto_2022.xlsx "R4 omistaja"

# Asukkaat
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv" -nln vanhin ../data/DVV/DVV-aineisto_2022.xlsx "R9 huon asukk"

echo "Muunnetaan jkr-muotoon..."
psql -h $HOST -p $PORT -d $DB_NAME -U $USER -v formatted_date="20220128" -f import_dvv.sql

# (Vaihe 4) Päivitetään huoneistomäärä
echo "Luetaan huoneistomäärät..."
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$JKR_DB_HOST port=$JKR_DB_PORT dbname=$JKR_DB user=$JKR_USER ACTIVE_SCHEMA=jkr_dvv" -nln huoneistomaara ../data/Huoneistomäärät_2022.xlsx "Huoneistolkm"

# Päivitetään huoneistomäärät rakennus-tauluun
echo "Päivitetään huoneistomäärät rakennus-tauluun..."
psql -h $JKR_DB_HOST -p $JKR_DB_PORT -d $JKR_DB -U $JKR_USER -f update_huoneistomaara.sql


# (Vaihe 5) Luetaan Hapa
echo "Tuodaan Hapa-aineisto..."
export CSV_FILE_PATH='../data/Hapa-kohteet_aineisto_2022.csv'

# (Vaihe 3) Luodaan kohteet perusmaksuaineistosta
echo "Luetaan Perusmaksuaineisto..."
jkr create_dvv_kohteet 28.1.2022 ../data/Perusmaksuaineisto.xlsx


# Tarkista että CSV-tiedosto on olemassa
if [ ! -f "$CSV_FILE_PATH" ]; then
    echo "Virhe: Tiedostoa $CSV_FILE_PATH ei löydy"
    exit 1
fi

# Tuo data tietokantaan
psql -h $HOST -p $PORT -d $DB_NAME -U $USER -c "\copy jkr.hapa_aineisto(rakennus_id_tunnus, kohde_tunnus, sijaintikunta, asiakasnro, rakennus_id_tunnus2, katunimi_fi, talon_numero, postinumero, postitoimipaikka_fi, kohdetyyppi) FROM '${CSV_FILE_PATH}' WITH (FORMAT csv, DELIMITER ';', HEADER true, ENCODING 'UTF8', NULL '');"

# Tarkista tuonnin tulos
if [ $? -eq 0 ]; then
    echo "HAPA-aineiston tuonti onnistui."
else
    echo "HAPA-aineiston tuonti epäonnistui."
fi

# (Vaihe 6) Velvoiteajo
echo "Velvoiteajo..."
psql -h $HOST -p $PORT -d $DB_NAME -U $USER -c "SELECT jkr.update_velvoitteet();"

echo "Valmis"