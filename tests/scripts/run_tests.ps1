# run_tests.ps1
# Nollaa testikanta ja ajaa kaikki testit kontainerissa.
#
# Käyttö: .\tests\scripts\run_tests.ps1
# Aja projektin juuresta tai skripti löytää juuren itse.
#
# Vaatimukset:
#   - Docker käynnissä
#   - .env.local projektin juuressa (JKR_TEST_DB, JKR_TEST_DB_PORT, JKR_TEST_PASSWORD asetettu)
#
# Voit myös ajaa testit suoraan ilman kannan nollaamista:
#   docker compose -f testing.docker-compose.yml --env-file ".env.local" run --rm jkr-core-runner

$ErrorActionPreference = "Stop"

# --- Polut ---
$ScriptDir    = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot  = Resolve-Path (Join-Path $ScriptDir "../..")
$EnvFile      = Join-Path $ProjectRoot ".env.local"
$ComposeFile  = Join-Path $ProjectRoot "testing.docker-compose.yml"

# --- Validoi .env.local ---
if (-not (Test-Path $EnvFile)) {
    Write-Error ".env.local ei löydy: $EnvFile"
    exit 1
}

$EnvVars = @{}
Get-Content $EnvFile | ForEach-Object {
    if ($_ -match "^\s*([^#][^=]*?)\s*=\s*(.*?)\s*$") {
        $EnvVars[$Matches[1]] = $Matches[2]
    }
}

foreach ($var in @("JKR_TEST_DB", "JKR_TEST_DB_PORT", "JKR_TEST_PASSWORD", "JKR_USER")) {
    if (-not $EnvVars.ContainsKey($var) -or $EnvVars[$var] -eq "") {
        Write-Error "Muuttuja $var puuttuu tai on tyhjä .env.local-tiedostossa"
        exit 1
    }
}

$TestDb   = $EnvVars["JKR_TEST_DB"]
$TestPort = $EnvVars["JKR_TEST_DB_PORT"]

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  JKR Testit kontainerissa" -ForegroundColor Cyan
Write-Host "  Kanta : $TestDb (portti $TestPort)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# ============================================================
# [1/2] Nollaa testikanta (poistetaan vanha data)
# ============================================================
Write-Host "`n[1/2] Nollataan testikanta..." -ForegroundColor Yellow

try { docker compose --env-file $EnvFile -f $ComposeFile down -v 2>&1 | Out-Null } catch {}

Write-Host "      Vanha kanta poistettu." -ForegroundColor Gray

# ============================================================
# [2/2] Aja testit kontainerissa
#
# Docker Compose hoitaa ketjun automaattisesti depends_on-ehtojen perusteella:
#   db_test        → käynnistyy, odotetaan healthcheck
#   flyway_test    → ajaa migraatiot (service_healthy)
#   jkr-core-runner → ajaa testit (service_completed_successfully)
# ============================================================
Write-Host "`n[2/2] Käynnistetään testikanta, ajetaan migraatiot ja testit..." -ForegroundColor Yellow
Write-Host "      (Docker Compose hoitaa ketjun: db_test → flyway_test → pytest)`n" -ForegroundColor Gray

docker compose --env-file $EnvFile -f $ComposeFile run --rm jkr-core-runner
$TestExitCode = $LASTEXITCODE

# --- Yhteenveto ---
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($TestExitCode -eq 0) {
    Write-Host "  Kaikki testit lapaisivat!" -ForegroundColor Green
} else {
    Write-Host "  Testejä epäonnistui (exit code $TestExitCode)" -ForegroundColor Red
}
Write-Host "========================================" -ForegroundColor Cyan

# db_test jää pyörimään seuraavaa ajoa varten (nopeutuu); pysäytä manuaalisesti:
Write-Host "  Testikanta pyörii taustalla (sammuta: docker stop jkr_test_database)" -ForegroundColor DarkGray

exit $TestExitCode
