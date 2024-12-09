@echo off
setlocal enabledelayedexpansion

REM Check if environment file parameter is provided
if "%1"=="" (
    echo Usage: %0 path_to_env_file
    exit /b 1
)

REM Read environment variables from specified file
for /f "tokens=*" %%a in ('type "%1"') do (
    set "%%a"
)

REM Run migrations
docker run --rm ^
    --network host ^
    -v "%CD%\db\migrations":/flyway/sql ^
    -v "%CD%\db\flyway.conf":/flyway/conf/flyway.conf ^
    flyway/flyway ^
    -url=jdbc:postgresql://%JKR_DB_HOST%:%JKR_DB_PORT%/%JKR_DB% ^
    -user=%JKR_USER% ^
    -password=%JKR_PASSWORD% ^
    migrate

REM Show migration status
docker run --rm ^
    --network host ^
    -v "%CD%\db\migrations":/flyway/sql ^
    -v "%CD%\db\flyway.conf":/flyway/conf/flyway.conf ^
    flyway/flyway ^
    -url=jdbc:postgresql://%JKR_DB_HOST%:%JKR_DB_PORT%/%JKR_DB% ^
    -user=%JKR_USER% ^
    -password=%JKR_PASSWORD% ^
    info

endlocal