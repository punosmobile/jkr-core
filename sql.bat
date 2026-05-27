@echo off
setlocal

REM ---------------------------------------------------------------------------
REM Kaytto: sql.bat <ymparisto> "SQL-kysely" [tietokanta]
REM   <ymparisto>   = local | dev | test | prod (lukee ../.env.<ymparisto>)
REM   "SQL-kysely"  = ajettava SQL
REM   [tietokanta]  = valinnainen DB-nimen ohitus (oletus JKR_DB env-tiedostosta)
REM Esim: sql.bat local "SELECT version();"
REM ---------------------------------------------------------------------------

set "ENV_NAME=%~1"
set "SQL_QUERY=%~2"
set "DB_NAME_OVERRIDE=%~3"

if "%ENV_NAME%"=="" goto :usage
if "%SQL_QUERY%"=="" goto :usage

REM Etsi .env-tiedosto (ensin ../.env.<env>, sitten ./.env.<env>)
set "ENV_FILE=%~dp0..\.env.%ENV_NAME%"
if not exist "%ENV_FILE%" set "ENV_FILE=%~dp0.env.%ENV_NAME%"
if not exist "%ENV_FILE%" (
    echo Virhe: env-tiedostoa ei loydy: .env.%ENV_NAME%
    exit /b 1
)

REM Lue env-tiedosto (ohittaa kommentit ja tyhjat rivit)
for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%ENV_FILE%") do (
    if not "%%A"=="" set "%%A=%%B"
)

REM Validoi pakolliset muuttujat
if "%JKR_DB_HOST%"=="" (
    echo Virhe: JKR_DB_HOST puuttuu tiedostosta %ENV_FILE%
    exit /b 1
)
if "%JKR_DB_PORT%"=="" set "JKR_DB_PORT=5432"
if "%JKR_USER%"=="" (
    echo Virhe: JKR_USER puuttuu tiedostosta %ENV_FILE%
    exit /b 1
)
if not "%DB_NAME_OVERRIDE%"=="" set "JKR_DB=%DB_NAME_OVERRIDE%"
if "%JKR_DB%"=="" (
    echo Virhe: JKR_DB puuttuu tiedostosta %ENV_FILE%
    exit /b 1
)

REM PGPASSWORD asetetaan jos JKR_PASSWORD on annettu (muuten env-tiedoston PGPASSWORD)
if not "%JKR_PASSWORD%"=="" set "PGPASSWORD=%JKR_PASSWORD%"

set "PAGER="

echo [%ENV_NAME%] %JKR_USER%@%JKR_DB_HOST%:%JKR_DB_PORT%/%JKR_DB%
psql -h %JKR_DB_HOST% -U %JKR_USER% -p %JKR_DB_PORT% -d %JKR_DB% -c "%SQL_QUERY%"
set "EXITCODE=%ERRORLEVEL%"

set "PGPASSWORD="
endlocal & exit /b %EXITCODE%

:usage
echo Kaytto: %~nx0 ^<ymparisto^> "SQL-kysely" [tietokanta]
echo   ymparisto: local ^| dev ^| test ^| prod  (lukee ../.env.^<ymparisto^>)
echo Esim:    %~nx0 local "SELECT version();"
exit /b 1