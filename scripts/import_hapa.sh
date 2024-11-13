#!/bin/bash
export HOST=db
export PORT=$JKR_DB_PORT
export DB_NAME=$JKR_DB
export USER=$JKR_USER
export PGPASSWORD=$JKR_PASSWORD

export CSV_FILE_PATH='../data/Hapa-kohteet.xlsx'

psql -h $HOST -p $PORT -d $DB_NAME -U $USER -c "\copy hapa_aineisto(kohde_id, rakennus_id, asiakasnumero, osoite, kiinteistotunnus, omistaja, asukas, rakennusluokka, kohdetyyppi) FROM '$CSV_FILE_PATH' DELIMITER ';' CSV HEADER;"

# Tarkista, onnistuiko tuonti
if [ $? -eq 0 ]; then
  echo "HAPA-aineiston tuonti onnistui."
else
  echo "HAPA-aineiston tuonti epäonnistui."
fi