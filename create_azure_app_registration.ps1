# 1. Luo App Registration
$app = az ad app create `
    --display-name "Tiedonhallinta Development" `
    --web-redirect-uris "http://localhost:8000/auth" `
    --sign-in-audience "AzureADMyOrg" | ConvertFrom-Json

$appId = $app.appId
Write-Host "App ID (Client ID): $appId"

# 2. Luo Client Secret (oletuksena 2v voimassa)
$secret = az ad app credential reset `
    --id $appId `
    --append `
    --display-name "dev-secret" | ConvertFrom-Json

Write-Host "Client Secret: $($secret.password)"
Write-Host "TALLENNA SECRET NYT - sitä ei voi lukea enää myöhemmin!"

# 3. Lisää Microsoft Graph -oikeudet
#    User.Read (delegated) - käyttäjän perustiedot
az ad app permission add --id $appId `
    --api 00000003-0000-0000-c000-000000000000 `
    --api-permissions e1fe6dd8-ba31-4d61-89e7-88639da4683d=Scope

#    GroupMember.Read.All (delegated) - käyttäjän ryhmäjäsenyydet
az ad app permission add --id $appId `
    --api 00000003-0000-0000-c000-000000000000 `
    --api-permissions bc024368-1153-4739-b217-4326f2e966d0=Scope

az ad app update --id $appId `
    --set groupMembershipClaims="SecurityGroup"


# 4. Myönnä admin consent (vaatii admin-oikeudet)
az ad app permission admin-consent --id $appId

# 5. Luo Service Principal
az ad sp create --id $appId

Write-Host "`nValmis! Yhteenveto:"
Write-Host "Client ID:  $appId"
Write-Host "Tenant ID:  $(az account show --query tenantId -o tsv)"