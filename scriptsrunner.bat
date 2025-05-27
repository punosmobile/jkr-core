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

REM Käynnistä Docker-kontti samalla tavalla kuin docker-compose
docker run --rm -it ^
    --name jkr-runner ^
    -e JKR_DB_HOST=%JKR_DB_HOST% ^
    -e JKR_DB_PORT=%JKR_DB_PORT% ^
    -e JKR_DB=%JKR_DB% ^
    -e JKR_USER=%JKR_USER% ^
    -e JKR_PASSWORD=%JKR_PASSWORD% ^
    -e PGPASSWORD=%PGPASSWORD% ^
    -e APPDATA=/$HOME/.config/jkr/.env ^
    -v "%CD%":/app ^
    jkr-core-runner:latest ^
    bash -c "cd /app && poetry install && cd /app/scripts && exec /bin/bash"

endlocal