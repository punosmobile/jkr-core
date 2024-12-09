@echo off
chcp 65001 > nul
set PGCLIENTENCODING=UTF8
setlocal EnableDelayedExpansion
if "%~1"=="" (
    echo Virhe: Anna .env tiedoston polku parametrina
    echo Kaytto: %0 polku\.env
    exit /b 1
)
if not exist "%~1" (
    echo Virhe: .env tiedostoa ei loydy: %~1
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

REM Get current date and time in desired format
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set YYYY=%datetime:~0,4%
set MM=%datetime:~4,2%
set DD=%datetime:~6,2%
set HH=%datetime:~8,2%
set Min=%datetime:~10,2%

REM Create dump directory if it doesn't exist
if not exist "..\dump" (
    mkdir "..\dump"
)
set "DUMP_PATH=..\dump"
set "SCHEMA_FILENAME=%DUMP_PATH%\%YYYY%%MM%%DD%%HH%%Min%_%HOST%_%DB_NAME%_schema.sql"
set "DATA_FILENAME=%DUMP_PATH%\%YYYY%%MM%%DD%%HH%%Min%_%HOST%_%DB_NAME%_data.sql"

echo Luodaan schema dump tiedostoon: %SCHEMA_FILENAME%
set PGSSLMODE=prefer
call "%QGIS_BIN_PATH%\pg_dump.exe" -h %HOST% -p %PORT% -U %USER% -Fp --inserts -O --no-owner --no-acl --schema-only -f "%SCHEMA_FILENAME%" %DB_NAME%

echo Luodaan data dump tiedostoon: %DATA_FILENAME%
call "%QGIS_BIN_PATH%\pg_dump.exe" -h %HOST% -p %PORT% -U %USER% -Fp --inserts -O --no-owner --no-acl --data-only -f "%DATA_FILENAME%" %DB_NAME%

if %ERRORLEVEL% equ 0 (
    echo Tietokantadumpit luotu onnistuneesti.
) else (
    echo Virhe tietokantadumppien luonnissa.
)
goto :eof

:missing_env
echo Virhe: M├ñ├ñrittele ensin ymp├ñrist├Âmuuttujat JKR_DB_HOST, JKR_DB_PORT, JKR_DB, JKR_USER ja JKR_PASSWORD
exit /b 1