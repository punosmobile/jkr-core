@echo off

REM Vaihdetaan terminaalin code page UTF-8:ksi
CHCP 65001
REM Kerrotaan Postgresille myös että terminaalin encoding on UTF-8
SET PGCLIENTENCODING=UTF8

SET HOST=localhost
SET PORT=5435
SET DB_NAME=jkr
SET USER=jkr_admin
REM Määritä salasana %APPDATA%\postgresql\pgpass.conf tiedostossa

ECHO Muunnetaan jkr-muotoon...
psql -h %HOST% -p %PORT% -d %DB_NAME% -U %USER% -f "drop_schemas.sql"