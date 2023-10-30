@echo off

REM Tarkistetaan, että poimintapäivämäärä annettu
IF "%~1"=="" (
    echo Anna dvv-aineiston poimintapäivämäärä parametrina muodossa P.K.VVVV
    exit /b 1
)

REM Muutetaan poimintapäivä VVVVMMDD muotoon.
for /f "tokens=1-3 delims=." %%a in ("%~1%") do (
    set "day=%%a"
    set "month=%%b"
    set "year=%%c"
)

REM Lisätään tarvittaessa päiville ja kuukausille 0 eteen.
if %day% lss 10 set "day=0%day%"
if %month% lss 10 set "month=0%month%"

REM Reformat the date to YYYYMMDD
set "formatted_date=%year%%month%%day%"

REM Vaihdetaan terminaalin code page UTF-8:ksi
CHCP 65001
REM Kerrotaan Postgresille myös että terminaalin encoding on UTF-8
SET PGCLIENTENCODING=UTF8

SET HOST=localhost
SET PORT=5435
SET DB_NAME=jkr
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
psql -h %HOST% -p %PORT% -d %DB_NAME% -U %USER% -v formatted_date="%formatted_date%" -f "import_dvv.sql"
