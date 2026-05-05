#!/bin/bash

# Määritä aikaleima
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
START_TIME=$(date +%s)

# Luo logs-hakemisto jos ei ole olemassa
mkdir -p logs/arkisto
mkdir -p logs/kohteet
mkdir -p logs/tietovirrat/2025_Q1
mkdir -p logs/tietovirrat/2025_Q2 
mkdir -p logs/tietovirrat/2025_Q3
mkdir -p logs/tietovirrat/2025_Q4

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
   local exit_code=$?

   # Lopetusaika ja keston laskeminen
   local STEP_END=$(date +%s)
   local DURATION=$((STEP_END - STEP_START))
   local HOURS=$((DURATION / 3600))
   local MINUTES=$(( (DURATION % 3600) / 60 ))
   local SECONDS=$((DURATION % 60))

   echo "===================" >> "$log_file"
   echo "Lopetusaika: $(date)" >> "$log_file"
   echo "Kesto: $HOURS tuntia, $MINUTES minuuttia, $SECONDS sekuntia" >> "$log_file"

   if [ $exit_code -ne 0 ]; then
       echo "VIRHE: $desc epäonnistui (exit code: $exit_code)" | tee -a "$log_file"
       echo "Katso lokitiedosto: $log_file"
       status "VIRHE: $desc epäonnistui (exit code: $exit_code). Skripti keskeytetty."
       exit $exit_code
   fi

   echo "Suoritus valmis" >> "$log_file"
   echo "Lopetusaika: $(date)"
   echo "Suoritus valmis"
   echo "Kesto: $HOURS tuntia, $MINUTES minuuttia, $SECONDS sekuntia"
   echo "==================="
   status "=== $desc - Lopetettu (Kesto: ${HOURS}h ${MINUTES}m ${SECONDS}s) ==="
}

# Funktio lokitusta varten komennoille jotka eivät kulje jkr-CLI:n kautta
# (esim. psql, ogr2ogr, sh-skriptit). Kirjaa tapahtuman jkr.sisaanluku_tapahtuma -tauluun.
log_exec_with_sql_log() {
   local cmd="$1"
   local log_file="$2"
   local desc="$3"

   # Aloitusaika
   local STEP_START
   STEP_START=$(date +%s)

   echo "=== $desc ==="
   status "=== $desc - Aloitettu ==="
   echo "Aloitusaika: $(date)"
   echo "=== $desc ===" > "$log_file"
   echo "Suoritetaan: $cmd" >> "$log_file"
   echo "Aloitusaika: $(date)" >> "$log_file"
   echo "===================" >> "$log_file"

   # Kirjataan sisäänlukutapahtuma kantaan (alkuaika)
   # Poistetaan salasanat komennosta ennen tallennusta
   local SAFE_CMD
   SAFE_CMD=$(printf '%s\n' "$cmd" | sed 's/password=[^ ]*/password=***/g')
   # Käytetään psql:n :'muuttuja'-syntaksia jotta lainausmerkit escapoituvat turvallisesti
   local TAPAHTUMA_ID
   TAPAHTUMA_ID=$(psql -h $HOST -p $PORT -d $DB_NAME -U $USER -t -A \
     -v komento="$SAFE_CMD" <<'EOSQL' 2>/dev/null | head -1 | tr -d '[:space:]'
INSERT INTO jkr.sisaanluku_tapahtuma (komento, alkuaika, status)
VALUES (:'komento', NOW(), 'käynnissä') RETURNING id;
EOSQL
   )

   # Tallennetaan komennon tuloste erilliseen temp-tiedostoon
   local CMD_OUTPUT_FILE
   CMD_OUTPUT_FILE=$(mktemp)
   local EXIT_CODE
   eval "$cmd" > "$CMD_OUTPUT_FILE" 2>&1
   EXIT_CODE=$?
   cat "$CMD_OUTPUT_FILE" >> "$log_file"

   rm -f "$CMD_OUTPUT_FILE"

   # Lopetusaika ja keston laskeminen
   local STEP_END
   STEP_END=$(date +%s)
   local DURATION=$((STEP_END - STEP_START))
   local HOURS=$((DURATION / 3600))
   local MINUTES=$(( (DURATION % 3600) / 60 ))
   local SECONDS=$((DURATION % 60))

   # Päivitetään sisäänlukutapahtuma kantaan (loppuaika + status + lisatiedot)
   # Lisätietoihin tallennetaan vain lyhyt kooste. Tarkempi tuloste on lokitiedostossa.
   if [ -n "$TAPAHTUMA_ID" ]; then
     local CMD_STATUS
     local CMD_LISATIEDOT
     if [ $EXIT_CODE -eq 0 ]; then
       CMD_STATUS="valmis"
       CMD_LISATIEDOT="Valmis. Kesto: ${HOURS}h ${MINUTES}m ${SECONDS}s. Loki: ${log_file}"
     else
       CMD_STATUS="virhe"
       CMD_LISATIEDOT="Virhe (exit code ${EXIT_CODE}). Kesto: ${HOURS}h ${MINUTES}m ${SECONDS}s. Loki: ${log_file}"
     fi
     psql -h $HOST -p $PORT -d $DB_NAME -U $USER -t -A -c \
       "UPDATE jkr.sisaanluku_tapahtuma SET loppuaika = NOW(), status = '${CMD_STATUS}', lisatiedot = '${CMD_LISATIEDOT}' WHERE id = ${TAPAHTUMA_ID};"
   fi

   echo "===================" >> "$log_file"
   echo "Lopetusaika: $(date)" >> "$log_file"
   echo "Kesto: $HOURS tuntia, $MINUTES minuuttia, $SECONDS sekuntia" >> "$log_file"

   if [ $EXIT_CODE -ne 0 ]; then
       echo "VIRHE: $desc epäonnistui (exit code: $EXIT_CODE)" | tee -a "$log_file"
       echo "Katso lokitiedosto: $log_file"
       status "VIRHE: $desc epäonnistui (exit code: $EXIT_CODE). Skripti keskeytetty."
       exit $EXIT_CODE
   fi

   echo "Suoritus valmis" >> "$log_file"
   echo "Lopetusaika: $(date)"
   echo "Suoritus valmis"
   echo "Kesto: $HOURS tuntia, $MINUTES minuuttia, $SECONDS sekuntia"
   echo "==================="
   status "=== $desc - Lopetettu (Kesto: ${HOURS}h ${MINUTES}m ${SECONDS}s) ==="
}

echo "Tuodaan DVV 2025 aineisto..."
# DVV-aineisto 2025
log_exec_with_sql_log "ogr2ogr -f PostgreSQL -overwrite -progress PG:\"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv\" -nln rakennus ../data/DVV/DVV-aineisto_2025.xlsx \"R1 rakennus\"" \
        "logs/import_dvv_rakennukset.log" \
        "DVV rakennusten tuonti"

log_exec_with_sql_log "ogr2ogr -f PostgreSQL -overwrite -progress PG:\"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv\" -nln osoite ../data/DVV/DVV-aineisto_2025.xlsx \"R3 osoite\"" \
        "logs/import_dvv_osoitteet.log" \
        "DVV osoitteiden tuonti"

log_exec_with_sql_log "ogr2ogr -f PostgreSQL -overwrite -progress PG:\"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv\" -nln omistaja ../data/DVV/DVV-aineisto_2025.xlsx \"R4 omistaja\"" \
        "logs/import_dvv_omistajat.log" \
        "DVV omistajien tuonti"

log_exec_with_sql_log "ogr2ogr -f PostgreSQL -overwrite -progress PG:\"host=$HOST port=$PORT dbname=$DB_NAME user=$USER password=$JKR_PASSWORD ACTIVE_SCHEMA=jkr_dvv\" -nln vanhin ../data/DVV/DVV-aineisto_2025.xlsx \"R9 huon asukk\"" \
        "logs/import_dvv_asukkaat.log" \
        "DVV asukkaiden tuonti"

echo "Muunnetaan jkr-muotoon..."
log_exec_with_sql_log "psql -h $HOST -p $PORT -d $DB_NAME -U $USER -v formatted_date=\"20250310\" -f import_dvv.sql" \
        "logs/import_dvv_muunnos.log" \
        "DVV-tietojen muunnos JKR-muotoon"

# Päivitetään huoneistomäärät
echo "Tuodaan huoneistomäärät..."
log_exec_with_sql_log "ogr2ogr -f PostgreSQL -overwrite -progress PG:\"host=$HOST port=$PORT dbname=$DB_NAME user=$USER ACTIVE_SCHEMA=jkr_dvv\" -nln huoneistomaara ../data/Huoneistomäärät_2025.xlsx \"Huoneistomäärät 2025\"" \
        "logs/huoneistomaara_tuonti.log" \
        "Huoneistomäärien tuonti"

log_exec_with_sql_log "psql -h $HOST -p $PORT -d $DB_NAME -U $USER -f update_huoneistomaara.sql" \
        "logs/huoneistomaara_paivitys.log" \
        "Huoneistomäärien päivitys"

# Luodaan kohteet
echo "Luodaan kohteet..."
log_exec "jkr create_dvv_kohteet 10.3.2025" \
        "logs/kohteet/DVV_kohteet.log" \
        "Kohteiden luonti"

# Tuodaan HAPA-aineisto
echo "Tuodaan HAPA-aineisto 2024..."
export CSV_FILE_PATH='../data/Hapa-kohteet_aineisto_2024.csv'

if [ ! -f "$CSV_FILE_PATH" ]; then
    echo "Virhe: Tiedostoa $CSV_FILE_PATH ei löydy" | tee logs/hapa_import.log
fi

quarter="Q1"

log_exec "jkr import_sote ../data/Sotekohteet/Sotekohteet_2025.csv \
        "logs/sote_import.log" \
        "SOTE-aineiston tuonti"

log_exec_with_sql_log "psql -h $HOST -p $PORT -d $DB_NAME -U $USER -c \"\copy jkr.hapa_aineisto(rakennus_id_tunnus, kohde_tunnus, sijaintikunta, asiakasnro, rakennus_id_tunnus2, katunimi_fi, talon_numero, postinumero, postitoimipaikka_fi, kohdetyyppi) FROM '${CSV_FILE_PATH}' WITH (FORMAT csv, DELIMITER ';', HEADER true, ENCODING 'UTF8', NULL '');\"" \
        "logs/hapa_import.log" \
        "HAPA-aineiston tuonti"

# Päivitetään velvoitteet
echo "Ajetaan velvoitepäivitys..."
log_exec "psql -h $HOST -p $PORT -d $DB_NAME -U $USER -c \"SELECT jkr.update_velvoitteet();\"" \
        "logs/kohteet/velvoitteet.log" \
        "Velvoitteiden päivitys"

# Q1 2025 tietojen tuonti (jos saatavilla)
quarter="Q1"
echo "=== Q1 2025 tietovirtojen tuonti ==="

# LIETE-tiedot (jos saatavilla)
if [ -f "../data/Liete/Liete_kuljetustiedot_2025$quarter.xlsx" ]; then
    log_exec "jkr import_liete ../data/Liete/Liete_kuljetustiedot_2025$quarter.xlsx LSJ 1.1.2025 31.3.2025" \
            "logs/tietovirrat/2025_$quarter/liete_kuljetukset.log" \
            "Q1 2025 LIETE-kuljetustietojen tuonti"
fi

if [ -f "../data/Liete/Paatokset_2025$quarter.xlsx" ]; then
    log_exec "jkr import_paatokset ../data/Liete/Paatokset_2025$quarter.xlsx" \
            "logs/tietovirrat/2025_$quarter/liete_paatokset.log" \
            "Q1 2025 LIETE-päätösten tuonti"
fi

# Tavalliset tietovirrat (jos saatavilla)
if [ -f "../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2025/$quarter/Paatokset_2025$quarter.xlsx" ]; then
    log_exec "jkr import_paatokset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2025/$quarter/Paatokset_2025$quarter.xlsx" \
            "logs/tietovirrat/2025_$quarter/paatokset.log" \
            "Q1 2025 päätösten tuonti"
fi

if [ -f "../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2025/$quarter/Kompostointi-ilmoitus_2025$quarter.xlsx" ]; then
    log_exec "jkr import_ilmoitukset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2025/$quarter/Kompostointi-ilmoitus_2025$quarter.xlsx" \
            "logs/tietovirrat/2025_$quarter/ilmoitukset.log" \
            "Q1 2025 ilmoitusten tuonti"
fi

if [ -f "../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2025/$quarter/Kompostoinnin_lopettaminen_2025$quarter.xlsx" ]; then
    log_exec "jkr import_lopetusilmoitukset ../data/Ilmoitus-_ja_päätöstiedot/Päätös-_ja_ilmoitustiedot_2025/$quarter/Kompostoinnin_lopettaminen_2025$quarter.xlsx" \
            "logs/tietovirrat/2025_$quarter/lopetusilmoitukset.log" \
            "Q1 2025 lopetusilmoitusten tuonti"
fi

if [ -d "../data/Kuljetustiedot/Kuljetustiedot_2025/$quarter" ]; then
    log_exec "jkr import ../data/Kuljetustiedot/Kuljetustiedot_2025/$quarter LSJ 1.1.2025 31.3.2025" \
            "logs/tietovirrat/2025_$quarter/kuljetukset.log" \
            "Q1 2025 kuljetustietojen tuonti"
fi

log_exec "psql -h $HOST -p $PORT -d $DB_NAME -U $USER -c \"select jkr.tallenna_velvoite_status('2025-03-31');\"" \
        "logs/tietovirrat/2025_$quarter/velvoitteet.log" \
        "Q1 2025 velvoitteiden tallennus"

# Lopetusaika ja keston laskeminen
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

# Muunna sekunnit helpommin luettavaan muotoon
HOURS=$((DURATION / 3600))
MINUTES=$(( (DURATION % 3600) / 60 ))
SECONDS=$((DURATION % 60))

echo "Skriptin suoritus kesti: $HOURS tuntia, $MINUTES minuuttia, $SECONDS sekuntia"