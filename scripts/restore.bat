@echo off
chcp 65001 > nul
set PGCLIENTENCODING=UTF8
setlocal EnableDelayedExpansion

if "%~3"=="" (
    echo Virhe: Anna .env tiedoston polku, schema dumpin polku ja data dumpin polku parametreina
    echo Kaytto: %0 polku\.env polku\schema.sql polku\data.sql
    exit /b 1
)

if not exist "%~1" (
    echo Virhe: .env tiedostoa ei loydy: %~1
    exit /b 1
)

if not exist "%~2" (
    echo Virhe: Schema dump-tiedostoa ei loydy: %~2
    exit /b 1
)

if not exist "%~3" (
    echo Virhe: Data dump-tiedostoa ei loydy: %~3
    exit /b 1
)

for /f "usebackq tokens=1,* delims==" %%a in ("%~1") do (
    set "%%a=%%b"
)

if "%JKR_DB_HOST%"=="" goto :missing_env
if "%JKR_DB_PORT%"=="" goto :missing_env
if "%JKR_DB%"=="" goto :missing_env
if "%JKR_USER%"=="" goto :missing_env
if "%JKR_PASSWORD%"=="" goto :missing_env
if "%QGIS_BIN_PATH%"=="" goto :missing_env

set HOST=%JKR_DB_HOST%
set PORT=%JKR_DB_PORT%
set DB_NAME=%JKR_DB%
set USER=%JKR_USER%
set PGPASSWORD=%JKR_PASSWORD%
set QGIS_BIN_PATH=%QGIS_BIN_PATH%

REM Debug: n├ñyt├ñ luetut arvot
echo Luetut ymparistomuuttujat:
echo HOST: %JKR_DB_HOST%
echo PORT: %JKR_DB_PORT%
echo DB_NAME: %JKR_DB%
echo USER: %JKR_USER%
echo QGIS_BIN_PATH: %QGIS_BIN_PATH%

echo Palautetaan schema tiedostosta: %~2
set PGSSLMODE=require

call "%QGIS_BIN_PATH%\psql.exe" -h %HOST% -p %PORT% -U %USER% -d %DB_NAME% -f "%~2"

echo Palautetaan data tiedostosta: %~3
call "%QGIS_BIN_PATH%\psql.exe" -h %HOST% -p %PORT% -U %USER% -d %DB_NAME% -f "%~3"

if %ERRORLEVEL% equ 0 (
    echo Tietokanta palautettu onnistuneesti.
) else (
    echo Virhe tietokannan palautuksessa.
)
goto :eof

:missing_env
echo Virhe: M├ñ├ñrittele ensin ymp├ñrist├Âmuuttujat JKR_DB_HOST, JKR_DB_PORT, JKR_DB, JKR_USER ja JKR_PASSWORD
exit /b 1