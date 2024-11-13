@echo off
setlocal enabledelayedexpansion

REM Lue ympäristömuuttujat .testenv tiedostosta
for /f "tokens=*" %%a in ('type .testenv') do (
    set "%%a"
)

REM Aja migraatiot
docker run --rm ^
    --network host ^
    -v "%CD%\db\migrations":/flyway/sql ^
    -v "%CD%\db\flyway.conf":/flyway/conf/flyway.conf ^
    flyway/flyway ^
    -url=jdbc:postgresql://%JKR_DB_HOST%:%JKR_DB_PORT%/%JKR_DB% ^
    -user=%JKR_USER% ^
    -password=%JKR_PASSWORD% ^
    migrate

REM Näytä migraatioiden tila
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