# ==========================================================================
# JKR Tiedonhallinta – Osa 1/2: App Registration
#
# Mitä tämä tekee:
#   - Luo App Registrationin EntraID:hen
#   - Konfiguroi Flutter SPA -kirjautumisen (MSAL, PKCE)
#   - Lisää Graph-oikeudet (User.Read, GroupMember.Read.All)
#   - Lisää Sites.Selected -oikeuden SharePoint-kirjoitusta varten
#   - Luo client secretin dev/test-ympäristöä varten
#   - Myöntää kirjoitusoikeuden valitulle SharePoint-sitelle
#   - Hakee Security Group ID:t automaattisesti
#
# Milloin ajetaan:
#   → Heti, ennen kuin Container App on olemassa
#
# Milloin ajetaan Osa 2:
#   → Kun Container App on julkaistu (prod-ympäristö)
#   → Osa 2 korvaa client secretin Managed Identityllä
#
# Käyttö:
#   .\New-JKRAppRegistration.ps1
#   .\New-JKRAppRegistration.ps1 -Env prod -AppName "JKR Tuotanto"
#   .\New-JKRAppRegistration.ps1 -SharePointSiteId "contoso.sharepoint.com,xxx,yyy"
#
# Vaatii:
#   - Azure CLI (az) asennettuna
#   - Kirjautunut Global Admin tai Application Admin -tunnuksilla
#   - az login tehty oikeaan tenantiin
# ==========================================================================

[CmdletBinding()]
param(
    # Ympäristö – vaikuttaa app-nimeen ja redirect URI:hin
    [ValidateSet("dev","test","prod")]
    [string]$Env = "dev",

    # App Registrationin näyttönimi – oletuksena generoidaan ympäristön mukaan
    [string]$AppName = "",

    # SharePoint-kansio johon background job kirjoittaa
    [string]$SharePointFolder = "/Shared Documents/JKR-ajot",

    # SharePoint Site ID jos tiedossa – muuten näytetään valikko
    [string]$SharePointSiteId = "",

    # Client secretin voimassaolo vuosina
    [int]$SecretYears = 2,

    # Lisää redirect URI:t tuotantodomainille (esim. "https://jkr.contoso.fi")
    [string]$ProductionUrl = ""
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

function Invoke-GraphGet([string]$uri) {
    $token = Get-GraphToken
    $resp = az rest --method GET --uri $uri `
        --headers "Authorization=Bearer $token" `
        --output json 2>$null | ConvertFrom-Json
    return $resp
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

function Invoke-GraphPatch([string]$uri, [hashtable]$body) {
    $token = Get-GraphToken
    $tmp = [System.IO.Path]::GetTempFileName() + ".json"
    $body | ConvertTo-Json -Depth 10 | Set-Content -Path $tmp -Encoding UTF8
    az rest --method PATCH --uri $uri `
        --headers "Authorization=Bearer $token" "Content-Type=application/json" `
        --body "@$tmp" | Out-Null
    Remove-Item $tmp -ErrorAction SilentlyContinue
}

# --------------------------------------------------------------------------
# OTSIKKO
# --------------------------------------------------------------------------

Write-Host @"

==========================================================================
  JKR Tiedonhallinta – Osa 1/2: App Registration
  Ympäristö: $($Env.ToUpper())
==========================================================================
"@ -ForegroundColor White

# --------------------------------------------------------------------------
# ESITARKISTUKSET
# --------------------------------------------------------------------------

$account = az account show 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Fatal "Et ole kirjautunut Azure CLI:hin. Aja ensin: az login"
}

$tenantId = $account.tenantId
$userPrincipal = $account.user.name

# Generoi app-nimi jos ei annettu
if (-not $AppName) {
    $AppName = "JKR Tiedonhallinta $($Env.ToUpper())"
}

# Rakenna redirect URI:t ympäristön mukaan
$redirectUris = @("http://localhost:3000", "http://localhost:8080")
if ($Env -eq "prod" -and $ProductionUrl) {
    $redirectUris += $ProductionUrl
}
if ($Env -eq "test" -and $ProductionUrl) {
    $redirectUris += $ProductionUrl
}

Write-Host "  Tenant:    $tenantId"
Write-Host "  Käyttäjä:  $userPrincipal"
Write-Host "  App nimi:  $AppName"
Write-Host "  Redirect:  $($redirectUris -join ', ')"
Write-Host ""

$confirm = Read-Host "Jatketaanko? (k/e)"
if ($confirm -notin @("k","K","y","Y")) {
    Write-Host "Keskeytettiin." -ForegroundColor Yellow
    exit 0
}

# --------------------------------------------------------------------------
# VAIHE 1 – Luo App Registration
# --------------------------------------------------------------------------

Write-Step 1 9 "Luodaan App Registration '$AppName'..."

$app = az ad app create `
    --display-name $AppName `
    --sign-in-audience "AzureADMyOrg" | ConvertFrom-Json

$appId  = $app.appId
$objId  = $app.id
$scopeId = [guid]::NewGuid().ToString()

Write-OK "App ID (Client ID): $appId"
Write-OK "Object ID:          $objId"

# --------------------------------------------------------------------------
# VAIHE 2 – SPA redirect URI:t, API scope, optional claims
# --------------------------------------------------------------------------

Write-Step 2 9 "Konfiguroidaan SPA, API scope ja optional claims..."

$patchBody = @{
    identifierUris = @("api://$appId")
    spa            = @{ redirectUris = $redirectUris }
    api            = @{
        oauth2PermissionScopes = @(@{
            id                      = $scopeId
            adminConsentDisplayName = "Access JKR API"
            adminConsentDescription = "Allows the user to access JKR Tiedonhallinta API"
            userConsentDisplayName  = "Access JKR API"
            userConsentDescription  = "Allows the user to access JKR Tiedonhallinta API"
            value                   = "access_as_user"
            type                    = "User"
            isEnabled               = $true
        })
    }
    optionalClaims = @{
        accessToken = @(@{
            name                 = "groups"
            essential            = $false
            additionalProperties = @("sam_account_name", "cloud_displayname")
        })
        idToken = @(@{
            name                 = "groups"
            essential            = $false
            additionalProperties = @("sam_account_name", "cloud_displayname")
        })
    }
}

Invoke-GraphPatch "https://graph.microsoft.com/v1.0/applications/$objId" $patchBody
Write-OK "SPA redirect URI:t asetettu"
Write-OK "API scope: api://$appId/access_as_user"
Write-OK "Groups-claim tokenissa"

# --------------------------------------------------------------------------
# VAIHE 3 – Graph-oikeudet
# --------------------------------------------------------------------------

Write-Step 3 9 "Lisätään Graph-oikeudet..."

$GRAPH_API = "00000003-0000-0000-c000-000000000000"

# User.Read (delegated)
az ad app permission add --id $appId `
    --api $GRAPH_API `
    --api-permissions "e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope" | Out-Null

# GroupMember.Read.All (delegated)
az ad app permission add --id $appId `
    --api $GRAPH_API `
    --api-permissions "bc024368-1153-4739-b217-4326f2e966d0=Scope" | Out-Null

# Sites.Selected (application) – background job SharePoint-kirjoitus
az ad app permission add --id $appId `
    --api $GRAPH_API `
    --api-permissions "883ea226-0bf2-4a8f-9f9d-92c9162a727d=Role" | Out-Null

Write-OK "User.Read (delegated)"
Write-OK "GroupMember.Read.All (delegated)"
Write-OK "Sites.Selected (application) – taustatyö SharePoint-kirjoitukseen"

# --------------------------------------------------------------------------
# VAIHE 4 – groupMembershipClaims
# --------------------------------------------------------------------------

Write-Step 4 9 "Asetetaan groupMembershipClaims..."

az ad app update --id $appId `
    --set groupMembershipClaims="SecurityGroup" | Out-Null

Write-OK "Security Group -jäsenyydet tulevat tokeniin"

# --------------------------------------------------------------------------
# VAIHE 5 – Service Principal
# --------------------------------------------------------------------------

Write-Step 5 9 "Luodaan Service Principal..."

$ErrorActionPreference = "SilentlyContinue"
$existingSp = az ad sp show --id $appId 2>$null | ConvertFrom-Json
$ErrorActionPreference = "Stop"

if (-not $existingSp) {
    az ad sp create --id $appId | Out-Null
    Write-OK "Service Principal luotu"
} else {
    Write-OK "Service Principal oli jo olemassa"
}

Write-Info "Odotetaan propagoitumista..."
Start-Sleep -Seconds 5

# --------------------------------------------------------------------------
# VAIHE 6 – Admin consent
# --------------------------------------------------------------------------

Write-Step 6 9 "Myönnetään admin consent..."

$ErrorActionPreference = "SilentlyContinue"
az ad app permission grant `
    --id $appId `
    --api $GRAPH_API `
    --scope "User.Read GroupMember.Read.All" 2>$null | Out-Null

try {
    az ad app permission admin-consent --id $appId 2>$null | Out-Null
    Write-OK "Admin consent myönnetty"
} catch {
    Write-Warn "Admin consent vaatii manuaalisen hyväksynnän portaalissa:"
    Write-Info "https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnAPI/appId/$appId"
}
$ErrorActionPreference = "Stop"

# --------------------------------------------------------------------------
# VAIHE 7 – Client secret
# --------------------------------------------------------------------------

Write-Step 7 9 "Luodaan client secret ($SecretYears vuotta)..."

$secretResult = az ad app credential reset `
    --id $appId `
    --display-name "jkr-$Env-secret" `
    --years $SecretYears `
    --append | ConvertFrom-Json

$clientSecret = $secretResult.password
$secretExpiry = (Get-Date).AddYears($SecretYears).ToString("yyyy-MM-dd")

Write-OK "Client secret luotu (vanhenee $secretExpiry)"
Write-Warn "Tallenna secret heti – sitä ei voi hakea uudelleen!"

if ($Env -eq "prod") {
    Write-Warn "PROD: Harkitse Managed Identityn käyttöä client secretin sijaan."
    Write-Info "Aja Set-JKRManagedIdentity.ps1 kun Container App on julkaistu."
}

# --------------------------------------------------------------------------
# VAIHE 8 – SharePoint site -valinta
# --------------------------------------------------------------------------

Write-Step 8 9 "SharePoint site -valinta..."

if (-not $SharePointSiteId) {
    Write-Info "Haetaan saatavilla olevat SharePoint-sidet..."

    $token = Get-GraphToken
    $sitesResp = az rest --method GET `
        --uri "https://graph.microsoft.com/v1.0/sites?search=*" `
        --headers "Authorization=Bearer $token" `
        --output json 2>$null | ConvertFrom-Json

    $sites = $sitesResp.value

    if (-not $sites -or $sites.Count -eq 0) {
        Write-Warn "SharePoint-sitejä ei löytynyt automaattisesti."
        Write-Info "Voit lisätä grantin myöhemmin parametrilla -SharePointSiteId"
        $SharePointSiteId = Read-Host "  Syötä Site ID manuaalisesti (tai Enter ohittaaksesi)"
    } else {
        Write-Host ""
        Write-Host "  Löytyi $($sites.Count) SharePoint-siteä:" -ForegroundColor White
        Write-Host ""

        for ($i = 0; $i -lt $sites.Count; $i++) {
            $s = $sites[$i]
            Write-Host "  [$($i+1)] $($s.displayName)" -ForegroundColor White
            Write-Host "      URL: $($s.webUrl)" -ForegroundColor Gray
            Write-Host "      ID:  $($s.id)" -ForegroundColor DarkGray
            Write-Host ""
        }
        Write-Host "  [0] Ohita – lisätään myöhemmin" -ForegroundColor DarkGray
        Write-Host ""

        do {
            $raw = Read-Host "  Valitse numero (0-$($sites.Count))"
            $choice = [int]$raw
        } while ($choice -lt 0 -or $choice -gt $sites.Count)

        if ($choice -eq 0) {
            Write-Warn "SharePoint site -grant ohitettu."
            Write-Info "Lisää myöhemmin ajamalla skripti uudelleen -SharePointSiteId parametrilla."
            $SharePointSiteId = ""
        } else {
            $sel = $sites[$choice - 1]
            $SharePointSiteId = $sel.id
            Write-OK "Valittu: $($sel.displayName)"
            Write-OK "Site ID: $SharePointSiteId"
        }
    }
} else {
    Write-OK "Käytetään annettua Site ID:tä: $SharePointSiteId"
}

# --------------------------------------------------------------------------
# VAIHE 9 – SharePoint grant
# --------------------------------------------------------------------------

Write-Step 9 9 "Myönnetään kirjoitusoikeus SharePoint-siteen..."

$spGrantId = ""
if ($SharePointSiteId) {
    $grantBody = @{
        roles               = @("write")
        grantedToIdentities = @(@{
            application = @{
                id          = $appId
                displayName = $AppName
            }
        })
    }

    try {
        $grantResp = Invoke-GraphPost `
            "https://graph.microsoft.com/v1.0/sites/$SharePointSiteId/permissions" `
            $grantBody
        $spGrantId = $grantResp.id
        Write-OK "Kirjoitusoikeus myönnetty"
        Write-OK "Permission ID: $spGrantId"
    } catch {
        Write-Warn "Grantin myöntäminen epäonnistui: $_"
        Write-Warn "Varmista Sites.Selected admin consent portaalissa ja aja uudelleen."
    }
} else {
    Write-Warn "SharePoint grant ohitettu"
}

# --------------------------------------------------------------------------
# Security Group ID:t
# --------------------------------------------------------------------------

$ErrorActionPreference = "SilentlyContinue"
$adminGroupId  = az ad group show --group "sg-jkr-admin-sql"  --query id -o tsv 2>$null
$viewerGroupId = az ad group show --group "sg-jkr-viewer-sql" --query id -o tsv 2>$null
$ErrorActionPreference = "Stop"
if (-not $adminGroupId)  { $adminGroupId  = "<EI LÖYTYNYT – lisää manuaalisesti>" }
if (-not $viewerGroupId) { $viewerGroupId = "<EI LÖYTYNYT – lisää manuaalisesti>" }

# --------------------------------------------------------------------------
# YHTEENVETO
# --------------------------------------------------------------------------

$spSiteDisplay   = if ($SharePointSiteId) { $SharePointSiteId } else { "<ei asetettu>" }
$spGrantDisplay  = if ($spGrantId)        { $spGrantId }        else { "<ei asetettu>" }

Write-Host @"

==========================================================================
  VALMIS – Yhteenveto ($($Env.ToUpper()))
==========================================================================

  App nimi:      $AppName
  Client ID:     $appId
  Tenant ID:     $tenantId
  Object ID:     $objId
  Ympäristö:     $Env

  API Scope:     api://$appId/access_as_user
  Client Secret: $clientSecret
  Secret expiry: $secretExpiry

  SharePoint Site ID:  $spSiteDisplay
  SharePoint kansio:   $SharePointFolder
  SharePoint Grant ID: $spGrantDisplay

  Admin Group:   $adminGroupId
  Viewer Group:  $viewerGroupId

==========================================================================
  Backend .env ($Env)
==========================================================================

  AZURE_TENANT_ID=$tenantId
  AZURE_CLIENT_ID=$appId
  AZURE_CLIENT_SECRET=$clientSecret
  AZURE_ADMIN_GROUP_ID=$adminGroupId
  AZURE_VIEWER_GROUP_ID=$viewerGroupId
  SHAREPOINT_SITE_ID=$spSiteDisplay
  SHAREPOINT_FOLDER=$SharePointFolder

==========================================================================
  Flutter-konfiguraatio
==========================================================================

  clientId:  $appId
  tenantId:  $tenantId
  scopes:    ['api://$appId/access_as_user']

==========================================================================
  Seuraavat askeleet
==========================================================================

  1. Tallenna client secret salasananhallintaan (Azure Key Vault tai vastaava)

  2. Tarkista admin consent portaalissa jos yllä tuli varoitus:
     https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationMenuBlade/~/CallAnAPI/appId/$appId

  3. Lisää tuotannon redirect URI tarvittaessa:
     .\New-JKRAppRegistration.ps1 -Env prod -ProductionUrl https://jkr.contoso.fi

  4. KUN Container App on julkaistu (prod), aja Osa 2:
     .\Set-JKRManagedIdentity.ps1 -ContainerAppName <nimi> -ResourceGroup rg-jkr-prod -SharePointSiteId $spSiteDisplay
     → Tämä korvaa client secretin Managed Identityllä prodissa

==========================================================================
"@ -ForegroundColor Green

# Tallenna yhteenveto tiedostoon (ilman secretia)
$summaryFile = "jkr-app-registration-$Env-$appId.txt"
@"
JKR App Registration – yhteenveto
Luotu:     $(Get-Date -Format "yyyy-MM-dd HH:mm")
Ympäristö: $Env

App nimi:      $AppName
Client ID:     $appId
Tenant ID:     $tenantId
Object ID:     $objId
Secret expiry: $secretExpiry

SharePoint Site ID:  $spSiteDisplay
SharePoint kansio:   $SharePointFolder
SharePoint Grant ID: $spGrantDisplay

Admin Group:   $adminGroupId
Viewer Group:  $viewerGroupId

HUOM: Client secret näkyy vain skriptin ajohetkellä.
Tallenna se Azure Key Vaultiin tai muuhun salasananhallintaan.

Seuraava vaihe (prod): .\Set-JKRManagedIdentity.ps1
"@ | Set-Content -Path $summaryFile -Encoding UTF8

Write-Host "  Yhteenveto tallennettu: $summaryFile" -ForegroundColor DarkGray
Write-Host ""
