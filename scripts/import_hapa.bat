@echo off
REM import_hapa.bat - Imports HAPA data to JKR database
REM Usage: import_hapa.bat <path_to_hapa_csv_file>

setlocal enabledelayedexpansion

REM Check if the CSV file path is provided
if "%~1"=="" (
    echo Error: CSV file path not provided.
    echo Usage: import_hapa.bat ^<path_to_hapa_csv_file^>
    exit /b 1
)

REM Set the CSV file path
set "CSV_FILE_PATH=%~1"

REM Check if the file exists
if not exist "%CSV_FILE_PATH%" (
    echo Error: File %CSV_FILE_PATH% does not exist.
    exit /b 1
)

REM Load environment variables from .env file if it exists
if exist ".env" (
    echo Loading environment variables from .env
    for /F "tokens=*" %%i in (.env) do (
        set "%%i"
    )
)

REM Check for required environment variables
if not defined JKR_DB_HOST (
    echo Error: JKR_DB_HOST environment variable is not defined.
    exit /b 1
)
if not defined JKR_DB_PORT (
    echo Error: JKR_DB_PORT environment variable is not defined.
    exit /b 1
)
if not defined JKR_DB (
    echo Error: JKR_DB environment variable is not defined.
    exit /b 1
)
if not defined JKR_USER (
    echo Error: JKR_USER environment variable is not defined.
    exit /b 1
)

REM Check for QGIS bin path
if not defined QGIS_BIN_PATH (
    echo Error: QGIS_BIN_PATH environment variable is not defined.
    exit /b 1
)

REM Set psql command path
set "PSQL_CMD=%QGIS_BIN_PATH%\psql.exe"

REM Check if psql command exists
if not exist "%PSQL_CMD%" (
    echo Error: psql command not found at %PSQL_CMD%
    exit /b 1
)

REM Vaihdetaan terminaalin code page UTF-8:ksi
CHCP 65001
REM Kerrotaan Postgresille my├Âs ett├ñ terminaalin encoding on UTF-8
SET PGCLIENTENCODING=UTF8

echo Importing HAPA data from %CSV_FILE_PATH%...

REM Import the HAPA data using psql's COPY command
"%PSQL_CMD%" -h %JKR_DB_HOST% -p %JKR_DB_PORT% -d %JKR_DB% -U %JKR_USER% -c "\copy jkr.hapa_aineisto(rakennus_id_tunnus, kohde_tunnus, sijaintikunta, asiakasnro, rakennus_id_tunnus2, katunimi_fi, talon_numero, postinumero, postitoimipaikka_fi, kohdetyyppi) FROM '%CSV_FILE_PATH%' WITH (FORMAT csv, DELIMITER ';', HEADER true, ENCODING 'UTF8', NULL '');"

if %ERRORLEVEL% neq 0 (
    echo Error importing HAPA data.
    exit /b %ERRORLEVEL%
)

echo HAPA data imported successfully.
echo VALMIS!

endlocal
exit /b 0
