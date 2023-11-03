@echo off

REM Luodaan kanta alusta dockerilla
docker stop jkr_test_database
docker rm jkr_test_database
docker volume rm jkr-core_postgis-data-test
docker compose -f ..\\docker-compose.yml up -d db_test
docker compose -f ..\\docker-compose.yml run --rm flyway_test migrate

REM Vaihdetaan terminaalin code page UTF-8:ksi
CHCP 65001
REM Kerrotaan Postgresille my├Âs terminaalin encoding UTF-8
SET PGCLIENTENCODING=UTF8

SET HOST=localhost
SET PORT=5436
SET DB_NAME=jkr_test
SET USER=jkr_admin
SET PGPASSWORD=qwerty
REM Salasana v├ñlitet├ñ├ñn ymp├ñrist├Âmuuttujassa ainoastaan testikannalle, joka ei sis├ñll├ñ todellista dataa

ECHO Kunnat ja postinumerot
REM Kunnat ja postinumerot on tuotava tietokantaan ennen dvv-aineiston tuontia
psql -h %HOST% -p %PORT% -d %DB_NAME% -U %USER% -f "./scripts/import_posti_test.sql"

SET OGR2OGR_PATH="C:\\Program Files\\QGIS 3.28.9\\bin"

ECHO Rakennukset
%OGR2OGR_PATH%\\ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%HOST% port=%PORT% dbname=%DB_NAME% user=%USER% ACTIVE_SCHEMA=jkr_dvv" -nln rakennus "./data/test_data_import/DVV_original.xlsx" "R1 rakennus"

ECHO Osoitteet
%OGR2OGR_PATH%\\ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%HOST% port=%PORT% dbname=%DB_NAME% user=%USER% ACTIVE_SCHEMA=jkr_dvv" -nln osoite "./data/test_data_import/DVV_original.xlsx" "R3 osoite"

ECHO Omistajat
%OGR2OGR_PATH%\\ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%HOST% port=%PORT% dbname=%DB_NAME% user=%USER% ACTIVE_SCHEMA=jkr_dvv" -nln omistaja "./data/test_data_import/DVV_original.xlsx" "R4 omistaja"

ECHO Asukkaat
%OGR2OGR_PATH%\\ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%HOST% port=%PORT% dbname=%DB_NAME% user=%USER% ACTIVE_SCHEMA=jkr_dvv" -nln vanhin "./data/test_data_import/DVV_original.xlsx" "R9 huon asukk"

ECHO Muunnetaan jkr-muotoon...
psql -h %HOST% -p %PORT% -d %DB_NAME% -U %USER% -v formatted_date=20220128 -f "../scripts/import_dvv.sql"
