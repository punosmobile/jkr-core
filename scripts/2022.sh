#!/bin/bash

# Määritä aikaleima
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
START_TIME=$(date +%s)

rm -rf logs
rm jkr.log
rm cluster_debug.log
rm kiinteisto_debug.log

# Luo logs-hakemisto jos ei ole olemassa
mkdir -p logs/arkisto
mkdir -p logs/kohteet
mkdir -p logs/tietovirrat/2022_Q1
mkdir -p logs/tietovirrat/2022_Q2 
mkdir -p logs/tietovirrat/2022_Q3
mkdir -p logs/tietovirrat/2022_Q4

find ../data -type f -iname "kohdentumat*" -exec rm {} \;

# Arkistoi vanhat lokit jos niitä on
if [ -n "$(ls -A logs 2>/dev/null)" ]; then
    echo "Arkistoidaan vanhat lokit..."
    mkdir -p logs/arkisto
    tar -czf logs/arkisto/logs_${TIMESTAMP}.tar.gz --exclude='logs/arkisto' logs/
    rm -f logs/*/*.log logs/*.log
fi

# Aseta ympäristömuuttujat
export HOST=$JKR_DB_HOST
export PORT=$JKR_DB_PORT
export DB_NAME=$JKR_DB
export USER=$JKR_USER
export PGPASSWORD=$JKR_PASSWORD
export APPDATA=/$HOME/.config/jkr/.env
export HOOK_URL=$HOOK_URL

# Funktio edistymistä varten
status() {
    local message="$1"
    
    # Tarkista onko HOOK_URL määritelty
    if [ -n "${HOOK_URL}" ]; then
        echo "Lähetetään webhook: $message"
        curl -s -X POST \
             -H "Content-Type: application/json" \
             -d "{\"message\": \"${message}\"}" \
             "${HOOK_URL}" || echo "Webhook lähetys epäonnistui"
    fi
}

# Funktio lokitusta varten
log_exec() {
   local cmd="$1"
   local log_file="$2"
   local desc="$3"
   
   # Aloitusaika
   local STEP_START=$(date +%s)
   
   echo "=== $desc ==="
   status "=== $desc - Aloitettu ==="
   echo "Aloitusaika: $(date)"
   echo "=== $desc ===" > "$log_file"
   echo "Suoritetaan: $cmd" >> "$log_file"
   echo "Aloitusaika: $(date)" >> "$log_file"
   echo "===================" >> "$log_file"
   
   eval "$cmd" >> "$log_file" 2>&1
   
   # Lopetusaika ja keston laskeminen
   local STEP_END=$(date +%s)
   local DURATION=$((STEP_END - STEP_START))
   local HOURS=$((DURATION / 3600))
   local MINUTES=$(( (DURATION % 3600) / 60 ))
   local SECONDS=$((DURATION % 60))
   
   echo "===================" >> "$log_file"
   echo "Lopetusaika: $(date)" >> "$log_file"
   echo "Suoritus valmis" >> "$log_file"
   echo "Kesto: $HOURS tuntia, $MINUTES minuuttia, $SECONDS sekuntia" >> "$log_file"
   echo "Lopetusaika: $(date)"
   echo "Suoritus valmis"
   echo "Kesto: $HOURS tuntia, $MINUTES minuuttia, $SECONDS sekuntia"
   echo "==================="
   status "=== $desc - Lopetettu (Kesto: ${HOURS}h ${MINUTES}m ${SECONDS}s) ==="
}

echo "Aloitetaan tietojen tuonti..."

# Tarkista että tiedontuottaja on olemassa
log_exec "jkr tiedontuottaja list | grep -q 'LSJ' || jkr tiedontuottaja add LSJ 'Lahden Seudun Jätehuolto'" \
        "logs/tiedontuottaja_setup.log" \
        "Tiedontuottajan määritys"

# Vaihe 1: Taajamarajaukset
log_exec "sh import_taajama.sh 2020-01-01" \
        "logs/import_taajama.log" \
        "Taajamarajausten tuonti"

# Vaihe 2: Kunnat ja postinumerot
log_exec "psql -h $HOST -p $PORT -d $DB_NAME -U $USER -f import_posti.sql" \
        "logs/import_posti.log" \
        "Kuntien ja postinumeroiden tuonti"

# Vaihe 3: DVV aineisto 2022
echo "=== DVV-aineiston tuonti ===" > logs/import_dvv.log
# Rakennukset
log_exec "ogr2ogr -f PostgreSQL -overwrite -progress PG:\"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv\" -nln rakennus ../data/DVV/DVV-aineisto_2022.xlsx \"R1 rakennus\"" \
        "logs/import_dvv_rakennukset.log" \
        "DVV rakennusten tuonti"

# Osoitteet
log_exec "ogr2ogr -f PostgreSQL -overwrite -progress PG:\"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv\" -nln osoite ../data/DVV/DVV-aineisto_2022.xlsx \"R3 osoite\"" \
        "logs/import_dvv_osoitteet.log" \
        "DVV osoitteiden tuonti"

# Omistajat
log_exec "ogr2ogr -f PostgreSQL -overwrite -progress PG:\"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv\" -nln omistaja ../data/DVV/DVV-aineisto_2022.xlsx \"R4 omistaja\"" \
        "logs/import_dvv_omistajat.log" \
        "DVV omistajien tuonti"

# Asukkaat
log_exec "ogr2ogr -f PostgreSQL -overwrite -progress PG:\"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv\" -nln vanhin ../data/DVV/DVV-aineisto_2022.xlsx \"R9 huon asukk\"" \
        "logs/import_dvv_asukkaat.log" \
        "DVV asukkaiden tuonti"

# DVV muunnos JKR-muotoon
log_exec "psql -h $HOST -p $PORT -d $DB_NAME -U $USER -v formatted_date=\"20220128\" -f import_dvv.sql" \
        "logs/import_dvv_muunnos.log" \
        "DVV-tietojen muunnos JKR-muotoon"

# Vaihe 4: Huoneistomäärän päivitys

log_exec "ogr2ogr -f PostgreSQL -overwrite -progress PG:\"host=$JKR_DB_HOST port=$JKR_DB_PORT dbname=$JKR_DB user=$JKR_USER ACTIVE_SCHEMA=jkr_dvv\" -nln huoneistomaara ../data/Huoneistomäärät_2022.xlsx \"Huoneistolkm\"" \
        "logs/huoneistomaara_tuonti.log" \
        "Huoneistomäärien tuonti"

log_exec "psql -h $JKR_DB_HOST -p $JKR_DB_PORT -d $JKR_DB -U $JKR_USER -f update_huoneistomaara.sql" \
        "logs/huoneistomaara_paivitys.log" \
        "Huoneistomäärien päivitys"

# Vaihe 5: Kohteiden luonti perusmaksuaineistosta
log_exec "jkr create_dvv_kohteet 28.1.2022 ../data/Perusmaksuaineisto.xlsx" \
        "logs/kohteet/perusmaksu_kohteet.log" \
        "Kohteiden luonti perusmaksuaineistosta"

# Vaihe 6: HAPA-aineiston tuonti
export CSV_FILE_PATH='../data/Hapa-kohteet_aineisto_2022.csv'

if [ ! -f "$CSV_FILE_PATH" ]; then
    echo "Virhe: Tiedostoa $CSV_FILE_PATH ei löydy" | tee logs/hapa_import.log
fi

log_exec "psql -h $HOST -p $PORT -d $DB_NAME -U $USER -c \"\copy jkr.hapa_aineisto(rakennus_id_tunnus, kohde_tunnus, sijaintikunta, asiakasnro, rakennus_id_tunnus2, katunimi_fi, talon_numero, postinumero, postitoimipaikka_fi, kohdetyyppi) FROM '${CSV_FILE_PATH}' WITH (FORMAT csv, DELIMITER ';', HEADER true, ENCODING 'UTF8', NULL '');\"" \
        "logs/hapa_import.log" \
        "HAPA-aineiston tuonti"

# Velvoitteiden päivitys
log_exec "psql -h $HOST -p $PORT -d $DB_NAME -U $USER -c \"SELECT jkr.update_velvoitteet();\"" \
        "logs/kohteet/velvoitteet.log" \
        "Velvoitteiden päivitys"

# Q1 2022 tietojen tuonti
quarter="Q1"
log_exec "jkr import_paatokset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2022/$quarter/Paatokset_2022$quarter.xlsx" \
        "logs/tietovirrat/2022_$quarter/paatokset.log" \
        "Q1 päätösten tuonti"

log_exec "jkr import_ilmoitukset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2022/$quarter/Kompostointi-ilmoitus_2022$quarter.xlsx" \
        "logs/tietovirrat/2022_$quarter/ilmoitukset.log" \
        "Q1 ilmoitusten tuonti"

log_exec "jkr import_lopetusilmoitukset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2022/$quarter/Kompostoinnin_lopettaminen_2022$quarter.xlsx" \
        "logs/tietovirrat/2022_$quarter/lopetusilmoitukset.log" \
        "Q1 lopetusilmoitusten tuonti"

log_exec "jkr import ../data/Kuljetustiedot/Kuljetustiedot_2022/$quarter LSJ 1.1.2022 31.3.2022" \
        "logs/tietovirrat/2022_$quarter/kuljetukset.log" \
        "Q1 kuljetustietojen tuonti"

log_exec "psql -h $HOST -p $PORT -d $DB_NAME -U $USER -c \"select jkr.tallenna_velvoite_status('2022-03-31');\"" \
        "logs/tietovirrat/2022_$quarter/velvoitteet.log" \
        "Q1 velvoitteiden tallennus"

# Q2 2022 tietojen tuonti
quarter="Q2"
log_exec "jkr import_paatokset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2022/$quarter/Paatokset_2022$quarter.xlsx" \
        "logs/tietovirrat/2022_$quarter/paatokset.log" \
        "Q2 päätösten tuonti"

log_exec "jkr import_ilmoitukset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2022/$quarter/Kompostointi-ilmoitus_2022$quarter.xlsx" \
        "logs/tietovirrat/2022_$quarter/ilmoitukset.log" \
        "Q2 ilmoitusten tuonti"

log_exec "jkr import_lopetusilmoitukset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2022/$quarter/Kompostoinnin_lopettaminen_2022$quarter.xlsx" \
        "logs/tietovirrat/2022_$quarter/lopetusilmoitukset.log" \
        "Q2 lopetusilmoitusten tuonti"

log_exec "jkr import ../data/Kuljetustiedot/Kuljetustiedot_2022/$quarter LSJ 1.4.2022 30.6.2022" \
        "logs/tietovirrat/2022_$quarter/kuljetukset.log" \
        "Q2 kuljetustietojen tuonti"

log_exec "psql -h $HOST -p $PORT -d $DB_NAME -U $USER -c \"select jkr.tallenna_velvoite_status('2022-06-30');\"" \
        "logs/tietovirrat/2022_$quarter/velvoitteet.log" \
        "Q2 velvoitteiden tallennus"

# Q3 2022 tietojen tuonti
quarter="Q3"
log_exec "jkr import_paatokset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2022/$quarter/Paatokset_2022$quarter.xlsx" \
        "logs/tietovirrat/2022_$quarter/paatokset.log" \
        "Q3 päätösten tuonti"

log_exec "jkr import_ilmoitukset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2022/$quarter/Kompostointi-ilmoitus_2022$quarter.xlsx" \
        "logs/tietovirrat/2022_$quarter/ilmoitukset.log" \
        "Q3 ilmoitusten tuonti"

log_exec "jkr import_lopetusilmoitukset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2022/$quarter/Kompostoinnin_lopettaminen_2022$quarter.xlsx" \
        "logs/tietovirrat/2022_$quarter/lopetusilmoitukset.log" \
        "Q3 lopetusilmoitusten tuonti"

log_exec "jkr import ../data/Kuljetustiedot/Kuljetustiedot_2022/$quarter LSJ 1.7.2022 30.9.2022" \
        "logs/tietovirrat/2022_$quarter/kuljetukset.log" \
        "Q3 kuljetustietojen tuonti"

log_exec "psql -h $HOST -p $PORT -d $DB_NAME -U $USER -c \"select jkr.tallenna_velvoite_status('2022-09-30');\"" \
        "logs/tietovirrat/2022_$quarter/velvoitteet.log" \
        "Q3 velvoitteiden tallennus"

# Q4 2022 tietojen tuonti
quarter="Q4"
log_exec "jkr import_paatokset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2022/$quarter/Paatokset_2022$quarter.xlsx" \
        "logs/tietovirrat/2022_$quarter/paatokset.log" \
        "Q4 päätösten tuonti"

log_exec "jkr import_ilmoitukset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2022/$quarter/Kompostointi-ilmoitus_2022$quarter.xlsx" \
        "logs/tietovirrat/2022_$quarter/ilmoitukset.log" \
        "Q4 ilmoitusten tuonti"

log_exec "jkr import_lopetusilmoitukset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2022/$quarter/Kompostoinnin_lopettaminen_2022$quarter.xlsx" \
        "logs/tietovirrat/2022_$quarter/lopetusilmoitukset.log" \
        "Q4 lopetusilmoitusten tuonti"

log_exec "jkr import ../data/Kuljetustiedot/Kuljetustiedot_2022/$quarter LSJ 1.10.2022 31.12.2022" \
        "logs/tietovirrat/2022_$quarter/kuljetukset.log" \
        "Q4 kuljetustietojen tuonti"

log_exec "psql -h $HOST -p $PORT -d $DB_NAME -U $USER -c \"select jkr.tallenna_velvoite_status('2022-12-31');\"" \
        "logs/tietovirrat/2022_$quarter/velvoitteet.log" \
        "Q4 velvoitteiden tallennus"

# Lopetusaika ja keston laskeminen
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Muunna sekunnit helpommin luettavaan muotoon
HOURS=$((DURATION / 3600))
MINUTES=$(( (DURATION % 3600) / 60 ))
SECONDS=$((DURATION % 60))

echo "Skriptin suoritus kesti: $HOURS tuntia, $MINUTES minuuttia, $SECONDS sekuntia"