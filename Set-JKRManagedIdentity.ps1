# ==========================================================================
# JKR Tiedonhallinta – Osa 2/2: Managed Identity (Container App)
#
# Mitä tämä tekee:
#   - Ottaa Managed Identityn käyttöön olemassaolevassa Container Appissa
#   - Myöntää SharePoint-kirjoitusoikeuden Managed Identitylle
#   - Poistaa vanhan App Registration -grantin (optional)
#   - Tulostaa ohjeet client secretin poistamiseen prodista
#
# Milloin ajetaan:
#   → Kun Container App on julkaistu prod-ympäristöön
#   → Osa 1 (New-JKRAppRegistration.ps1) pitää olla ajettu ensin
#
# Käyttö:
#   .\Set-JKRManagedIdentity.ps1 `
#       -ContainerAppName "jkr-backend-prod" `
#       -ResourceGroup "rg-jkr-prod" `
#       -SharePointSiteId "contoso.sharepoint.com,xxx,yyy"
#
# Vaatii:
#   - Azure CLI (az) asennettuna
#   - Kirjautunut Contributor + Application Admin -tunnuksilla
#   - Container App oltava olemassa
#   - Osa 1 ajettu (App Registration olemassa)
# ==========================================================================

[CmdletBinding()]
param(
    # Container Appin nimi Azuressa
    [Parameter(Mandatory=$true)]
    [string]$ContainerAppName,

    # Resurssiryhmä jossa Container App sijaitsee
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup,

    # SharePoint Site ID – sama kuin Osa 1:ssä käytettiin
    [Parameter(Mandatory=$true)]
    [string]$SharePointSiteId,

    # SharePoint-kansio (sama kuin Osa 1:ssä)
    [string]$SharePointFolder = "/Shared Documents/JKR-ajot",

    # Poistetaanko vanha App Registration -grant SharePointista
    # Aseta $true kun olet varmistanut että Managed Identity toimii
    [bool]$RemoveOldAppGrant = $false,

    # Vanhan App Registration grantin ID (löytyy Osa 1:n yhteenvedosta)
    [string]$OldGrantId = ""
)

$ErrorActionPreference = "Stop"

# --------------------------------------------------------------------------
# APUFUNKTIOT
# --------------------------------------------------------------------------

function Write-Step([int]$n, [int]$total, [string]$msg) {
    Write-Host "`n$n/$total  $msg" -ForegroundColor Cyan
}
function Write-OK([string]$msg)   { Write-Host "  [OK]  $msg" -ForegroundColor Green }
function Write-Warn([string]$msg) { Write-Host "  [!!]  $msg" -ForegroundColor Yellow }
function Write-Info([string]$msg) { Write-Host "        $msg" -ForegroundColor Gray }
function Write-Fatal([string]$msg) {
    Write-Host "`n[VIRHE] $msg" -ForegroundColor Red
    exit 1
}

function Get-GraphToken {
    $t = az account get-access-token `
        --resource https://graph.microsoft.com `
        --query accessToken -o tsv 2>$null
    if (-not $t) { Write-Fatal "Graph-tokenin haku epäonnistui. Onko az login tehty?" }
    return $t
}

function Invoke-GraphPost([string]$uri, [hashtable]$body) {
    $token = Get-GraphToken
    $tmp = [System.IO.Path]::GetTempFileName() + ".json"
    $body | ConvertTo-Json -Depth 10 | Set-Content -Path $tmp -Encoding UTF8
    $resp = az rest --method POST --uri $uri `
        --headers "Authorization=Bearer $token" "Content-Type=application/json" `
        --body "@$tmp" --output json 2>$null | ConvertFrom-Json
    Remove-Item $tmp -ErrorAction SilentlyContinue
    return $resp
}

function Invoke-GraphDelete([string]$uri) {
    $token = Get-GraphToken
    az rest --method DELETE --uri $uri `
        --headers "Authorization=Bearer $token" | Out-Null
}

# --------------------------------------------------------------------------
# OTSIKKO
# --------------------------------------------------------------------------

Write-Host @"

==========================================================================
  JKR Tiedonhallinta – Osa 2/2: Managed Identity
  Container App: $ContainerAppName
  Resurssiryhmä: $ResourceGroup
==========================================================================
"@ -ForegroundColor White

# --------------------------------------------------------------------------
# ESITARKISTUKSET
# --------------------------------------------------------------------------

$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Fatal "Et ole kirjautunut Azure CLI:hin. Aja ensin: az login"
}

$tenantId      = $account.tenantId
$userPrincipal = $account.user.name

Write-Host "  Tenant:    $tenantId"
Write-Host "  Käyttäjä:  $userPrincipal"
Write-Host ""

# Tarkista että Container App on olemassa
Write-Info "Tarkistetaan Container App..."
$ErrorActionPreference = "SilentlyContinue"
$containerApp = az containerapp show `
    --name $ContainerAppName `
    --resource-group $ResourceGroup `
    --output json 2>$null | ConvertFrom-Json
$ErrorActionPreference = "Stop"

if (-not $containerApp) {
    Write-Fatal "Container Appia '$ContainerAppName' ei löydy resurssiryhmästä '$ResourceGroup'.`nTarkista nimi ja resurssiryhmä."
}

Write-OK "Container App löytyi: $($containerApp.name)"
Write-OK "Sijainti: $($containerApp.location)"
Write-Host ""

$confirm = Read-Host "Jatketaanko? (k/e)"
if ($confirm -notin @("k","K","y","Y")) {
    Write-Host "Keskeytettiin." -ForegroundColor Yellow
    exit 0
}

# --------------------------------------------------------------------------
# VAIHE 1 – Ota Managed Identity käyttöön
# --------------------------------------------------------------------------

Write-Step 1 4 "Otetaan System-assigned Managed Identity käyttöön..."

# Tarkista onko jo päällä
$existingIdentity = $containerApp.identity
if ($existingIdentity -and $existingIdentity.type -match "SystemAssigned") {
    $principalId = $existingIdentity.principalId
    Write-OK "Managed Identity oli jo käytössä"
    Write-OK "Principal ID: $principalId"
} else {
    $identityResult = az containerapp identity assign `
        --name $ContainerAppName `
        --resource-group $ResourceGroup `
        --system-assigned `
        --output json | ConvertFrom-Json

    $principalId = $identityResult.principalId
    Write-OK "Managed Identity otettu käyttöön"
    Write-OK "Principal ID: $principalId"

    Write-Info "Odotetaan identiteetin propagoitumista Azure AD:hen..."
    Start-Sleep -Seconds 15
}

# --------------------------------------------------------------------------
# VAIHE 2 – Varmista Service Principal on olemassa EntraID:ssä
# --------------------------------------------------------------------------

Write-Step 2 4 "Tarkistetaan Service Principal EntraID:ssä..."

$ErrorActionPreference = "SilentlyContinue"
$sp = az ad sp show --id $principalId --output json 2>$null | ConvertFrom-Json
$ErrorActionPreference = "Stop"

if (-not $sp) {
    Write-Warn "Service Principal ei vielä näy – odotetaan lisää..."
    Start-Sleep -Seconds 20
    $ErrorActionPreference = "SilentlyContinue"
    $sp = az ad sp show --id $principalId --output json 2>$null | ConvertFrom-Json
    $ErrorActionPreference = "Stop"
}

if ($sp) {
    Write-OK "Service Principal löytyy: $($sp.displayName)"
} else {
    Write-Warn "Service Principalia ei löydy vielä – SharePoint grant saattaa epäonnistua."
    Write-Info "Voit yrittää uudelleen muutaman minuutin kuluttua."
}

# --------------------------------------------------------------------------
# VAIHE 3 – Myönnä SharePoint-kirjoitusoikeus Managed Identitylle
# --------------------------------------------------------------------------

Write-Step 3 4 "Myönnetään SharePoint-kirjoitusoikeus Managed Identitylle..."

$displayName = "MI: $ContainerAppName"

$grantBody = @{
    roles               = @("write")
    grantedToIdentities = @(@{
        application = @{
            id          = $principalId
            displayName = $displayName
        }
    })
}

$miGrantId = ""
try {
    $grantResp = Invoke-GraphPost `
        "https://graph.microsoft.com/v1.0/sites/$SharePointSiteId/permissions" `
        $grantBody
    $miGrantId = $grantResp.id
    Write-OK "Kirjoitusoikeus myönnetty Managed Identitylle"
    Write-OK "Permission ID: $miGrantId"
} catch {
    Write-Warn "Grantin myöntäminen epäonnistui: $_"
    Write-Info "Varmista että Sites.Selected on admin-consentoitu App Registrationille:"
    Write-Info "https://portal.azure.com"
}

# --------------------------------------------------------------------------
# VAIHE 4 – Poista vanha App Registration -grant (optional)
# --------------------------------------------------------------------------

Write-Step 4 4 "Vanhan App Registration -grantin käsittely..."

if ($RemoveOldAppGrant -and $OldGrantId) {
    Write-Info "Poistetaan vanha grant ID: $OldGrantId"
    try {
        Invoke-GraphDelete `
            "https://graph.microsoft.com/v1.0/sites/$SharePointSiteId/permissions/$OldGrantId"
        Write-OK "Vanha grant poistettu"
    } catch {
        Write-Warn "Vanhan grantin poisto epäonnistui: $_"
        Write-Info "Voit poistaa sen manuaalisesti portaalista."
    }
} elseif ($RemoveOldAppGrant -and -not $OldGrantId) {
    Write-Warn "RemoveOldAppGrant on true mutta OldGrantId puuttuu – ohitetaan."
    Write-Info "Löydät Grant ID:n Osa 1:n yhteenvedosta (jkr-app-registration-prod-*.txt)"
} else {
    Write-Info "Vanhaa grant:ia ei poistettu (RemoveOldAppGrant=$RemoveOldAppGrant)"
    Write-Info "Voit poistaa sen myöhemmin kun olet varmistanut Managed Identityn toimivan:"
    Write-Info ".\Set-JKRManagedIdentity.ps1 ... -RemoveOldAppGrant `$true -OldGrantId <id>"
}

# --------------------------------------------------------------------------
# YHTEENVETO
# --------------------------------------------------------------------------

Write-Host @"

==========================================================================
  VALMIS – Managed Identity konfiguroitu
==========================================================================

  Container App:  $ContainerAppName
  Resurssiryhmä:  $ResourceGroup
  Principal ID:   $principalId

  SharePoint Site ID:     $SharePointSiteId
  SharePoint kansio:      $SharePointFolder
  MI Grant ID:            $miGrantId

==========================================================================
  Backend Python-koodi (prod) – ei secreteja tarvita
==========================================================================

  from azure.identity import ManagedIdentityCredential
  from azure.identity import ChainedTokenCredential, AzureCliCredential

  # Tuotannossa käyttää Managed Identityä automaattisesti
  # Kehityksessä fallback az login -tunnuksille
  credential = ChainedTokenCredential(
      ManagedIdentityCredential(),
      AzureCliCredential()
  )

  # SharePoint-kutsu – ei secreteja, ei token-hallintaa
  token = credential.get_token("https://graph.microsoft.com/.default")

==========================================================================
  Seuraavat askeleet
==========================================================================

  1. Testaa että backend toimii Managed Identityllä:
     - Julkaise uusi versio Container Appista
     - Tarkista logit että SharePoint-kirjoitus onnistuu

  2. Kun toimii, poista client secret prodista:
     .\Set-JKRManagedIdentity.ps1 `
         -ContainerAppName $ContainerAppName `
         -ResourceGroup $ResourceGroup `
         -SharePointSiteId $SharePointSiteId `
         -RemoveOldAppGrant `$true `
         -OldGrantId <osa1-yhteenvedosta>

  3. Poista AZURE_CLIENT_SECRET ympäristömuuttuja Container Appista:
     az containerapp secret remove --name $ContainerAppName ``
         --resource-group $ResourceGroup --secret-names azure-client-secret

  HUOM: Dev- ja test-ympäristöissä client secret voi jäädä käyttöön –
  Managed Identity toimii vain Azuren palveluissa.

==========================================================================
"@ -ForegroundColor Green

# Tallenna yhteenveto
$summaryFile = "jkr-managed-identity-$ContainerAppName.txt"
@"
JKR Managed Identity – yhteenveto
Konfiguroitu: $(Get-Date -Format "yyyy-MM-dd HH:mm")

Container App:  $ContainerAppName
Resurssiryhmä:  $ResourceGroup
Principal ID:   $principalId
Tenant ID:      $tenantId

SharePoint Site ID:  $SharePointSiteId
SharePoint kansio:   $SharePointFolder
MI Grant ID:         $miGrantId
"@ | Set-Content -Path $summaryFile -Encoding UTF8

Write-Host "  Yhteenveto tallennettu: $summaryFile" -ForegroundColor DarkGray
Write-Host ""
