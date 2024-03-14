@echo off

REM Vaihdetaan terminaalin code page UTF-8:ksi
CHCP 65001
REM Kerrotaan Postgresille my├Âs terminaalin encoding UTF-8
SET PGCLIENTENCODING=UTF8

REM Tarkistetaan .env tiedosto.
if not exist "%APPDATA%\jkr\.env" (
    echo Error: .env file not found at %APPDATA%\jkr\.env
    exit /b 1
)

REM Ladataan muuttujat .env tiedostosta.
for /f "usebackq tokens=1,* delims==" %%a in ("%APPDATA%\jkr\.env") do (
    set "%%a=%%b"
)

REM Tarkistetaan onko tarvittavat muuttujat asetettu.
if "%JKR_DB_HOST%"=="" (
    echo Error: HOST variable not set in .env file
    exit /b 1
)
if "%JKR_TEST_DB_PORT%"=="" (
    echo Error: PORT variable not set in .env file
    exit /b 1
)
if "%JKR_TEST_DB%"=="" (
    echo Error: DB_NAME variable not set in .env file
    exit /b 1
)
if "%JKR_USER%"=="" (
    echo Error: USER variable not set in .env file
    exit /b 1
)

SET PGPASSWORD=%JKR_PASSWORD%

SET OGR2OGR_PATH="C:\\Program Files\\QGIS 3.28.11\\bin"

ECHO Rakennukset
%OGR2OGR_PATH%\\ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%JKR_DB_HOST% port=%JKR_TEST_DB_PORT% dbname=%JKR_TEST_DB% user=%JKR_USER% ACTIVE_SCHEMA=jkr_dvv" -nln rakennus "./data/test_data_import/DVV_update.xlsx" "R1 rakennus"

ECHO Osoitteet
%OGR2OGR_PATH%\\ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%JKR_DB_HOST% port=%JKR_TEST_DB_PORT% dbname=%JKR_TEST_DB% user=%JKR_USER% ACTIVE_SCHEMA=jkr_dvv" -nln osoite "./data/test_data_import/DVV_update.xlsx" "R3 osoite"

ECHO Omistajat
%OGR2OGR_PATH%\\ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%JKR_DB_HOST% port=%JKR_TEST_DB_PORT% dbname=%JKR_TEST_DB% user=%JKR_USER% ACTIVE_SCHEMA=jkr_dvv" -nln omistaja "./data/test_data_import/DVV_update.xlsx" "R4 omistaja"

ECHO Asukkaat
%OGR2OGR_PATH%\\ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%JKR_DB_HOST% port=%JKR_TEST_DB_PORT% dbname=%JKR_TEST_DB% user=%JKR_USER% ACTIVE_SCHEMA=jkr_dvv" -nln vanhin "./data/test_data_import/DVV_update.xlsx" "R9 huon asukk"

ECHO Muunnetaan jkr-muotoon...
psql -h %JKR_DB_HOST% -p %JKR_TEST_DB_PORT% -d %JKR_TEST_DB% -U %JKR_USER% -v formatted_date=20230131 -f "../scripts/import_dvv.sql"
