@echo off

SET HOST=localhost
SET PORT=5435
SET DB_NAME=ymparisto_db
SET USER=jkr_admin
REM Määritä salasana %APPDATA%\postgresql\pgpass.conf tiedostossa

ECHO Rakennukset
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%HOST% port=%PORT% dbname=%DB_NAME% user=%USER% ACTIVE_SCHEMA=jkr_dvv" -nln rakennus -sql "select * from \"R1 rakennus\"" -f xlsx "../data/dvv/DVV_rakennukset.xlsx"

ECHO Osoitteet
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%HOST% port=%PORT% dbname=%DB_NAME% user=%USER% ACTIVE_SCHEMA=jkr_dvv" -nln osoite -sql "select * from \"R3 osoite\"" -f xlsx "../data/dvv/DVV_rakennukset.xlsx"

ECHO Omistajat
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%HOST% port=%PORT% dbname=%DB_NAME% user=%USER% ACTIVE_SCHEMA=jkr_dvv" -nln omistaja -sql "select * from \"R4 omistaja\"" -f xlsx "../data/dvv/DVV_rakennukset.xlsx"

ECHO Asukkaat
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%HOST% port=%PORT% dbname=%DB_NAME% user=%USER% ACTIVE_SCHEMA=jkr_dvv" -nln vanhin -sql "select * from \"R9 huon asukk\"" -f xlsx "../data/dvv/DVV_rakennukset.xlsx"

ECHO Muunnetaan jkr-muotoon...
psql -h %HOST% -p %PORT% -d %DB_NAME% -U %USER% -f "import_dvv.sql"
