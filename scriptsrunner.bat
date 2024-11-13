@echo off
setlocal enabledelayedexpansion

REM Tarkista että .testenv tiedosto löytyy
if not exist .testenv (
    echo VIRHE: .testenv tiedostoa ei löydy!
    exit /b 1
)

REM Lue ympäristömuuttujat .testenv tiedostosta
for /f "tokens=*" %%a in ('type .testenv') do (
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
    -e APPDATA=/usr/local/bin/dotenv ^
    -v "%CD%":/app ^
    jkr-core-runner:latest ^
    bash -c "cd /app && poetry install && cd /app/scripts && exec /bin/bash"

endlocal