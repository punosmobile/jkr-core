@echo off

REM Tarkista onko .env tiedoston polku annettu parametrina
if "%~1"=="" (
   echo Error: Anna .env tiedoston polku parametrina
   echo Käyttö: %0 polku\tiedostoon\.env
   exit /b 1
)

REM Tarkista että .env tiedosto on olemassa
if not exist "%~1" (
   echo Error: .env tiedostoa ei löydy: %~1
   exit /b 1
)

REM UTF-8 koodaus
CHCP 65001
SET PGCLIENTENCODING=UTF8

REM Lue muuttujat .env tiedostosta
for /f "usebackq tokens=1,* delims==" %%a in ("%~1") do (
   set "%%a=%%b"
)

REM Tarkista pakolliset muuttujat
if "%JKR_DB_HOST%"=="" (
   echo Error: HOST puuttuu .env tiedostosta
   exit /b 1
)
if "%JKR_DB_PORT%"=="" (
   echo Error: PORT puuttuu .env tiedostosta
   exit /b 1
)
if "%JKR_DB%"=="" (
   echo Error: DB_NAME puuttuu .env tiedostosta
   exit /b 1
)
if "%JKR_USER%"=="" (
   echo Error: USER puuttuu .env tiedostosta
   exit /b 1
)
if "%QGIS_BIN_PATH%"=="" (
   echo Error: QGIS_BIN_PATH puuttuu .env tiedostosta
   exit /b 1
)

ECHO Muunnetaan jkr-muotoon...
"%QGIS_BIN_PATH%\psql" -h %JKR_DB_HOST% -p %JKR_DB_PORT% -d %JKR_DB% -U %JKR_USER% -f "drop_schemas.sql"