#!/bin/bash

ENV_PATH="/Users/samulivirtanen/Documents/samuli/lahti/lahtitest/jkr-core/.env"

export $(grep -v '^#' "$ENV_PATH" | xargs)

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

if [ "$#" -lt 5 ]; then
    echo "Anna parametrit järjestyksessä:"
    echo "1. polku CSV-tiedostoon"
    echo "2. tarkastelupäivämäärä, esim. 2020-01-01"
    echo "3. kunta, esim. Orimattila, * = kaikki kunnat"
    echo "4. huoneistomäärä, 4 = enintään neljä, 5 = vähintään viisi, 0 = kaikki huoneistomäärät"
    echo "5. taajaman koko, 200 tai 10000, 0 = ei taajamarajausta"
    echo "Esimerkki: ./tulosta_raportti.sh \"/tmp/raportit/raportti_orimattila_4_200.csv\" 2020-01-01 Orimattila 4 200"
    exit 1
fi


export LC_ALL=en_US.UTF-8
export PGCLIENTENCODING=UTF8

"psql" -v csv_path="$1" -v check_date="$2" -v municipality="$3" -v count_apartments="$4" -v taajama_size="$5" -h "$JKR_DB_HOST" -p "$JKR_DB_PORT" -d "$JKR_DB" -U "$JKR_USER" -f ./tulosta_raportti.sql

echo "Valmis!"
