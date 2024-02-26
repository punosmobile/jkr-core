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

SET EXCEL_FILE=%~1
SET HOST=<palvelimen nimi>
SET PORT=<tietokantaportti>
SET DB_NAME=<tietokannan_nimi>
SET USER=<kayttajatunnus>
REM Määritä salasana %APPDATA%\postgresql\pgpass.conf tiedostossa

REM Määritä polku QGISin psql-asennukseen. Esim. "C:\\Program Files\\QGIS 3.30.2\\bin".
SET PSQL_PATH="<Tiedostopolku QGISin bin kansioon>"

REM Määritä polku QGISin ogr2ogr-asennukseen. Esim. "C:\\Program Files\\QGIS 3.30.2\\bin".
SET OGR2OGR_PATH="<Tiedostopolku QGISin bin kansioon>"

ECHO Luetaan huoneistomäärät
%OGR2OGR_PATH%\\ogr2ogr -f PostgreSQL -overwrite -progress PG:"host=%HOST% port=%PORT% dbname=%DB_NAME% user=%USER% ACTIVE_SCHEMA=jkr_dvv" -nln huoneistomaara %EXCEL_FILE% "Huoneistolkm"

ECHO Päivitetään huoneistomäärät rakennus-tauluun
%PSQL_PATH%\\psql -h %HOST% -p %PORT% -d %DB_NAME% -U %USER% -f "update_huoneistomaara.sql"
