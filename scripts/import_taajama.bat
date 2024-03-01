@echo off
setlocal

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

SET HOST=<palvelimen nimi>
SET PORT=<tietokantaportti>
SET DB_NAME=<tietokannan_nimi>
SET USER=<kayttajatunnus>
REM Määritä salasana %APPDATA%\postgresql\pgpass.conf tiedostossa

SET SHP_FILE=%~1
SET DATE_FROM=%~2
SET POPULATION=%~3

for %%A in ("%SHP_FILE%") do (
   SET "SHP_TABLE=%%~nA"
)

REM Määritä polku QGISin ogr2ogr-asennukseen. Esim. "C:\\Program Files\\QGIS 3.30.2\\bin".
SET OGR2OGR_PATH="C:\\Program Files\\QGIS 3.28.9\\bin"

%OGR2OGR_PATH%\\ogr2ogr -f PostgreSQL -update -append PG:"host=%HOST% port=%PORT% dbname=%DB_NAME% user=%USER% ACTIVE_SCHEMA=jkr" -nln taajama -nlt MULTIPOLYGON -dialect SQLITE -sql "SELECT ""Geometry"" as geom, ""Urakkaraja"" as nimi, %POPULATION% as vaesto_lkm, ""fid"" as taajama_id, '%DATE_FROM%' as alkupvm FROM ""%SHP_TABLE%""" "%SHP_FILE%"

ECHO Valmis!
