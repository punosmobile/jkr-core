# run_tests.ps1
# Nollaa testikanta ja ajaa testit kontainerissa.
#
# Kaytto:
#   .\tests\scripts\run_tests.ps1            # Interaktiivinen valikko
#   .\tests\scripts\run_tests.ps1 --all      # Aja kaikki testit suoraan
#   .\tests\scripts\run_tests.ps1 --test test_kompostori  # Aja yksittainen testi
#
# Vaatimukset:
#   - Docker kaynnissa
#   - .env.local projektin juuressa (JKR_TEST_DB, JKR_TEST_DB_PORT, JKR_TEST_PASSWORD asetettu)

param(
    [switch]$All,
    [string]$Test
)

$ErrorActionPreference = 'Stop'

# --- Polut ---
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Resolve-Path (Join-Path $ScriptDir '../..')
$EnvFile = Join-Path $ProjectRoot '.env.local'
$ComposeFile = Join-Path $ProjectRoot 'testing.docker-compose.yml'
$TestsDir = Join-Path $ProjectRoot 'tests'

# --- Validoi .env.local ---
if (-not (Test-Path $EnvFile)) {
    Write-Error ".env.local not found: $EnvFile"
    exit 1
}

$EnvVars = @{}
Get-Content $EnvFile | ForEach-Object {
    if ($_ -match '^\s*([^#][^=]*?)\s*=\s*(.*?)\s*$') {
        $EnvVars[$Matches[1]] = $Matches[2]
    }
}

foreach ($var in @('JKR_TEST_DB', 'JKR_TEST_DB_PORT', 'JKR_TEST_PASSWORD', 'JKR_USER')) {
    if (-not $EnvVars.ContainsKey($var) -or $EnvVars[$var] -eq '') {
        Write-Error "Variable $var missing or empty in .env.local"
        exit 1
    }
}

$TestDb = $EnvVars['JKR_TEST_DB']
$TestPort = $EnvVars['JKR_TEST_DB_PORT']

# --- Hae testitiedostot ---
$TestFiles = Get-ChildItem -Path $TestsDir -Filter 'test_*.py' -File |
Sort-Object Name |
ForEach-Object { $_.BaseName }

# --- Valitse ajettava testi ---
if ($All) {
    $PytestTarget = 'tests/'
    $RunLabel = 'Kaikki testit'
}
elseif ($Test -ne '') {
    $TestName = $Test
    if (-not $TestName.StartsWith('test_')) { $TestName = "test_$TestName" }
    if (-not ($TestFiles -contains $TestName)) {
        Write-Host ''
        Write-Host "Testitiedostoa '${TestName}.py' ei loydy." -ForegroundColor Red
        Write-Host ''
        Write-Host 'Saatavilla olevat testit:' -ForegroundColor Yellow
        foreach ($tf in $TestFiles) { Write-Host "  $tf" }
        exit 1
    }
    $PytestTarget = "tests/${TestName}.py"
    $RunLabel = $TestName
}
else {
    # --- Interaktiivinen valikko ---
    Write-Host ''
    Write-Host '========================================' -ForegroundColor Cyan
    Write-Host '  JKR Testivalikko' -ForegroundColor Cyan
    Write-Host "  Kanta : $TestDb (portti $TestPort)" -ForegroundColor Cyan
    Write-Host '========================================' -ForegroundColor Cyan
    Write-Host ''
    Write-Host '  0) Kaikki testit' -ForegroundColor White

    for ($i = 0; $i -lt $TestFiles.Count; $i++) {
        $num = $i + 1
        Write-Host "  ${num}) $($TestFiles[$i])" -ForegroundColor White
    }

    Write-Host ''
    $Choice = Read-Host 'Valitse testi [0 = kaikki] (oletus: 0)'
    if ($Choice -eq '' -or $Choice -eq '0') {
        $PytestTarget = 'tests/'
        $RunLabel = 'Kaikki testit'
    }
    elseif ($Choice -match '^\d+$') {
        $idx = [int]$Choice - 1
        if ($idx -lt 0 -or $idx -ge $TestFiles.Count) {
            Write-Host "Virheellinen valinta: $Choice" -ForegroundColor Red
            exit 1
        }
        $PytestTarget = "tests/$($TestFiles[$idx]).py"
        $RunLabel = $TestFiles[$idx]
    }
    else {
        Write-Host "Virheellinen valinta: $Choice" -ForegroundColor Red
        exit 1
    }
}

Write-Host ''
Write-Host '========================================' -ForegroundColor Cyan
Write-Host '  JKR Testit kontainerissa' -ForegroundColor Cyan
Write-Host "  Kanta : $TestDb (portti $TestPort)" -ForegroundColor Cyan
Write-Host "  Kohde : $RunLabel" -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan

# ============================================================
# [1/2] Nollaa testikanta
# ============================================================
Write-Host ''
Write-Host '[1/2] Nollataan testikanta...' -ForegroundColor Yellow

try { docker compose --env-file $EnvFile -f $ComposeFile down -v 2>&1 | Out-Null } catch {}

Write-Host '      Vanha kanta poistettu.' -ForegroundColor Gray

# ============================================================
# [2/2] Aja testit kontainerissa
# ============================================================
Write-Host ''
Write-Host '[2/2] Kaynnistetaan testikanta, ajetaan migraatiot ja testit...' -ForegroundColor Yellow
Write-Host '      (Docker Compose: db_test -> flyway_test -> pytest)' -ForegroundColor Gray
Write-Host ''

$PytestCmd = "cd /app && poetry install --no-root -q && poetry run python -m pytest $PytestTarget -v"
docker compose --env-file $EnvFile -f $ComposeFile run --rm jkr-core-runner bash -c $PytestCmd
$TestExitCode = $LASTEXITCODE

# --- Yhteenveto ---
Write-Host ''
Write-Host '========================================' -ForegroundColor Cyan
if ($TestExitCode -eq 0) {
    Write-Host "  $RunLabel - OK!" -ForegroundColor Green
}
else {
    Write-Host "  $RunLabel - FAILED (exit code $TestExitCode)" -ForegroundColor Red
}
Write-Host '========================================' -ForegroundColor Cyan
Write-Host '  Testikanta pyorii taustalla (sammuta: docker stop jkr_test_database)' -ForegroundColor DarkGray

exit $TestExitCode
