#!/bin/bash

export HOST=db
export PORT=$JKR_DB_PORT
export DB_NAME=$JKR_DB
export USER=$JKR_USER
export PGPASSWORD=$JKR_PASSWORD
export APPDATA=/usr/local/bin/dotenv

# Haetaan kuluva päivä ja muotoillaan
formatted_date=$(date +"%Y%m%d")
day=$(date +"%d")
month=$(date +"%m")
year=$(date +"%Y")


# (Vaihe 3) DVV aineisto Huoneistot
jkr create_dvv_kohteet $day.$month.$year ../data/DVV/DVV_rakennukset.xlsx ../data/Perusmaksu.xlsx posti