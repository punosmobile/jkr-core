´╗┐@echo off
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

REM K├ñynnist├ñ Docker-kontti samalla tavalla kuin docker-compose
REM --network liitt├ñ├ñ kontin docker-compose-verkkoon jossa db-palvelu n├ñkyy
REM JKR_DB_HOST=db ja JKR_DB_PORT=5432 ovat konttien v├ñlisi├ñ sis├ñisi├ñ osoitteita
docker run --rm -it ^
    -p 8000:8000 ^
    --name jkr-runner ^
    --network jkr-core-development_default ^
    -e JKR_DB_HOST=db ^
    -e JKR_DB_PORT=5432 ^
    -e JKR_DB=%JKR_DB% ^
    -e JKR_USER=%JKR_USER% ^
    -e JKR_PASSWORD=%JKR_PASSWORD% ^
    -e PGPASSWORD=%JKR_PASSWORD% ^
    -e APPDATA=/$HOME/.config/jkr/.env ^
    -e JKR_LOG_LEVEL=%JKR_LOG_LEVEL% ^
    -v "%CD%":/app ^
    jkr-core-runner:latest ^
    bash -c "cd /app && poetry install && uvicorn jkrimporter.api.api:app --host 0.0.0.0 --port 8000 & cd /app/scripts && exec /bin/bash"

endlocal