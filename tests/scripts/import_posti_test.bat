@echo off

REM Vaihdetaan terminaalin code page UTF-8:ksi
CHCP 65001
REM Kerrotaan Postgresille my├Âs terminaalin encoding UTF-8
SET PGCLIENTENCODING=UTF8

SET HOST=localhost
SET PORT=5436
SET DB_NAME=jkr_test
SET USER=jkr_admin
SET PGPASSWORD=qwerty
REM Salasana v├ñlitet├ñ├ñn ymp├ñrist├Âmuuttujassa ainoastaan testikannalle, joka ei sis├ñll├ñ todellista dataa

ECHO Kunnat ja postinumerot
REM Kunnat ja postinumerot on tuotava tietokantaan ennen dvv-aineiston tuontia
psql -h %HOST% -p %PORT% -d %DB_NAME% -U %USER% -f "./scripts/import_posti_test.sql"
