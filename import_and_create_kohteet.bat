@echo off

setlocal

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

SET HOST=<palvelimen nimi>
SET PORT=<tietokantaportti>
SET DB_NAME=<tietokannan_nimi>
SET USER=<kayttajatunnus>
REM Määritä salasana %APPDATA%\postgresql\pgpass.conf tiedostossa


REM Tarkistetaan halutaanko importoida posti data.

IF "%~3"=="posti" (
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

psql -h %HOST% -p %PORT% -d %DB_NAME% -U %USER% -v formatted_date="%formatted_date%" -f "import_dvv.sql"

endlocal
