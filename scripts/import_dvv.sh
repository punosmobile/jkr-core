#!/bin/bash

export HOST=localhost
export PORT=5435
export DB_NAME=jkr
export USER=jkr_admin
# Määritä salasana %APPDATA%\postgresql\pgpass.conf tiedostossa

# Rakennukset
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER ACTIVE_SCHEMA=jkr_dvv" -nln rakennus -sql "select * from \"R1 rakennus\"" -f xlsx ../data/dvv/DVV_rakennukset.xlsx

# Osoitteet
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER ACTIVE_SCHEMA=jkr_dvv" -nln osoite -sql "select * from \"R3 osoite\"" -f xlsx ../data/dvv/DVV_rakennukset.xlsx

# Omistajat
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER ACTIVE_SCHEMA=jkr_dvv" -nln omistaja -sql "select * from \"R4 omistaja\"" -f xlsx ../data/dvv/DVV_rakennukset.xlsx

# Asukkaat
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=$HOST port=$PORT dbname=$DB_NAME user=$USER ACTIVE_SCHEMA=jkr_dvv" -nln vanhin -sql "select * from \"R9 huon asukk\"" -f xlsx ../data/dvv/DVV_rakennukset.xlsx

psql -h $HOST -p $PORT -d $DB_NAME -U $USER -f import_dvv.sql
