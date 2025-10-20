#!/bin/bash
export HOST=db
export PORT=$JKR_DB_PORT
export DB_NAME=$JKR_DB
export USER=$JKR_USER
export PGPASSWORD=$JKR_PASSWORD


# Tarkistetaan onko tarvittavat muuttujat asetettu
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

# Tarkistetaan päivämääräparametri
if [ "$#" -ne 1 ]; then
   echo "Anna parametrina taajamarajausten alkupäivämäärä, esim. 2020-01-01"
   exit 1
fi

DATE_FROM="$1"

# Asetetaan PostgreSQL client encoding
export PGCLIENTENCODING=UTF8

BASE_PATH="../data/Taajama-alueet_karttarajaukset"

# Käsitellään 10000 asukkaan taajamat
SHP_FILE_10000="$BASE_PATH/Hyötyjäteurakat yli 10000 asukkaan taajamat.shp"
if [ -f "$SHP_FILE_10000" ]; then
   echo "Käsitellään yli 10000 asukkaan taajamat..."
   SHP_TABLE=$(basename "$SHP_FILE_10000" .shp)
   
   ogr2ogr -f PostgreSQL -update -append \
       "PG:host=$JKR_DB_HOST port=$JKR_DB_PORT dbname=$JKR_DB user=$JKR_USER ACTIVE_SCHEMA=jkr" \
       -nln taajama \
       -nlt MULTIPOLYGON \
       -dialect SQLITE \
       -sql "SELECT \"Geometry\" as geom, \"Urakkaraja\" as nimi, 10000 as vaesto_lkm, \"fid\" as taajama_id, '$DATE_FROM' as alkupvm FROM \"$SHP_TABLE\"" \
       "$SHP_FILE_10000"
else
   echo "Varoitus: 10000 asukkaan taajamien tiedostoa ei löydy"
fi

# Käsitellään 200 asukkaan taajamat 
SHP_FILE_200="$BASE_PATH/Hyötyjäteurakat yli 200 asukkaan taajamat.shp"
if [ -f "$SHP_FILE_200" ]; then
   echo "Käsitellään yli 200 asukkaan taajamat..."
   SHP_TABLE=$(basename "$SHP_FILE_200" .shp)
   
   ogr2ogr -f PostgreSQL -update -append \
       "PG:host=$JKR_DB_HOST port=$JKR_DB_PORT dbname=$JKR_DB user=$JKR_USER ACTIVE_SCHEMA=jkr" \
       -nln taajama \
       -nlt MULTIPOLYGON \
       -dialect SQLITE \
       -sql "SELECT \"Geometry\" as geom, \"Urakkaraja\" as nimi, 200 as vaesto_lkm, \"fid\" as taajama_id, '$DATE_FROM' as alkupvm FROM \"$SHP_TABLE\"" \
       "$SHP_FILE_200"
else
   echo "Varoitus: 200 asukkaan taajamien tiedostoa ei löydy"
fi

echo "Valmis!"