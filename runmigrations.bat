@echo off
setlocal enabledelayedexpansion

if "%~1"=="" (
    echo Virhe: Anna .env tiedoston polku parametrina
    echo Kaytto: %0 polku\.env
    exit /b 1
)

if not exist "%~1" (
    echo Virhe: .env tiedostoa ei loydy: %~1
    exit /b 1
)

REM Lue ympäristömuuttujat parametrina annetusta .env tiedostosta
for /f "usebackq tokens=1,* delims==" %%a in ("%~1") do (
    set "%%a=%%b"
)

if "%JKR_DB_HOST%"=="" goto :missing_env
if "%JKR_DB_PORT%"=="" goto :missing_env
if "%JKR_DB%"=="" goto :missing_env
if "%JKR_USER%"=="" goto :missing_env
if "%JKR_PASSWORD%"=="" goto :missing_env

REM Debug: näytä luetut arvot
echo Luetut ymparistomuuttujat:
echo HOST: %JKR_DB_HOST%
echo PORT: %JKR_DB_PORT%
echo DB: %JKR_DB%
echo USER: %JKR_USER%

REM Aja migraatiot
echo Ajetaan migraatiot...
docker run --rm ^
    --network host ^
    -v "%CD%\db\migrations":/flyway/sql ^
    -v "%CD%\db\flyway.conf":/flyway/conf/flyway.conf ^
    flyway/flyway ^
    -url=jdbc:postgresql://%JKR_DB_HOST%:%JKR_DB_PORT%/%JKR_DB% ^
    -user=%JKR_USER% ^
    -password=%JKR_PASSWORD% ^
    migrate

if %ERRORLEVEL% neq 0 (
    echo Virhe migraatioiden ajamisessa
    goto :eof
)

REM Näytä migraatioiden tila
echo.
echo Migraatioiden tila:
docker run --rm ^
    --network host ^
    -v "%CD%\db\migrations":/flyway/sql ^
    -v "%CD%\db\flyway.conf":/flyway/conf/flyway.conf ^
    flyway/flyway ^
    -url=jdbc:postgresql://%JKR_DB_HOST%:%JKR_DB_PORT%/%JKR_DB% ^
    -user=%JKR_USER% ^
    -password=%JKR_PASSWORD% ^
    info

goto :eof

:missing_env
echo Virhe: Määrittele ensin ympäristömuuttujat JKR_DB_HOST, JKR_DB_PORT, JKR_DB, JKR_USER ja JKR_PASSWORD
exit /b 1

endlocal