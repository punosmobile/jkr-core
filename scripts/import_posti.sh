#!/bin/bash

export HOST=db
export PORT=$JKR_DB_PORT
export DB_NAME=$JKR_DB
export USER=$JKR_USER
export PGPASSWORD=$JKR_PASSWORD
# Määritä salasana %APPDATA%\postgresql\pgpass.conf tiedostossa

# Kunnat ja postinumerot
# Kunnat ja postinumerot on tuotava tietokantaan ennen dvv-aineiston tuontia
POSTI_FILE=${1:-../data/posti/PCF.dat}
psql -h $HOST -p $PORT -d $DB_NAME -U $USER -v posti_file="$POSTI_FILE" -f import_posti.sql

# Kadut
# Katuja ei tarvitse tuoda; tarvittavat kadut löytyvät dvv-osoiteaineistosta
# psql -h $HOST -p $PORT -d $DB_NAME -U $USER -f import_katu.sql
