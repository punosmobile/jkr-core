#!/bin/bash

export HOST=localhost
export PORT=5435
export DB_NAME=jkr
export USER=jkr_admin
# Määritä salasana %APPDATA%\postgresql\pgpass.conf tiedostossa

# Rakennukset
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER ACTIVE_SCHEMA=jkr_dvv" -nln rakennus ../data/dvv/DVV_rakennukset.xlsx "R1 rakennus"

# Osoitteet
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER ACTIVE_SCHEMA=jkr_dvv" -nln osoite ../data/dvv/DVV_rakennukset.xlsx "R3 osoite"

# Omistajat
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER ACTIVE_SCHEMA=jkr_dvv" -nln omistaja ../data/dvv/DVV_rakennukset.xlsx "R4 omistaja"

# Asukkaat
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER ACTIVE_SCHEMA=jkr_dvv" -nln vanhin ../data/dvv/DVV_rakennukset.xlsx "R9 huon asukk"

psql -h $HOST -p $PORT -d $DB_NAME -U $USER -f import_dvv.sql
