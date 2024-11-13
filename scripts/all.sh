#!/bin/bash
set -e # Lopettaa suorituksen virhetilanteessa

# Tarkista pakolliset ympäristömuuttujat
if [ -z "$JKR_DB_HOST" ] || [ -z "$JKR_DB_PORT" ] || [ -z "$JKR_DB" ] || [ -z "$JKR_USER" ] || [ -z "$JKR_PASSWORD" ]; then
    echo "Virhe: Määrittele ensin ympäristömuuttujat JKR_DB_HOST, JKR_DB_PORT, JKR_DB, JKR_USER ja JKR_PASSWORD"
    exit 1
fi

# Aseta tietokantayhteyden muuttujat
export HOST=$JKR_DB_HOST
export PORT=$JKR_DB_PORT
export DB_NAME=$JKR_DB
export USER=$JKR_USER
export PGPASSWORD=$JKR_PASSWORD

# Haetaan kuluva päivä ja muotoillaan
formatted_date=$(date +"%Y%m%d")
day=$(date +"%d")
month=$(date +"%m") 
year=$(date +"%Y")

echo "Käynnistetään import..."
echo "Käytetään poimintapäivämäärää: $day.$month.$year"

# Tarkista hakemistorakenne
data_dir="../data"
dvv_dir="$data_dir/dvv"
if [ ! -d "$data_dir" ] || [ ! -d "$dvv_dir" ]; then
    echo "Virhe: Vaaditut hakemistot puuttuvat. Luo hakemistorakenne: $data_dir/dvv"
    exit 1
fi

# (Vaihe 1) Kunnat ja postinumerot
echo "Tuodaan postinumerotiedot..."
if [ -f "$data_dir/posti/PCF.dat" ]; then
    psql -h $HOST -p $PORT -d $DB_NAME -U $USER -f import_posti.sql
else
    echo "Varoitus: Postitiedosto puuttuu ($data_dir/posti/PCF.dat)"
fi

# (Vaihe 2) DVV aineisto
echo "Tuodaan DVV-aineisto..."

# Tarkista DVV-aineiston olemassaolo
dvv_file="$dvv_dir/DVV_rakennukset.xlsx"
if [ ! -f "$dvv_file" ]; then
    echo "Virhe: DVV-aineisto puuttuu ($dvv_file)"
    exit 1
fi

# Rakennukset
echo "Tuodaan rakennustiedot..."
ogr2ogr -f PostgreSQL -overwrite -progress \
    PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$PGPASSWORD ACTIVE_SCHEMA=jkr_dvv" \
    -nln rakennus "$dvv_file" "R1 rakennus"

# Osoitteet
echo "Tuodaan osoitetiedot..."
ogr2ogr -f PostgreSQL -overwrite -progress \
    PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$PGPASSWORD ACTIVE_SCHEMA=jkr_dvv" \
    -nln osoite "$dvv_file" "R3 osoite"

# Omistajat
echo "Tuodaan omistajatiedot..."
ogr2ogr -f PostgreSQL -overwrite -progress \
    PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$PGPASSWORD ACTIVE_SCHEMA=jkr_dvv" \
    -nln omistaja "$dvv_file" "R4 omistaja"

# Asukkaat
echo "Tuodaan asukastiedot..."
ogr2ogr -f PostgreSQL -overwrite -progress \
    PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$PGPASSWORD ACTIVE_SCHEMA=jkr_dvv" \
    -nln vanhin "$dvv_file" "R9 huon asukk"

# Muunnetaan JKR muotoon
echo "Muunnetaan tiedot JKR-muotoon..."
psql -h $HOST -p $PORT -d $DB_NAME -U $USER -v formatted_date="$formatted_date" -f import_dvv.sql

# Luodaan kohteet
echo "Luodaan kohteet..."
if [ -f "$data_dir/Perusmaksu.xlsx" ]; then
    jkr create_dvv_kohteet "$day.$month.$year" "$data_dir/Perusmaksu.xlsx"
else
    jkr create_dvv_kohteet "$day.$month.$year"
    echo "Huom: Perusmaksurekisteri puuttuu, kohteet luotu ilman sitä"
fi

# Päivitä huoneistojen lukumäärät jos tiedosto löytyy
if [ -f "$data_dir/Huoneistot.xlsx" ]; then
    echo "Päivitetään huoneistomäärät..."
    ogr2ogr -f PostgreSQL -overwrite -progress \
        PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER ACTIVE_SCHEMA=jkr_dvv" \
        -nln huoneistomaara "$data_dir/Huoneistot.xlsx" "Huoneistolkm"
    
    psql -h $HOST -p $PORT -d $DB_NAME -U $USER -f update_huoneistomaara.sql
fi

# Kuljetustietojen tuonti
if [ -d "$data_dir/kuljetukset" ]; then
    echo "Tuodaan kuljetustiedot..."
    
    # Tarkista että tiedontuottaja on olemassa
    jkr tiedontuottaja list | grep -q "LSJ" || \
    jkr tiedontuottaja add LSJ "Lahden Seudun Jätehuolto"

    # Kuljetustietojen tuonti
    # Parametrit:
    # - siirtotiedosto: kuljetustietojen kansio
    # - tiedontuottajatunnus: esim. LSJ
    # --luo_uudet: luo puuttuvat uudet kohteet (default: false)
    # --ala_paivita_yhteystietoja: älä päivitä yhteystietoja (default: false) 
    # --ala_paivita_kohdetta: älä päivitä kohteen voimassaoloaikaa (default: true)
    # alkupvm: datan alkupvm (optional)
    # loppupvm: datan loppupvm (optional)
    
    jkr import "$data_dir/kuljetukset" "LSJ" 1.1.2021 $day.$month.$year
        
    if [ $? -eq 0 ]; then
        echo "Kuljetustietojen tuonti onnistui"
    else
        echo "Virhe kuljetustietojen tuonnissa!"
        exit 1
    fi
else
    echo "Kuljetustietoja ei löytynyt kansiosta $data_dir/kuljetukset"
fi

# HAPA-aineiston tuonti jos tiedosto löytyy
if [ -f "$data_dir/Hapa-kohteet.xlsx" ]; then
    echo "Tuodaan HAPA-aineisto..."
    psql -h $HOST -p $PORT -d $DB_NAME -U $USER -c "\
        COPY hapa_aineisto(kohde_id,rakennus_id,asiakasnumero,osoite,kiinteistotunnus,omistaja,asukas,rakennusluokka,kohdetyyppi) \
        FROM '$data_dir/Hapa-kohteet.xlsx' \
        DELIMITER ';' CSV HEADER;"
fi

echo "Import valmis!"