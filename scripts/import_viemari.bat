@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM === Environment variables ===
set HOST=db
set PORT=%JKR_DB_PORT%
set DB_NAME=%JKR_DB%
set USER=%JKR_USER%
set PGPASSWORD=%JKR_PASSWORD%

REM === Check required environment variables ===
if "%JKR_DB_HOST%"=="" (
    echo Error: HOST variable not set in .env file
    exit /b 1
)

if "%JKR_DB_PORT%"=="" (
    echo Error: PORT variable not set in .env file
    exit /b 1
)

if "%JKR_DB%"=="" (
    echo Error: DB_NAME variable not set in .env file
    exit /b 1
)

if "%JKR_USER%"=="" (
    echo Error: USER variable not set in .env file
    exit /b 1
)

REM === Check parameter count ===
if "%~2"=="" (
    echo Anna parametrina viemäriverkoston alkupäivämäärä, esim. 2020-01-01 sekä tiedosto, esim. Asikkala_vesihuoltolaitoksen_toiminta-alueet.shp
    exit /b 1
)

if not "%~3"=="" (
    echo Liikaa parametreja annettu
    exit /b 1
)

set DATE_FROM=%~1
set FILE_PATH=%~2

REM === PostgreSQL client encoding ===
set PGCLIENTENCODING=UTF8

REM === Process sewer network data ===
if exist "%FILE_PATH%" (

    echo Käsitellään viemäriverkosto...

    REM Extract shapefile base name
    for %%F in ("%FILE_PATH%") do set SHP_TABLE=%%~nF

    REM === Extract fields using ogrinfo + awk ===
    set FIELDS=

    for /f "usebackq delims=" %%A in (`
        ogrinfo -al -so "%FILE_PATH%" 2^>nul ^|
        awk "/^[A-Za-z_][A-Za-z0-9_]*: / && $1 !~ /^(Geometry|Extent|Metadata|Layer|Feature|Data|SRS|ID|PROJCRS|BASEGEOGCRS|CONVERSION|CS|AXIS|USAGE|BBOX)$/ { sub(/:.*/, \"\", $1); print $1 }"
    `) do (
        set FIELDS=!FIELDS! %%A
    )

    echo %FIELDS%
    echo start checks

    REM === Detect name column ===
    echo %FIELDS% | findstr /x /c:"nimi" >nul
    if not errorlevel 1 (
        set NAME_COL=nimi
    ) else (
        echo %FIELDS% | findstr /x /c:"Lajin_seli" >nul
        if not errorlevel 1 (
            set NAME_COL=Lajin_seli
        ) else (
            echo No name column found
            exit /b 1
        )
    )

    REM === Detect ID column ===
    echo %FIELDS% | findstr /c:"OBJECTID" >nul
    if not errorlevel 1 (
        set ID_COL=OBJECTID
    ) else (
        set ID_COL=Laji
    )

    REM === Run ogr2ogr ===
    set SHAPE_ENCODING=CP1252

    ogr2ogr -f PostgreSQL -update -append ^
    -s_srs EPSG:3880 ^
    -t_srs EPSG:3067 ^
    --config OGR_CT_FORCE_TRADITIONAL_GIS_ORDER YES ^
    "PG:host=%JKR_DB_HOST% port=%JKR_DB_PORT% dbname=%JKR_DB% user=%JKR_USER% ACTIVE_SCHEMA=jkr" ^
    -nln viemariverkosto ^
    -nlt MULTIPOLYGON ^
    -dialect SQLITE ^
    -sql "SELECT \"Geometry\" AS geom,
                 \"%NAME_COL%\" AS nimi,
                 \"%ID_COL%\" AS viemariverkosto_id,
                 '%DATE_FROM%' AS alkupvm
          FROM \"%SHP_TABLE%\"" ^
    "%FILE_PATH%"

) else (
    echo Varoitus: Annettua viemäröintiverkosto tiedostoa ei löydy
)

echo Valmis!
endlocal