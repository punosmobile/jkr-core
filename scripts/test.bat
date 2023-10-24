@echo off

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

REM Tarkistetaan onko postitiedosto syötetty.
IF "%~3" NEQ "None" (
    SET POSTI=%~3
)

REM Asetetaan parametrit muuttujiksi
SET DVV=%~1
SET POIMINTAPVM=%~2
REM Split the date into day, month, and year
for /f "tokens=1-3 delims=." %%a in ("%POIMINTAPVM%") do (
    set "day=%%a"
    set "month=%%b"
    set "year=%%c"
)

REM Pad day and month with leading zeros if needed
if %day% lss 10 set "day=0%day%"
if %month% lss 10 set "month=0%month%"

REM Reformat the date to YYYYMMDD
set "formatted_date=%year%%month%%day%"

echo Original Date: %POIMINTAPVM%
echo Formatted Date: %formatted_date%

REM Vaihdetaan terminaalin code page UTF-8:ksi
CHCP 65001
REM Kerrotaan Postgresille myös että terminaalin encoding on UTF-8
SET PGCLIENTENCODING=UTF8

SET HOST=localhost
SET PORT=5435
SET DB_NAME=jkr
SET USER=jkr_admin
REM Määritä salasana %APPDATA%\postgresql\pgpass.conf tiedostossa

IF DEFINED POSTI (
    psql -h %HOST% -p %PORT% -d %DB_NAME% -U %USER% -f "import_posti.sql"
)

ECHO Rakennukset
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%HOST% port=%PORT% dbname=%DB_NAME% user=%USER% ACTIVE_SCHEMA=jkr_dvv" -nln rakennus %DVV% "R1 rakennus"

ECHO Osoitteet
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%HOST% port=%PORT% dbname=%DB_NAME% user=%USER% ACTIVE_SCHEMA=jkr_dvv" -nln osoite %DVV% "R3 osoite"

ECHO Omistajat
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%HOST% port=%PORT% dbname=%DB_NAME% user=%USER% ACTIVE_SCHEMA=jkr_dvv" -nln omistaja %DVV% "R4 omistaja"

ECHO Asukkaat
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%HOST% port=%PORT% dbname=%DB_NAME% user=%USER% ACTIVE_SCHEMA=jkr_dvv" -nln vanhin %DVV% "R9 huon asukk"

ECHO Muunnetaan jkr-muotoon...

set FORMATTED_DATE=%formatted_date%
psql -h %HOST% -p %PORT% -d %DB_NAME% -U %USER% -v formatted_date="%FORMATTED_DATE%" -f "import_dvv.sql"
