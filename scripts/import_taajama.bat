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

REM Tarkistetaan parametrit
IF "%~3"=="" (
   ECHO Anna parametrit järjestyksessä
   ECHO 1. polku shp-tiedostoon
   ECHO 2. taajamarajausten alkupäivämäärä, esim. 2020-01-01
   ECHO 3. taajaman koko, esim. 200 tai 10000
   ECHO esim. .\import_taajama.bat "C:\tmp\rajaukset\Yli 10 000 asukkaan taajamat.shp" 2020-01-01 10000
   EXIT /b 1
)

REM Vaihdetaan terminaalin code page UTF-8:ksi
CHCP 65001
REM Kerrotaan Postgresille myäs että terminaalin encoding on UTF-8
SET PGCLIENTENCODING=UTF8

SET SHP_FILE=%~1
SET DATE_FROM=%~2
SET POPULATION=%~3

for %%A in ("%SHP_FILE%") do (
   SET "SHP_TABLE=%%~nA"
)

"%QGIS_BIN_PATH%\\ogr2ogr" -f PostgreSQL -update -append PG:"host=%JKR_DB_HOST% port=%JKR_DB_PORT% dbname=%JKR_DB% user=%JKR_USER% ACTIVE_SCHEMA=jkr" -nln taajama -nlt MULTIPOLYGON -dialect SQLITE -sql "SELECT ""Geometry"" as geom, ""Urakkaraja"" as nimi, %POPULATION% as vaesto_lkm, ""fid"" as taajama_id, '%DATE_FROM%' as alkupvm FROM ""%SHP_TABLE%""" "%SHP_FILE%"

ECHO Valmis!
