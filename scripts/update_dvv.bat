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

ECHO Rakennukset
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%JKR_DB_HOST% port=%JKR_DB_PORT% dbname=%JKR_DB% user=%JKR_USER% ACTIVE_SCHEMA=jkr_dvv" -nln rakennus "../data/dvv/DVV_rakennukset_uusi.xlsx" "R1 rakennus"

ECHO Osoitteet
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%JKR_DB_HOST% port=%JKR_DB_PORT% dbname=%JKR_DB% user=%JKR_USER% ACTIVE_SCHEMA=jkr_dvv" -nln osoite "../data/dvv/DVV_rakennukset_uusi.xlsx" "R3 osoite"

ECHO Omistajat
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%JKR_DB_HOST% port=%JKR_DB_PORT% dbname=%JKR_DB% user=%JKR_USER% ACTIVE_SCHEMA=jkr_dvv" -nln omistaja "../data/dvv/DVV_rakennukset_uusi.xlsx" "R4 omistaja"

ECHO Asukkaat
ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%JKR_DB_HOST% port=%JKR_DB_PORT% dbname=%JKR_DB% user=%JKR_USER% ACTIVE_SCHEMA=jkr_dvv" -nln vanhin "../data/dvv/DVV_rakennukset_uusi.xlsx" "R9 huon asukk"

ECHO Muunnetaan jkr-muotoon...
psql -h %JKR_DB_HOST% -p %JKR_DB_PORT% -d %JKR_DB% -U %JKR_USER% -v formatted_date="%formatted_date%" -f "import_dvv.sql"
