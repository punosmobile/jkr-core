# ==========================================================================
# JKR Tiedonhallinta – Azure AD App Registration
#
# Luo App Registrationin joka palvelee:
#   - Flutter web -frontendia (SPA, MSAL-kirjautuminen)
#   - Python FastAPI -backendia (token-validointi)
#
# Ei client secretia – Flutter web kayttaa SPA-virtaa (Authorization Code + PKCE)
#
# Kaytto:
#   .\create_azure_app_registration.ps1
#
# Vaatii: Azure CLI (az) kirjautuneena admin-tunnuksilla
# ==========================================================================

$ErrorActionPreference = "Stop"

# 1. Luo App Registration
#    - sign-in-audience: vain oman organisaation kayttajat
Write-Host "1/8 Luodaan App Registration..." -ForegroundColor Cyan
$app = az ad app create `
    --display-name "Tiedonhallinta Development" `
    --sign-in-audience "AzureADMyOrg" | ConvertFrom-Json

$appId = $app.appId
$objectId = $app.id
Write-Host "  App ID (Client ID): $appId"
Write-Host "  Object ID: $objectId"

# 2. Aseta SPA redirect URI:t ja API scope Graph API:lla
#    az ad app update ei tue --spa-redirect-uris, joten kaytetaan az rest + Graph API:a.
#    Kirjoitetaan JSON temp-tiedostoon jotta PowerShell ei sotke escapeja.
Write-Host "2/8 Asetetaan SPA redirect URI:t ja API scope..." -ForegroundColor Cyan
$scopeId = [guid]::NewGuid().ToString()
$tempFile = [System.IO.Path]::GetTempFileName()

$jsonContent = @"
{
  "identifierUris": ["api://$appId"],
  "spa": {
    "redirectUris": ["http://localhost:3000", "http://localhost:8080"]
  },
  "api": {
    "oauth2PermissionScopes": [
      {
        "id": "$scopeId",
        "adminConsentDisplayName": "Access JKR API",
        "adminConsentDescription": "Allows the user to access JKR Tiedonhallinta API",
        "userConsentDisplayName": "Access JKR API",
        "userConsentDescription": "Allows the user to access JKR Tiedonhallinta API",
        "value": "access_as_user",
        "type": "User",
        "isEnabled": true
      }
    ]
  },
  "optionalClaims": {
    "accessToken": [
      {
        "name": "groups",
        "essential": false,
        "additionalProperties": ["sam_account_name", "cloud_displayname"]
      }
    ],
    "idToken": [
      {
        "name": "groups",
        "essential": false,
        "additionalProperties": ["sam_account_name", "cloud_displayname"]
      }
    ]
  }
}
"@

Set-Content -Path $tempFile -Value $jsonContent -Encoding UTF8

az rest --method PATCH `
    --uri "https://graph.microsoft.com/v1.0/applications/$objectId" `
    --headers "Content-Type=application/json" `
    --body "@$tempFile"

Remove-Item $tempFile -ErrorAction SilentlyContinue

# 3. Lisaa Microsoft Graph -oikeudet
#    User.Read (delegated) – kayttajan perustiedot
Write-Host "3/8 Lisataan Graph-oikeudet..." -ForegroundColor Cyan
az ad app permission add --id $appId `
    --api 00000003-0000-0000-c000-000000000000 `
    --api-permissions e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope

#    GroupMember.Read.All (delegated) – kayttajan ryhmajasenydet
az ad app permission add --id $appId `
    --api 00000003-0000-0000-c000-000000000000 `
    --api-permissions bc024368-1153-4739-b217-4326f2e966d0=Scope

# 4. Sisallyta Security Group -jasenydet tokeniin (groups-claim)
#    Backend tarkistaa sg-jkr-admin-sql / sg-jkr-viewer-sql Object ID:t tokenista
Write-Host "4/8 Asetetaan groupMembershipClaims..." -ForegroundColor Cyan
az ad app update --id $appId `
    --set groupMembershipClaims="SecurityGroup"

# 5. Luo Service Principal (vaaditaan ennen permission grant:ia)
Write-Host "5/8 Luodaan Service Principal..." -ForegroundColor Cyan
$ErrorActionPreference = "SilentlyContinue"
$existingSp = az ad sp show --id $appId 2>$null
$ErrorActionPreference = "Stop"
if (-not $existingSp) {
    az ad sp create --id $appId | Out-Null
    Write-Host "  Service Principal luotu."
}
else {
    Write-Host "  Service Principal on jo olemassa, ohitetaan."
}

# 6. Myonna admin consent Graph-oikeuksille (vaatii admin-oikeudet)
#    permission grant luo OAuth2-consentobjektin (AllPrincipals) suoraan.
#    admin-consent ei toimi SP:n kanssa joka on juuri luotu (tunnettu bugi).
Write-Host "6/8 Myonnetaan admin consent..." -ForegroundColor Cyan
$ErrorActionPreference = "SilentlyContinue"
az ad app permission grant --id $appId `
    --api 00000003-0000-0000-c000-000000000000 `
    --scope "User.Read GroupMember.Read.All" 2>$null | Out-Null
$ErrorActionPreference = "Stop"
Write-Host "  Admin consent myonnetty (User.Read, GroupMember.Read.All)."

# 7. Hae Security Group Object ID:t
Write-Host "7/8 Haetaan Security Group ID:t..." -ForegroundColor Cyan
$ErrorActionPreference = "SilentlyContinue"
$adminGroupId = az ad group show --group "sg-jkr-admin-sql" --query id -o tsv 2>$null
$viewerGroupId = az ad group show --group "sg-jkr-viewer-sql" --query id -o tsv 2>$null
$ErrorActionPreference = "Stop"

if (-not $adminGroupId) {
    Write-Host "  VAROITUS: Ryhmaa 'sg-jkr-admin-sql' ei loydy!" -ForegroundColor Yellow
    $adminGroupId = "<EI LOYTYNYT - aseta manuaalisesti>"
}
if (-not $viewerGroupId) {
    Write-Host "  VAROITUS: Ryhmaa 'sg-jkr-viewer-sql' ei loydy!" -ForegroundColor Yellow
    $viewerGroupId = "<EI LOYTYNYT - aseta manuaalisesti>"
}

# 8. Tulosta yhteenveto
$tenantId = az account show --query tenantId -o tsv

Write-Host "`n==========================================" -ForegroundColor Green
Write-Host "8/8 Valmis! Yhteenveto:" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Client ID:    $appId"
Write-Host "Tenant ID:    $tenantId"
Write-Host "API Scope:    api://$appId/access_as_user"
Write-Host "Admin Group:  $adminGroupId (sg-jkr-admin-sql)"
Write-Host "Viewer Group: $viewerGroupId (sg-jkr-viewer-sql)"
Write-Host ""
Write-Host "Backend-ymparistomuuttujat (.env):"
Write-Host "  AZURE_TENANT_ID=$tenantId"
Write-Host "  AZURE_CLIENT_ID=$appId"
Write-Host "  AZURE_ADMIN_GROUP_ID=$adminGroupId"
Write-Host "  AZURE_VIEWER_GROUP_ID=$viewerGroupId"
Write-Host ""
Write-Host "Flutter-konfiguraatio:"
Write-Host "  clientId: $appId"
Write-Host "  tenantId: $tenantId"
Write-Host "  scopes: ['api://$appId/access_as_user']"