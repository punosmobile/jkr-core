@echo off
REM Set terminal code page to UTF-8
CHCP 65001

REM Check if env file parameter is provided
if "%~1"=="" (
    echo Usage: %0 path_to_env_file
    exit /b 1
)

REM Check if env file exists
if not exist "%~1" (
    echo Error: %~1 file not found
    exit /b 1
)

REM Set PostgreSQL client encoding
SET PGCLIENTENCODING=UTF8

REM Load variables from env file
for /f "usebackq tokens=1,* delims==" %%a in ("%~1") do (
    set "%%a=%%b"
)

REM Check required variables
if "%JKR_DB_HOST%"=="" (
    echo Error: HOST variable not set in env file
    exit /b 1
)
if "%JKR_DB_PORT%"=="" (
    echo Error: PORT variable not set in env file
    exit /b 1
)
if "%JKR_DB%"=="" (
    echo Error: DB_NAME variable not set in env file
    exit /b 1
)
if "%JKR_USER%"=="" (
    echo Error: USER variable not set in env file
    exit /b 1
)
if "%QGIS_BIN_PATH%"=="" (
    echo Error: QGIS_BIN_PATH variable not set in env file
    exit /b 1
)

ECHO Converting to jkr format...
"%QGIS_BIN_PATH%\psql" -h %JKR_DB_HOST% -p %JKR_DB_PORT% -d %JKR_DB% -U %JKR_USER% -f "drop_schemas.sql"