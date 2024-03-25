@echo off

REM Luodaan kanta alusta dockerilla
"C:\\Program Files\\Docker\\Docker\\resources\\bin\\docker.exe" stop jkr_test_database
"C:\\Program Files\\Docker\\Docker\\resources\\bin\\docker.exe" rm jkr_test_database
"C:\\Program Files\\Docker\\Docker\\resources\\bin\\docker.exe" volume rm jkr-core_postgis-data-test
"C:\\Program Files\\Docker\\Docker\\resources\\bin\\docker.exe" compose --env-file "%APPDATA%\jkr\.env" -f ..\\docker-compose.yml up -d db_test
"C:\\Program Files\\Docker\\Docker\\resources\\bin\\docker.exe" compose --env-file "%APPDATA%\jkr\.env" -f ..\\docker-compose.yml run --rm flyway_test migrate

REM Vaihdetaan terminaalin code page UTF-8:ksi
CHCP 65001
REM Kerrotaan Postgresille myÔö£├és terminaalin encoding UTF-8
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
if "%QGIS_BIN_PATH%"=="" (
    echo Error: QGIS_BIN_PATH variable not set in .env file
    exit /b1
)


SET PGPASSWORD=%JKR_PASSWORD%

ECHO Kunnat ja postinumerot
REM Kunnat ja postinumerot on tuotava tietokantaan ennen dvv-aineiston tuontia
"%QGIS_BIN_PATH%\\psql" -h %JKR_DB_HOST% -p %JKR_TEST_DB_PORT% -d %JKR_TEST_DB% -U %JKR_USER% -f "./scripts/import_posti_test.sql"


ECHO Rakennukset
"%QGIS_BIN_PATH%\\ogr2ogr" -f PostgreSQL -overwrite -progress PG:"host=%JKR_DB_HOST% port=%JKR_TEST_DB_PORT% dbname=%JKR_TEST_DB% user=%JKR_USER% ACTIVE_SCHEMA=jkr_dvv" -nln rakennus "./data/test_data_import/DVV_original.xlsx" "R1 rakennus"

ECHO Osoitteet
"%QGIS_BIN_PATH%\\ogr2ogr" -f PostgreSQL -overwrite -progress PG:"host=%JKR_DB_HOST% port=%JKR_TEST_DB_PORT% dbname=%JKR_TEST_DB% user=%JKR_USER% ACTIVE_SCHEMA=jkr_dvv" -nln osoite "./data/test_data_import/DVV_original.xlsx" "R3 osoite"

ECHO Omistajat
"%QGIS_BIN_PATH%\\ogr2ogr" -f PostgreSQL -overwrite -progress PG:"host=%JKR_DB_HOST% port=%JKR_TEST_DB_PORT% dbname=%JKR_TEST_DB% user=%JKR_USER% ACTIVE_SCHEMA=jkr_dvv" -nln omistaja "./data/test_data_import/DVV_original.xlsx" "R4 omistaja"

ECHO Asukkaat
"%QGIS_BIN_PATH%\\ogr2ogr" -f PostgreSQL -overwrite -progress PG:"host=%JKR_DB_HOST% port=%JKR_TEST_DB_PORT% dbname=%JKR_TEST_DB% user=%JKR_USER% ACTIVE_SCHEMA=jkr_dvv" -nln vanhin "./data/test_data_import/DVV_original.xlsx" "R9 huon asukk"

ECHO Muunnetaan jkr-muotoon...
"%QGIS_BIN_PATH%\\psql" -h %JKR_DB_HOST% -p %JKR_TEST_DB_PORT% -d %JKR_TEST_DB% -U %JKR_USER% -v formatted_date=20220128 -f "../scripts/import_dvv.sql"
