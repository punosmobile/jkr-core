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

# Tarkistetaan parametrien määrä
if [ "$#" -ne 2 ]; then
   echo "Anna parametrina viemäriverkoston alkupäivämäärä, esim. 2020-01-01 sekä tiedosto, esim. Asikkala_vesihuoltolaitoksen_toiminta-alueet.shp"
   exit 1
fi

DATE_FROM="$1"
FILE_PATH="$2"

# Asetetaan PostgreSQL client encoding
export PGCLIENTENCODING=UTF8


# Käsitellään viemäriverkoston tiedot
if [ -f "$FILE_PATH" ]; then
   echo "Käsitellään viemäriverkosto..."
   SHP_TABLE=$(basename "$FILE_PATH" .shp)

FIELDS=$(ogrinfo -al -so "$FILE_PATH" 2>/dev/null \
  | awk '
    /^[A-Za-z_][A-Za-z0-9_]*: / &&
    $1 !~ /^(Geometry|Extent|Metadata|Layer|Feature|Data|SRS|ID|PROJCRS|BASEGEOGCRS|CONVERSION|CS|AXIS|USAGE|BBOX)$/ {
      sub(/:.*/, "", $1)
      print $1
    }'
)

echo $FIELDS
echo "start checks"
if echo "$FIELDS" | grep -qx 'nimi'; then
  NAME_COL="nimi"
elif echo "$FIELDS" | grep -qx 'Lajin_seli'; then
  NAME_COL="Lajin_seli"
else
  echo "No name column found"
  exit 1
fi

if echo "$FIELDS" | grep -q "OBJECTID"; then
  ID_COL="OBJECTID"
else
  ID_COL="Laji"
fi
   
   SHAPE_ENCODING=CP1252 ogr2ogr -f PostgreSQL -update -append \
       "PG:host=$JKR_DB_HOST port=$JKR_DB_PORT dbname=$JKR_DB user=$JKR_USER ACTIVE_SCHEMA=jkr" \
       -nln viemariverkosto \
       -nlt MULTIPOLYGON \
       -dialect SQLITE \
       -sql "SELECT \"Geometry\" as geom, \"$NAME_COL\" as nimi, \"$ID_COL\" as viemariverkosto_id, '$DATE_FROM' as alkupvm FROM \"$SHP_TABLE\"" \
       "$FILE_PATH"
else
   echo "Varoitus: Annettua viemäröintiverkosto tiedostoa ei löydy"
fi

echo "Valmis!"