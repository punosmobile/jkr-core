@echo off
setlocal

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
if "%JKR_DB_PORT%"=="" (
    echo Error: PORT variable not set in .env file
    exit /b 1
)
if "%JKR_DB%"=="" (
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

if "%JKR_PASSWORD%"=="" (
    echo Error: USER variable not set in .env file
    exit /b 1
)

set PGPASSWORD=%JKR_PASSWORD%

REM Tarkistetaan, että dvv-aineisto on syötetty
IF "%~1"=="" (
    echo Anna dvv-aineiston tiedostopolku.
    exit /b 1
)

REM Tarkistetaan, että poimintapäivämäärä annettu
IF "%~2"=="" (
    echo Anna dvv-aineiston poimintapäivämäärä parametrina muodossa P.K.V
    exit /b 2
)

REM Asetetaan parametrit muuttujiksi
SET DVV=%~1
SET POIMINTAPVM=%~2
REM Muutetaan poimintapäivämäärä muotoon VVVVKKPP
for /f "tokens=1-3 delims=." %%a in ("%POIMINTAPVM%") do (
    set "day=%%a"
    set "month=%%b"
    set "year=%%c"
)

if %day% lss 10 set "day=0%day%"
if %month% lss 10 set "month=0%month%"

set "formatted_date=%year%%month%%day%"


REM Vaihdetaan terminaalin code page UTF-8:ksi
CHCP 65001
REM Kerrotaan Postgresille myös että terminaalin encoding on UTF-8
SET PGCLIENTENCODING=UTF8

REM Tarkistetaan halutaanko importoida posti data.

IF "%~3"=="posti" (
    "%QGIS_BIN_PATH%\\psql" -h %JKR_DB_HOST% -p %JKR_DB_PORT% -d %JKR_DB% -U %JKR_USER% -f "./scripts/jkr_posti.sql"
)

ECHO Rakennukset
"%QGIS_BIN_PATH%\\ogr2ogr" -f PostgreSQL -overwrite -progress PG:"host=%JKR_DB_HOST% port=%JKR_DB_PORT% dbname=%JKR_DB% user=%JKR_USER% ACTIVE_SCHEMA=jkr_dvv" -nln rakennus %DVV% "R1 rakennus"

ECHO Osoitteet
"%QGIS_BIN_PATH%\\ogr2ogr" -f PostgreSQL -overwrite -progress PG:"host=%JKR_DB_HOST% port=%JKR_DB_PORT% dbname=%JKR_DB% user=%JKR_USER% ACTIVE_SCHEMA=jkr_dvv" -nln osoite %DVV% "R3 osoite"

ECHO Omistajat
"%QGIS_BIN_PATH%\\ogr2ogr" -f PostgreSQL -overwrite -progress PG:"host=%JKR_DB_HOST% port=%JKR_DB_PORT% dbname=%JKR_DB% user=%JKR_USER% ACTIVE_SCHEMA=jkr_dvv" -nln omistaja %DVV% "R4 omistaja"

ECHO Asukkaat
"%QGIS_BIN_PATH%\\ogr2ogr" -f PostgreSQL -overwrite -progress PG:"host=%JKR_DB_HOST% port=%JKR_DB_PORT% dbname=%JKR_DB% user=%JKR_USER% ACTIVE_SCHEMA=jkr_dvv" -nln vanhin %DVV% "R9 huon asukk"

ECHO Muunnetaan jkr-muotoon...

"%QGIS_BIN_PATH%\\psql" -h %JKR_DB_HOST% -p %JKR_DB_PORT% -d %JKR_DB% -U %JKR_USER% -v formatted_date="%formatted_date%" -f ".\scripts\import_dvv.sql"

endlocal