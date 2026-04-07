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
    [ValidateSet("dev", "test", "prod")]
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
function Write-OK([string]$msg) { Write-Host "  [OK]  $msg" -ForegroundColor Green }
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
if ($confirm -notin @("k", "K", "y", "Y")) {
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

$appId = $app.appId
$objId = $app.id
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
        idToken     = @(@{
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
}
else {
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
    Write-Info "Odotetaan consentin propagoitumista (10s)..."
    Start-Sleep -Seconds 10
}
catch {
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
    Write-Host ""
    Write-Host "  SharePoint Site ID:tä ei annettu parametrina." -ForegroundColor White
    Write-Host "  Voit syöttää joko:" -ForegroundColor Gray
    Write-Host "    1) Site ID suoraan (esim. contoso.sharepoint.com,guid1,guid2)" -ForegroundColor Gray
    Write-Host "    2) SharePoint-siten URL (esim. https://contoso.sharepoint.com/sites/MySite)" -ForegroundColor Gray
    Write-Host "    3) Tyhjä (Enter) ohittaaksesi" -ForegroundColor Gray
    Write-Host ""

    $siteInput = Read-Host "  Syötä Site ID tai URL"

    if ($siteInput -match "^https?://") {
        Write-Info "Haetaan Site ID URL:n perusteella..."
        try {
            $uri = [System.Uri]$siteInput
            $hostname = $uri.Host
            $sitePath = $uri.AbsolutePath.TrimEnd('/')
            $graphUri = "https://graph.microsoft.com/v1.0/sites/${hostname}:${sitePath}"

            $token = Get-GraphToken
            $siteResp = az rest --method GET `
                --uri $graphUri `
                --headers "Authorization=Bearer $token" `
                --output json 2>$null | ConvertFrom-Json

            $SharePointSiteId = $siteResp.id
            Write-OK "Site löytyi: $($siteResp.displayName)"
            Write-OK "Site ID: $SharePointSiteId"
        }
        catch {
            Write-Warn "Siten haku epäonnistui: $_"
            Write-Info "Voit lisätä grantin myöhemmin parametrilla -SharePointSiteId"
            $SharePointSiteId = ""
        }
    }
    elseif ($siteInput) {
        $SharePointSiteId = $siteInput
        Write-OK "Käytetään annettua Site ID:tä: $SharePointSiteId"
    }
    else {
        Write-Warn "SharePoint site -grant ohitettu."
        Write-Info "Lisää myöhemmin ajamalla skripti uudelleen -SharePointSiteId parametrilla."
        $SharePointSiteId = ""
    }
}
else {
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
        # Site permission grant vaatii Sites.FullControl.All -oikeuden.
        # Azure CLI:n tokenissa ei ole tätä scopea, joten käytetään
        # device code flow -kirjautumista Graph CLI:n well-known app ID:llä.
        # Ei vaadi lisämoduuleja – toimii pelkällä Invoke-RestMethod:llä.
        $graphCliClientId = "14d82eec-204b-4c2f-b7e8-296a70dab67e"
        $deviceScope = "https://graph.microsoft.com/Sites.FullControl.All offline_access"

        Write-Info "Käynnistetään device code -kirjautuminen..."
        $deviceResp = Invoke-RestMethod -Method POST `
            -Uri "https://login.microsoftonline.com/$tenantId/oauth2/v2.0/devicecode" `
            -ContentType "application/x-www-form-urlencoded" `
            -Body "client_id=$graphCliClientId&scope=$([uri]::EscapeDataString($deviceScope))"

        Write-Host ""
        Write-Host "  $($deviceResp.message)" -ForegroundColor Yellow
        Write-Host ""

        # Pollaa token-endpointia kunnes käyttäjä kirjautuu
        $pollBody = "client_id=$graphCliClientId&grant_type=urn:ietf:params:oauth:grant-type:device_code&device_code=$($deviceResp.device_code)"
        $pollInterval = [math]::Max($deviceResp.interval, 5)
        $deadline = (Get-Date).AddSeconds($deviceResp.expires_in)
        $dcToken = $null

        while ((Get-Date) -lt $deadline) {
            Start-Sleep -Seconds $pollInterval
            try {
                $tokenResp = Invoke-RestMethod -Method POST `
                    -Uri "https://login.microsoftonline.com/$tenantId/oauth2/v2.0/token" `
                    -ContentType "application/x-www-form-urlencoded" `
                    -Body $pollBody
                $dcToken = $tokenResp.access_token
                break
            }
            catch {
                $errBody = $_.ErrorDetails.Message | ConvertFrom-Json -ErrorAction SilentlyContinue
                if ($errBody.error -eq "authorization_pending") {
                    continue
                }
                elseif ($errBody.error -eq "slow_down") {
                    $pollInterval += 5
                    continue
                }
                else {
                    throw $_
                }
            }
        }

        if (-not $dcToken) {
            throw "Kirjautuminen aikakatkaistiin tai epäonnistui."
        }

        Write-OK "Kirjautuminen onnistui (Sites.FullControl.All)"

        $grantJson = $grantBody | ConvertTo-Json -Depth 10
        $grantResp = Invoke-RestMethod -Method POST `
            -Uri "https://graph.microsoft.com/v1.0/sites/$SharePointSiteId/permissions" `
            -Headers @{ Authorization = "Bearer $dcToken" } `
            -ContentType "application/json" `
            -Body ([System.Text.Encoding]::UTF8.GetBytes($grantJson))

        $spGrantId = $grantResp.id
        Write-OK "Kirjoitusoikeus myönnetty"
        Write-OK "Permission ID: $spGrantId"
    }
    catch {
        $errMsg = $_.ToString()
        Write-Warn "Grantin myöntäminen epäonnistui: $errMsg"
        Write-Host ""
        Write-Info "Voit myöntää grantin manuaalisesti Graph Explorerilla:"
        Write-Info "  https://developer.microsoft.com/en-us/graph/graph-explorer"
        Write-Info "  POST https://graph.microsoft.com/v1.0/sites/$SharePointSiteId/permissions"
        Write-Info "  Content-Type: application/json"
        Write-Host ""
        $grantJson = $grantBody | ConvertTo-Json -Depth 10 -Compress
        Write-Info "Body: $grantJson"
        Write-Host ""
        Write-Info "Voit myöntää grantin myöhemmin ajamalla skriptin uudelleen -SharePointSiteId parametrilla."
    }
}
else {
    Write-Warn "SharePoint grant ohitettu"
}

# --------------------------------------------------------------------------
# Security Group ID:t
# --------------------------------------------------------------------------

$ErrorActionPreference = "SilentlyContinue"
$adminGroupId = az ad group show --group "sg-jkr-admin-sql"  --query id -o tsv 2>$null
$viewerGroupId = az ad group show --group "sg-jkr-viewer-sql" --query id -o tsv 2>$null
$ErrorActionPreference = "Stop"
if (-not $adminGroupId) { $adminGroupId = "<NOT FOUND - add manually>" }
if (-not $viewerGroupId) { $viewerGroupId = "<NOT FOUND - add manually>" }

# --------------------------------------------------------------------------
# YHTEENVETO
# --------------------------------------------------------------------------

$spSiteDisplay = $(if ($SharePointSiteId) { $SharePointSiteId } else { "<ei asetettu>" })
$spGrantDisplay = $(if ($spGrantId) { $spGrantId } else { "<ei asetettu>" })

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
