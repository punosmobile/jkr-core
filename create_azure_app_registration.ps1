# ==========================================================================
# JKR Tiedonhallinta – Azure AD App Registration
#
# Luo App Registrationin joka palvelee sekä:
#   - Flutter-frontendia (public client, MSAL-kirjautuminen)
#   - Python FastAPI -backendia (token-validointi)
#
# Käyttö:
#   .\create_azure_app_registration.ps1
#
# Vaatii: Azure CLI (az) kirjautuneena admin-tunnuksilla
# ==========================================================================

# 1. Luo App Registration
#    - sign-in-audience: vain oman organisaation käyttäjät
#    - Flutter käyttää MSAL:ia → tarvitsee SPA redirect URI:t
$app = az ad app create `
    --display-name "Tiedonhallinta Development" `
    --sign-in-audience "AzureADMyOrg" | ConvertFrom-Json

$appId = $app.appId
Write-Host "App ID (Client ID): $appId"

# 2. Aseta SPA redirect URI:t (Flutter web + dev)
#    HUOM: Flutter mobile käyttää MSAL:n brokeria, ei tarvitse erillistä redirect URI:a
az ad app update --id $appId `
    --spa-redirect-uris "http://localhost:3000" "http://localhost:8080" "msauth://com.example.jkr/callback"

# 3. Salli public client -virta (Flutter mobile MSAL tarvitsee tämän)
az ad app update --id $appId `
    --is-fallback-public-client true

# 4. Lisää Microsoft Graph -oikeudet
#    User.Read (delegated) – käyttäjän perustiedot
az ad app permission add --id $appId `
    --api 00000003-0000-0000-c000-000000000000 `
    --api-permissions e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope

#    GroupMember.Read.All (delegated) – käyttäjän ryhmäjäsenyydet
az ad app permission add --id $appId `
    --api 00000003-0000-0000-c000-000000000000 `
    --api-permissions bc024368-1153-4739-b217-4326f2e966d0=Scope

# 5. Sisällytä Security Group -jäsenyydet tokeniin (groups-claim)
#    Backend tarkistaa sg-jkr-admin-sql / sg-jkr-viewer-sql Object ID:t tokenista
az ad app update --id $appId `
    --set groupMembershipClaims="SecurityGroup"

# 6. Määritä API scope jota Flutter pyytää tokenissa
#    Luo "access_as_user" scope → Flutter pyytää: api://<clientId>/access_as_user
$scopeId = [guid]::NewGuid().ToString()
$apiBody = @{
    identifierUris = @("api://$appId")
    api            = @{
        oauth2PermissionScopes = @(
            @{
                id                      = $scopeId
                adminConsentDisplayName = "Käytä JKR API:a"
                adminConsentDescription = "Sallii käyttäjän käyttää JKR Tiedonhallinta API:a"
                userConsentDisplayName  = "Käytä JKR API:a"
                userConsentDescription  = "Sallii käyttäjän käyttää JKR Tiedonhallinta API:a"
                value                   = "access_as_user"
                type                    = "User"
                isEnabled               = $true
            }
        )
    }
} | ConvertTo-Json -Depth 5 -Compress

az rest --method PATCH `
    --uri "https://graph.microsoft.com/v1.0/applications/$($app.id)" `
    --headers "Content-Type=application/json" `
    --body $apiBody

# 7. Myönnä admin consent (vaatii admin-oikeudet)
az ad app permission admin-consent --id $appId

# 8. Luo Service Principal
az ad sp create --id $appId

# 9. Tulosta yhteenveto
$tenantId = az account show --query tenantId -o tsv

Write-Host "`n=========================================="
Write-Host "Valmis! Yhteenveto:"
Write-Host "=========================================="
Write-Host "Client ID:    $appId"
Write-Host "Tenant ID:    $tenantId"
Write-Host "API Scope:    api://$appId/access_as_user"
Write-Host ""
Write-Host "Backend-ympäristömuuttujat (.env):"
Write-Host "  AZURE_TENANT_ID=$tenantId"
Write-Host "  AZURE_CLIENT_ID=$appId"
Write-Host "  AZURE_ADMIN_GROUP_ID=<sg-jkr-admin-sql Object ID>"
Write-Host "  AZURE_VIEWER_GROUP_ID=<sg-jkr-viewer-sql Object ID>"
Write-Host ""
Write-Host "Flutter-konfiguraatio:"
Write-Host "  clientId: $appId"
Write-Host "  tenantId: $tenantId"
Write-Host "  scopes: ['api://$appId/access_as_user']"
Write-Host ""
Write-Host "HUOM: Hae Security Group Object ID:t komennolla:"
Write-Host "  az ad group show --group 'sg-jkr-admin-sql' --query id -o tsv"
Write-Host "  az ad group show --group 'sg-jkr-viewer-sql' --query id -o tsv"