#!/bin/bash

export HOST=localhost
export PORT=5435
export DB_NAME=jkr
export USER=jkr_admin
# Määritä salasana %APPDATA%\postgresql\pgpass.conf tiedostossa

# Kunnat ja postinumerot
# Kunnat ja postinumerot on tuotava tietokantaan ennen dvv-aineiston tuontia
psql -h $HOST -p $PORT -d $DB_NAME -U $USER -f import_posti.sql

# Kadut
# Katuja ei tarvitse tuoda; tarvittavat kadut löytyvät dvv-osoiteaineistosta
# psql -h $HOST -p $PORT -d $DB_NAME -U $USER -f import_katu.sql
