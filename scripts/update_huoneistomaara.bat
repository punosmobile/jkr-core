@echo off

REM Tarkistetaan, että on annettu polku xlsx-tiedostoon
 IF "%~1"=="" (
    echo Anna polku xlsx-tiedostoon, joka sisältää huoneistomäärät
    exit /b 1
)

REM Vaihdetaan terminaalin code page UTF-8:ksi
CHCP 65001
REM Kerrotaan Postgresille myäs että terminaalin encoding on UTF-8
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
if "%QGIS_BIN_PATH%"=="" (
    echo Error: QGIS_BIN_PATH variable not set in .env file
    exit /b1
)

if "%JKR_PASSWORD%"=="" (
    echo Error: USER variable not set in .env file
    exit /b 1
)

set PGPASSWORD=%JKR_PASSWORD%

SET EXCEL_FILE=%~1

ECHO Luetaan huoneistomäärät
"%QGIS_BIN_PATH%\\ogr2ogr" -f PostgreSQL -overwrite -progress PG:"host=%JKR_DB_HOST% port=%JKR_DB_PORT% dbname=%JKR_DB% user=%JKR_USER% ACTIVE_SCHEMA=jkr_dvv" -nln huoneistomaara %EXCEL_FILE% "Huoneistolkm"

ECHO Päivitetään huoneistomäärät rakennus-tauluun
"%QGIS_BIN_PATH%\\psql" -h %JKR_DB_HOST% -p %JKR_DB_PORT% -d %JKR_DB% -U %JKR_USER% -f "scripts//update_huoneistomaara.sql"
