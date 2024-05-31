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

REM Tarkistetaan parametrit
IF "%~5"=="" (
   ECHO Anna parametrit järjestyksessä
   ECHO 1. polku CSV-tiedostoon
   ECHO 2. tarkastelupäivämäärä, esim. 2020-01-01
   ECHO 3. kunta, esim. Orimattila
   ECHO 4. huoneistomäärä, 4 = enintään neljä, 5 = vähintään viisi
   ECHO 5. taajaman koko, 200 tai 10000
   ECHO esim. .\tulosta_raportti.bat "C:\tmp\raportit\raportti_orimattila_4_200.csv" 2020-01-01 Orimattila 4 200
   EXIT /b 1
)

REM Vaihdetaan terminaalin code page UTF-8:ksi.
CHCP 65001
REM Kerrotaan Postgresille, että terminaalin encoding on UTF-8.
SET PGCLIENTENCODING=UTF8

"%QGIS_BIN_PATH%\\psql" -v csv_path=%~1 -v check_date=%~2 -v municipality=%~3 -v count_apartments=%~4 -v taajama_size=%~5 -h %JKR_DB_HOST% -p %JKR_DB_PORT% -d %JKR_DB% -U %JKR_USER% -f tulosta_raportti.sql

ECHO Valmis!
