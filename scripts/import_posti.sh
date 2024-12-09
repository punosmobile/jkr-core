#!/bin/bash

export HOST=db
export PORT=$JKR_DB_PORT
export DB_NAME=$JKR_DB
export USER=$JKR_USER
export PGPASSWORD=$JKR_PASSWORD
# Määritä salasana %APPDATA%\postgresql\pgpass.conf tiedostossa

# Kunnat ja postinumerot
# Kunnat ja postinumerot on tuotava tietokantaan ennen dvv-aineiston tuontia
psql -h $HOST -p $PORT -d $DB_NAME -U $USER -f import_posti.sql

# Kadut
# Katuja ei tarvitse tuoda; tarvittavat kadut löytyvät dvv-osoiteaineistosta
# psql -h $HOST -p $PORT -d $DB_NAME -U $USER -f import_katu.sql
