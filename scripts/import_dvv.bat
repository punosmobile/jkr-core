@echo off

SET HOST=localhost
SET PORT=5435
SET DB_NAME=ymparisto_db
SET USER=jkr_admin
REM Määritä salasana %APPDATA%\postgresql\pgpass.conf tiedostossa

ECHO Rakennukset
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%HOST% port=%PORT% dbname=%DB_NAME% user=%USER% ACTIVE_SCHEMA=jkr_dvv" -nln rakennus "../data/dvv/DVV_rakennukset.xlsx" "R1 rakennus"

ECHO Osoitteet
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%HOST% port=%PORT% dbname=%DB_NAME% user=%USER% ACTIVE_SCHEMA=jkr_dvv" -nln osoite "../data/dvv/DVV_rakennukset.xlsx" "R3 osoite"

ECHO Omistajat
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%HOST% port=%PORT% dbname=%DB_NAME% user=%USER% ACTIVE_SCHEMA=jkr_dvv" -nln omistaja "../data/dvv/DVV_rakennukset.xlsx" "R4 omistaja"

ECHO Asukkaat
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%HOST% port=%PORT% dbname=%DB_NAME% user=%USER% ACTIVE_SCHEMA=jkr_dvv" -nln vanhin "../data/dvv/DVV_rakennukset.xlsx" "R9 huon asukk"

ECHO Muunnetaan jkr-muotoon...
psql -h %HOST% -p %PORT% -d %DB_NAME% -U %USER% -f "import_dvv.sql"
