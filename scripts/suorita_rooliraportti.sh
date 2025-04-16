#!/bin/bash

# Tarkista että .env-tiedosto on annettu parametrina
if [ -z "$1" ]; then
  echo "Käyttö: ./aja_rooliraportti.sh polku/.env"
  exit 1
fi

ENV_FILE="$1"
if [ ! -f "$ENV_FILE" ]; then
  echo "Tiedostoa $ENV_FILE ei löytynyt!"
  exit 1
fi

# Ladataan ympäristömuuttujat .env-tiedostosta
export $(grep -v '^#' "$ENV_FILE" | xargs)

# Tiedostonimet
TIEDOSTO="roles_report.csv"
AIKA=$(date +%Y-%m-%d_%H-%M)
VARMISTUS="roles_report_backup_$AIKA.csv"
AIKALEIMATTU="roles_report_$AIKA.csv"

# Jos vanha tiedosto on olemassa, tee varmuuskopio
if [ -f "$TIEDOSTO" ]; then
  echo "🛡️ Varmuuskopioidaan vanha raportti -> $VARMISTUS"
  cp "$TIEDOSTO" "$VARMISTUS"
fi

# Aja SQL-skripti psql:llä .env-muuttujilla
echo "▶️ Ajetaan rooliraportti kannasta $JKR_DB käyttäjällä $JKR_USER..."
PGPASSWORD="$JKR_PASSWORD" psql -h "$JKR_DB_HOST" -p "$JKR_DB_PORT" -U "$JKR_USER" -d "$JKR_DB" -f rooliraportti.sql

# Jos raportti syntyi, uudelleennimeä se aikaleimalla
if [ -f "$TIEDOSTO" ]; then
  mv "$TIEDOSTO" "$AIKALEIMATTU"
  echo "✅ Raportti tallennettu tiedostoon: $AIKALEIMATTU"
else
  echo "❌ Raporttia ei löytynyt – tarkista SQL-skripti tai kannayhteys."
fi
