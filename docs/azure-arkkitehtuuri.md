# JKR Tiedonhallinta – Azure-arkkitehtuuri

**Versio:** 1.0  
**Päivitetty:** 2026-04-03  
**Tila:** Tavoitearkkitehtuurikuvaus (ehdotus)

---

## Sisällysluettelo

1. [Yleiskuvaus](#1-yleiskuvaus)
2. [Azure-resurssit – täydellinen lista](#2-azure-resurssit--täydellinen-lista)
3. [Verkkoarkkitehtuuri](#3-verkkoarkkitehtuuri)
4. [Autentikointi ja valtuutus](#4-autentikointi-ja-valtuutus)
5. [Tietokanta-arkkitehtuuri](#5-tietokanta-arkkitehtuuri)
6. [CI/CD – Self-hosted runner](#6-cicd--self-hosted-runner)
7. [Frontend-arkkitehtuuri](#7-frontend-arkkitehtuuri)
8. [Salaisuuksien hallinta](#8-salaisuuksien-hallinta)
9. [Havainnointi ja lokitus](#9-havainnointi-ja-lokitus)
10. [Ympäristöjen väliset erot](#10-ympäristöjen-väliset-erot)
11. [Parannusehdotukset ja avoimet kysymykset](#11-parannusehdotukset-ja-avoimet-kysymykset)
12. [Käyttöönottojärjestys](#12-käyttöönottojärjestys)

---

## 1. Yleiskuvaus

JKR (Jätekuljetusrekisteri) Tiedonhallinta on web-pohjainen sovellus jätteenkuljetusrekisterin tiedonhallintaan. Järjestelmä koostuu:

- **Backend:** Python FastAPI -sovellus (jkr-core-development) – Azure Container App
- **Frontend:** Flutter web -sovellus (jkrfront) – Azure Container App (nginx-kontti)
- **Tietokanta:** Azure Database for PostgreSQL Flexible Server (PostGIS + pgaudit)
- **Autentikointi:** Microsoft Entra ID (MSAL), per-user tietokantayhteys, audit trail

Kaikki kolme ympäristöä (dev, test, prod) sijaitsevat **yhdessä Azure Subscriptionissa**, kukin omassa resurssiryhmässään. Yhteiset resurssit (Container Registry, runner, Log Analytics) sijaitsevat erillisessä jaettussa resurssiryhmässä.

### Kokonaisarkkitehtuuri

```
Internet
   │
   ├── Flutter SPA (MSAL) ──► Microsoft Entra ID
   │        │                       │
   │        │ Bearer token           │ JWKS
   │        ▼                       ▼
   ├── Container App (frontend)  Container App (backend / FastAPI)
   │   ca-jkr-frontend-{env}        ca-jkr-backend-{env}
   │                                        │
   │                               VNet-integraatio
   │                                        │
   │                            PostgreSQL Flexible Server
   │                               psql-jkr-{env}
   │
   └── GitHub Actions ──► Self-hosted runner (vm-jkr-runner)
            │                     │
            │              Azure Container Registry
            │                  crjkr (shared)
            │                     │
            └─────────────────────┴──► Deploy: ca-jkr-backend-{env}
                                       Deploy: ca-jkr-frontend-{env}
```

---

## 2. Azure-resurssit – täydellinen lista

### 2.1 Jaettu resurssiryhmä

| Resurssinimi | Tyyppi | Kuvaus |
|---|---|---|
| `rg-jkr-shared` | Resource Group | Jaetut resurssit kaikille ympäristöille |
| `crjkr` | Azure Container Registry (Standard) | Docker-imageiden rekisteri (backend + frontend) |
| `vm-jkr-runner` | Virtual Machine (Standard_B2s) | GitHub Actions self-hosted runner |
| `nic-jkr-runner` | Network Interface | Runnerin verkkokortti |
| `disk-jkr-runner` | Managed Disk (Standard SSD) | Runnerin käyttöjärjestelmälevy |
| `pip-jkr-runner` | Public IP Address | Runnerin julkinen IP (hallinta) |
| `nsg-jkr-runner` | Network Security Group | Runnerin liikennöintisäännöt (SSH sisään vain omasta IP:stä) |
| `vnet-jkr-shared` | Virtual Network | Runnerin verkko |
| `snet-jkr-runner` | Subnet | Runnerin aliverkko |
| `law-jkr` | Log Analytics Workspace | Kaikkien ympäristöjen lokit keskitetysti |
| `id-jkr-runner` | User-assigned Managed Identity | Runnerin identiteetti ACR-push + Container App -deploy oikeuksiin |

> **Huomio:** ACR:ssä on yksi rekisteri kaikille ympäristöille. Imageja erotetaan tageilla:
> `crjkr.azurecr.io/jkr-backend:dev-{sha}`, `crjkr.azurecr.io/jkr-backend:prod-{sha}` jne.

### 2.2 Dev-resurssiryhmä

| Resurssinimi | Tyyppi | Kuvaus |
|---|---|---|
| `rg-jkr-dev` | Resource Group | Dev-ympäristön kaikki resurssit |
| `vnet-jkr-dev` | Virtual Network (10.1.0.0/16) | Dev-ympäristön verkko |
| `snet-jkr-cae-dev` | Subnet (10.1.0.0/23) | Container App Environment -aliverkko (min /23) |
| `snet-jkr-db-dev` | Subnet (10.1.2.0/24) | PostgreSQL Flexible Server -aliverkko |
| `nsg-jkr-cae-dev` | Network Security Group | CAE-aliverkon säännöt |
| `nsg-jkr-db-dev` | Network Security Group | DB-aliverkon säännöt (sallii vain CAE-aliverkosta) |
| `pdnsz-postgres-dev` | Private DNS Zone | `privatelink.postgres.database.azure.com` – PostgreSQL:n nimenhaku VNetissä |
| `cae-jkr-dev` | Container App Environment | Dev-ympäristön Container App -isäntä (VNet-injektoitu) |
| `ca-jkr-backend-dev` | Container App | FastAPI-backend, dev |
| `ca-jkr-frontend-dev` | Container App | Flutter web / nginx, dev |
| `psql-jkr-dev` | PostgreSQL Flexible Server (Burstable B2ms) | Dev-tietokanta (PostGIS, pgaudit) |
| `kv-jkr-dev` | Key Vault (Standard) | Dev-ympäristön salaisuudet |
| `ai-jkr-dev` | Application Insights | Dev-ympäristön APM |

### 2.3 Test-resurssiryhmä

| Resurssinimi | Tyyppi | Kuvaus |
|---|---|---|
| `rg-jkr-test` | Resource Group | Test-ympäristön kaikki resurssit |
| `vnet-jkr-test` | Virtual Network (10.2.0.0/16) | Test-ympäristön verkko |
| `snet-jkr-cae-test` | Subnet (10.2.0.0/23) | Container App Environment -aliverkko |
| `snet-jkr-db-test` | Subnet (10.2.2.0/24) | PostgreSQL Flexible Server -aliverkko |
| `nsg-jkr-cae-test` | Network Security Group | CAE-aliverkon säännöt |
| `nsg-jkr-db-test` | Network Security Group | DB-aliverkon säännöt |
| `pdnsz-postgres-test` | Private DNS Zone | `privatelink.postgres.database.azure.com` |
| `cae-jkr-test` | Container App Environment | Test-ympäristön Container App -isäntä (VNet-injektoitu) |
| `ca-jkr-backend-test` | Container App | FastAPI-backend, test |
| `ca-jkr-frontend-test` | Container App | Flutter web / nginx, test |
| `psql-jkr-test` | PostgreSQL Flexible Server (Burstable B2ms) | Test-tietokanta |
| `kv-jkr-test` | Key Vault (Standard) | Test-ympäristön salaisuudet |
| `ai-jkr-test` | Application Insights | Test-ympäristön APM |

### 2.4 Prod-resurssiryhmä

| Resurssinimi | Tyyppi | Kuvaus |
|---|---|---|
| `rg-jkr-prod` | Resource Group | Tuotantoympäristön kaikki resurssit |
| `vnet-jkr-prod` | Virtual Network (10.3.0.0/16) | Tuotantoympäristön verkko |
| `snet-jkr-cae-prod` | Subnet (10.3.0.0/23) | Container App Environment -aliverkko |
| `snet-jkr-db-prod` | Subnet (10.3.2.0/24) | PostgreSQL Flexible Server -aliverkko |
| `nsg-jkr-cae-prod` | Network Security Group | CAE-aliverkon säännöt |
| `nsg-jkr-db-prod` | Network Security Group | DB-aliverkon säännöt |
| `pdnsz-postgres-prod` | Private DNS Zone | `privatelink.postgres.database.azure.com` |
| `cae-jkr-prod` | Container App Environment | Tuotantoympäristön Container App -isäntä (VNet-injektoitu) |
| `ca-jkr-backend-prod` | Container App | FastAPI-backend, prod (System-assigned Managed Identity) |
| `ca-jkr-frontend-prod` | Container App | Flutter web / nginx, prod |
| `psql-jkr-prod` | PostgreSQL Flexible Server (General Purpose D4s v3) | Tuotantotietokanta (HA-standby) |
| `kv-jkr-prod` | Key Vault (Standard) | Tuotantoympäristön salaisuudet |
| `ai-jkr-prod` | Application Insights | Tuotantoympäristön APM |

### 2.5 Microsoft Entra ID (koko tenant, ei per-ympäristö)

| Resurssinimi | Tyyppi | Kuvaus |
|---|---|---|
| `JKR Tiedonhallinta DEV` | App Registration | Dev-ympäristön sovellus (clientId + secret) |
| `JKR Tiedonhallinta TEST` | App Registration | Test-ympäristön sovellus (clientId + secret) |
| `JKR Tiedonhallinta PROD` | App Registration | Prod-ympäristön sovellus (clientId, ei secretia – Managed Identity) |
| `sg-jkr-admin-sql` | Security Group | Käyttäjät joilla kirjoitusoikeus ja oikeus ajaa migraatioita |
| `sg-jkr-viewer-sql` | Security Group | Käyttäjät joilla vain lukuoikeus |

---

## 3. Verkkoarkkitehtuuri

### 3.1 Periaatteet

- Jokainen ympäristö on **täysin eristetyssä VNetissä** – ympäristöjen välillä ei ole VNet Peeringiä
- PostgreSQL Flexible Server on **VNet-injektoitu**: sillä ei ole julkista IP-osoitetta
- Yhteys tietokantaan on mahdollinen **ainoastaan Container App Environmentin aliverkosta**
- Frontend Container App on julkisesti saavutettavissa Internetistä (Container Appin sisäänrakennettu HTTPS + custom domain)
- Backend Container App on julkisesti saavutettavissa (API-kutsujen vastaanotto frontendistä ja muista järjestelmistä)

### 3.2 Verkkokaavio (per ympäristö)

```
Internet
   │
   │ HTTPS (443)
   ▼
┌─────────────────────────────────────────────────────────┐
│  Container App Environment (cae-jkr-{env})              │
│  VNet-injektoitu: snet-jkr-cae-{env} (10.x.0.0/23)     │
│                                                         │
│  ┌──────────────────────┐  ┌──────────────────────────┐ │
│  │ ca-jkr-frontend-{env}│  │  ca-jkr-backend-{env}   │ │
│  │  nginx + Flutter web │  │  FastAPI (uvicorn)       │ │
│  │  Port 8080           │  │  Port 8000               │ │
│  └──────────────────────┘  └──────────┬───────────────┘ │
│                                        │                 │
└────────────────────────────────────────┼─────────────────┘
                                         │ Port 5432 (TLS)
                                         ▼
                        ┌────────────────────────────────┐
                        │  snet-jkr-db-{env}             │
                        │  (10.x.2.0/24)                 │
                        │                                │
                        │  psql-jkr-{env}                │
                        │  PostgreSQL Flexible Server     │
                        │  (ei julkista IP:tä)           │
                        └────────────────────────────────┘
```

### 3.3 NSG-säännöt (tietokanta-aliverkko)

| Sääntö | Suunta | Lähde | Kohde | Port | Toiminta |
|---|---|---|---|---|---|
| AllowBackendToPostgres | Inbound | `snet-jkr-cae-{env}` | `snet-jkr-db-{env}` | 5432 | Allow |
| DenyAllInbound | Inbound | Any | Any | Any | Deny |

### 3.4 Private DNS Zone

Jokainen ympäristö saa oman Private DNS Zone -liitoksen VNettiinsä:  
`privatelink.postgres.database.azure.com` → resolvaa `psql-jkr-{env}.postgres.database.azure.com` VNetin sisäiseen IP-osoitteeseen.

---

## 4. Autentikointi ja valtuutus

### 4.1 Autentikointiketju

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────────────┐
│  Flutter SPA  │────►│  Microsoft        │     │  FastAPI backend      │
│  (MSAL)       │◄───│  Entra ID         │     │  (ca-jkr-backend)     │
│               │     │                  │     │                      │
│  1. Login      │     │  2. Token        │     │  3. Validoi JWT       │
│  2. Saa tokenin│     │     (JWT, ~1h)   │────►│     JWKS-avaimilla    │
│  3. API-kutsut │────────────────────────────►│  4. Per-user DB conn  │
└──────────────┘     └──────────────────┘     └──────────┬───────────┘
                                                          │
                                              Token = salasana
                                                          │
                                                          ▼
                                              ┌──────────────────────┐
                                              │  PostgreSQL           │
                                              │  Flexible Server      │
                                              │  (Entra ID auth)     │
                                              │  Audit: käyttäjä     │
                                              │  näkyy lokissa       │
                                              └──────────────────────┘
```

### 4.2 App Registrationit

Kullakin ympäristöllä on oma App Registration (`New-JKRAppRegistration.ps1`):

| Ympäristö | App Registration | Client secret | Managed Identity |
|---|---|---|---|
| dev | `JKR Tiedonhallinta DEV` | Kyllä (Key Vaultissa) | Ei |
| test | `JKR Tiedonhallinta TEST` | Kyllä (Key Vaultissa) | Ei |
| prod | `JKR Tiedonhallinta PROD` | Ei (poistetaan käyttöönoton jälkeen) | Kyllä (`ca-jkr-backend-prod`) |

**API Scope:** `api://{clientId}/access_as_user`  
**Graph-oikeudet:** `User.Read` (delegated), `GroupMember.Read.All` (delegated), `Sites.Selected` (application)  
**Optional claims:** `groups` (SecurityGroup-jäsenyydet tokenissa)

### 4.3 Entra ID -ryhmät → PostgreSQL-roolit

| Entra ID Security Group (Azure) | PostgreSQL-rooli | Oikeudet |
|---|---|---|
| `sg-jkr-admin-sql` | `jkr_editor` | INSERT, UPDATE, DELETE kaikissa jkr-skeemoissa + Flyway-migraatiot + perii `jkr_viewer` |
| `sg-jkr-viewer-sql` | `jkr_viewer` | SELECT kaikissa jkr-skeemoissa |

Entra ID -ryhmät ja PostgreSQL-roolit ovat erillisiä käsitteitä. Entra ID -ryhmä linkitetään PostgreSQL-rooliin `pgaadauth_create_principal`-funktiolla (ks. osio 5.3). **Käyttäjähallinta tapahtuu yksinomaan Entra ID:ssä** – lisäämällä käyttäjä oikeaan Security Groupiin.

### 4.4 SharePoint-valtuutus (tuotanto)

Tuotannossa `ca-jkr-backend-prod` käyttää **System-assigned Managed Identityä** SharePoint-kirjoitukseen:

```
ca-jkr-backend-prod (Managed Identity)
    → Sites.Selected -oikeus SharePoint-siteen
    → Konfiguroitu: Set-JKRManagedIdentity.ps1
    → Ei client secretia tuotannossa
```

Dev ja test käyttävät App Registrationin client secretia (tallennettu Key Vaultiin).

---

## 5. Tietokanta-arkkitehtuuri

### 5.1 Per-ympäristö konfiguraatio

| Parametri | Dev | Test | Prod |
|---|---|---|---|
| SKU | Burstable B2ms | Burstable B2ms | General Purpose D4ds v5 |
| Tallennustila | 32 GB | 32 GB | 128 GB (autoskalautuva) |
| High Availability | Ei | Ei | Zone-redundant standby |
| Varmuuskopiot | 7 vrk (LRS) | 7 vrk (LRS) | 35 vrk (GRS) |
| PostgreSQL versio | 16 | 16 | 16 |
| Julkinen verkko | Ei (VNet only) | Ei (VNet only) | Ei (VNet only) |

### 5.2 Laajennukset (per tietokanta)

```sql
CREATE EXTENSION IF NOT EXISTS postgis;       -- Paikkatietokyselyt
CREATE EXTENSION IF NOT EXISTS pgaudit;       -- Audit trail (kirjoitusoperaatiot)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- UUID-generaatio
```

### 5.3 PostgreSQL-roolihierarkia

```
Entra ID (Azure)                       PostgreSQL Flexible Server
──────────────────────────             ──────────────────────────────────────
                                       postgres  (superuser, vain admin-ops)
                                       │
sg-jkr-admin-sql  (Security Group) ──► jkr_editor  ← INSERT, UPDATE, DELETE
                                       │               kaikissa jkr-skeemoissa
                                       │               + Flyway-migraatiot
                                       │               + perii jkr_viewer
                                       │
sg-jkr-viewer-sql (Security Group) ──► jkr_viewer  ← SELECT kaikissa
                                                       jkr-skeemoissa
```

Linkitys tehdään kertaluonteisesti `pgaadauth_create_principal`-kutsulla:

```sql
SELECT * FROM pgaadauth_create_principal('sg-jkr-admin-sql',  false, true);
GRANT jkr_editor TO "sg-jkr-admin-sql";

SELECT * FROM pgaadauth_create_principal('sg-jkr-viewer-sql', false, true);
GRANT jkr_viewer TO "sg-jkr-viewer-sql";
```

Erillinen tietokantakäyttäjä CI/CD-migraatioihin (ei Entra ID -autentikaatiota):

```
jkr-flyway  ← salasaunainen PostgreSQL-tunnus, tallennettu Key Vaultiin
               käytetään vain Flyway-migraatioissa
```

### 5.4 pgaudit-konfiguraatio

```ini
# Server parameters (Azure Portal tai IaC)
shared_preload_libraries = pgaudit
pgaudit.log = write          # Lokittaa INSERT, UPDATE, DELETE, TRUNCATE
pgaudit.log_catalog = off    # Ei järjestelmätaulujen lokitusta
```

### 5.5 Skeemarakenne

```
tietokanta: jkr
├── schema: jkr            ← Päädata (kohteet, kuljetukset, sopimukset)
├── schema: jkr_koodistot  ← Koodistot ja luokittelut
└── schema: jkr_osoite     ← Osoitetiedot (rakennukset, kiinteistöt)
```

Migraatiot hallitaan **Flywaylla** (`db/migrations/`).

---

## 6. CI/CD – Self-hosted runner

### 6.1 Runneriarkkitehtuuri

Self-hosted GitHub Actions runner (`vm-jkr-runner`) sijaitsee `rg-jkr-shared`-resurssiryhmässä. Se on Ubuntu-virtuaalikone, johon on asennettu:

- GitHub Actions runner agent
- Azure CLI
- Docker

Runnerilla on **User-assigned Managed Identity** (`id-jkr-runner`) jolla on seuraavat roolit:

| Rooli | Kohde | Tarkoitus |
|---|---|---|
| `AcrPush` | `crjkr` | Docker-imageiden lähetys rekisteriin |
| `Contributor` | `rg-jkr-dev` | Container App -deployaus deviin |
| `Contributor` | `rg-jkr-test` | Container App -deployaus testiin |
| `Contributor` | `rg-jkr-prod` | Container App -deployaus tuotantoon |
| `AcrPull` | `crjkr` | Container App voi vetää imageja |

> **Huomio:** Contributor-rooli on laaja. Harkitse tarkemmin rajattua roolia  
> (esim. `Container Apps Contributor` ja `Key Vault Secrets User`) tuotantoon.

### 6.2 CI/CD-putki (tavoitetila)

```
GitHub push/merge
       │
       ▼
GitHub Actions workflow (self-hosted runner: vm-jkr-runner)
       │
       ├── 1. Checkout koodi
       ├── 2. Build backend Docker image
       │       docker build -t crjkr.azurecr.io/jkr-backend:{env}-{sha} .
       ├── 3. Build frontend Docker image
       │       docker build -t crjkr.azurecr.io/jkr-frontend:{env}-{sha} ./jkrfront/
       ├── 4. Push molemmat imaget ACR:ään
       │       az acr login --name crjkr
       │       docker push crjkr.azurecr.io/jkr-backend:{env}-{sha}
       │       docker push crjkr.azurecr.io/jkr-frontend:{env}-{sha}
       ├── 5. Aja Flyway-migraatiot
       │       (runner-koneelta tai erillinen Container App Job)
       └── 6. Deploy Container Appit
               az containerapp update \
                 --name ca-jkr-backend-{env} \
                 --resource-group rg-jkr-{env} \
                 --image crjkr.azurecr.io/jkr-backend:{env}-{sha}
               az containerapp update \
                 --name ca-jkr-frontend-{env} \
                 --resource-group rg-jkr-{env} \
                 --image crjkr.azurecr.io/jkr-frontend:{env}-{sha}
```

### 6.3 Haarstrategia (ehdotus)

| Haara | Ympäristö | Laukaisin |
|---|---|---|
| `develop` | dev | Push |
| `main` | test | Push |
| `v*`-tagi (esim. `v1.2.3`) | prod | Tag-push (manuaalinen hyväksyntä) |

### 6.4 Flyway-migraatiot Azure-ympäristössä

Nykyinen Flyway-suoritus tapahtuu Docker Composen kautta paikallisesti. Azuressa migraatiot voidaan ajaa:

**Vaihtoehto A (suositeltu):** Container App Job  
- `caj-jkr-flyway-{env}` – kertaluonteinen Container App Job joka ajetaan CI/CD-putken vaiheessa 5
- Käyttää samaa `snet-jkr-cae-{env}` aliverkkoa → pääsee tietokantaan

**Vaihtoehto B:** Runnerin kautta  
- Runner tarvitsisi VNet-yhteyden tai PostgreSQL:n julkisen IP:n (ei suositella)

---

## 7. Frontend-arkkitehtuuri

### 7.1 Yksi image, useita ympäristöjä

Frontendistä rakennetaan **yksi Docker-image** joka toimii kaikissa ympäristöissä. Ympäristökohtainen konfiguraatio injektoidaan ajonaikaisesti:

```
Dockerfile (jkrfront/Dockerfile)
    Stage 1: Flutter build (ghcr.io/cirruslabs/flutter:3.27.4)
        flutter build web --release
    Stage 2: nginx:alpine
        Kopioi build/web → /usr/share/nginx/html
        Kopioi 30-runtime-config.sh → /docker-entrypoint.d/
```

Käynnistyessään nginx-kontti ajaa `30-runtime-config.sh`, joka generoi `runtime_config.js` tiedoston Container Appin ympäristömuuttujista:

```javascript
// runtime_config.js (generoitu ajonaikaisesti)
window.runtimeConfig = {
  apiBaseUrl: "https://ca-jkr-backend-prod.{hash}.{region}.azurecontainerapps.io",
  azureClientId: "...",
  azureTenantId: "...",
  azureRedirectUri: "https://ca-jkr-frontend-prod.{hash}.{region}.azurecontainerapps.io"
};
```

### 7.2 Frontend Container App – ympäristömuuttujat

| Muuttuja | Dev | Test | Prod |
|---|---|---|---|
| `API_BASE_URL` | `https://ca-jkr-backend-dev...` | `https://ca-jkr-backend-test...` | `https://ca-jkr-backend-prod...` |
| `AZURE_CLIENT_ID` | DEV App Registration Client ID | TEST App Registration Client ID | PROD App Registration Client ID |
| `AZURE_TENANT_ID` | Sama kaikissa | Sama kaikissa | Sama kaikissa |
| `AZURE_REDIRECT_URI` | Dev-frontend URL | Test-frontend URL | Prod-frontend URL |

### 7.3 Container App vs Static Web App

Nykyinen toteutus (nginx-kontti, runtime_config.js) vaatii Container Appin eikä ole yhteensopiva Azure Static Web Appsin kanssa.

| | Container App (nykyinen) | Azure Static Web App |
|---|---|---|
| Ympäristökohtainen konfig | Ympäristömuuttujat → runtime_config.js | Erillinen build per ympäristö |
| Hinta | Noin 15–30 €/kk per ympäristö (Consumption) | Ilmainen tai Standard ~9 €/kk |
| HTTPS | Sisäänrakennettu | Sisäänrakennettu |
| Custom domain | Tuettu | Tuettu |
| **Suositus** | **Käytä – yhteensopiva nykyisen lähestymistavan kanssa** | Ei sovi ilman arkkitehtuurimuutosta |

---

## 8. Salaisuuksien hallinta

### 8.1 Key Vault per ympäristö

Jokainen ympäristö käyttää omaa Key Vaultia. Container Appit lukevat salaisuudet Key Vault -viittauksilla (`secretRef`).

| Salaisuus | Dev | Test | Prod |
|---|---|---|---|
| `azure-client-secret` | Key Vault | Key Vault | **Ei ole** (Managed Identity) |
| `db-flyway-password` | Key Vault | Key Vault | Key Vault |
| `db-connection-string` | Key Vault | Key Vault | Key Vault |
| `sharepoint-site-id` | Key Vault | Key Vault | Key Vault |

### 8.2 Container App -salaisuudet

Backend Container App viittaa Key Vaultiin käyttäen Managed Identityä tai System-assigned Managed Identityä:

```bash
az containerapp secret set \
  --name ca-jkr-backend-dev \
  --resource-group rg-jkr-dev \
  --secrets "azure-client-secret=keyvaultref:https://kv-jkr-dev.vault.azure.net/secrets/azure-client-secret"
```

---

## 9. Havainnointi ja lokitus

### 9.1 Log Analytics Workspace

Kaikki ympäristöt lähettävät logit keskitettyyn `law-jkr` -työtilaan (tai vaihtoehtoisesti ympäristökohtaisiin työtilaan erottelun vuoksi).

| Lokityyppi | Lähde | Kohde |
|---|---|---|
| Container App -lokit | `ca-jkr-backend-{env}`, `ca-jkr-frontend-{env}` | `law-jkr` |
| PostgreSQL Diagnostic Logs | `psql-jkr-{env}` | `law-jkr` |
| pgaudit-lokit | PostgreSQL | `law-jkr` (PostgreSQL Diagnostic Logs kautta) |
| Sovelluksen telemetria | FastAPI + Application Insights SDK | `ai-jkr-{env}` |

### 9.2 Audit trail

pgaudit lokittaa kaikki kirjoitusoperaatiot (INSERT, UPDATE, DELETE) käyttäjänimellä (Entra ID UPN). Lokit välitetään Azure Log Analyticsiin:

```
AUDIT: SESSION,1,1,WRITE,INSERT,,jkr.kuljetus,
"INSERT INTO jkr.kuljetus ...",<none>
DETAIL: User: matti.meikalainen@lahti.fi
```

---

## 10. Ympäristöjen väliset erot

| Ominaisuus | Dev | Test | Prod |
|---|---|---|---|
| PostgreSQL SKU | Burstable B2ms | Burstable B2ms | General Purpose D4ds v5 |
| PostgreSQL HA | Ei | Ei | Zone-redundant |
| Varmuuskopioiden säilytys | 7 vrk | 7 vrk | 35 vrk |
| Varmuuskopioiden redundanssi | LRS | LRS | GRS |
| SharePoint-autentikointi | Client secret | Client secret | Managed Identity |
| Container App min-replicas | 0 (scale to zero) | 0 | 1 |
| Custom domain | Ei välttämätön | Ei välttämätön | Kyllä (`jkr.lahti.fi` tms.) |
| Entra ID -ryhmä autorisointi | Voidaan sallia kaikille devit | Rajattu testiryhmä | Vain tuotantoryhmät |

---

## 11. Parannusehdotukset ja avoimet kysymykset

### 11.1 Puuttuvat resurssit (kriittiset)

**Azure Container Registry** – ei mainittu alkuperäisessä kuvauksessa, mutta välttämätön Docker-imageiden varastointiin. Ilman ACR:ää Container App -deployaus ei onnistu. Tarvitaan yksi jaettu rekisteri.

**Azure Key Vault** – salaisuuksien hallinta on kriittistä. Client secret ei saa olla suoraan Container Appin ympäristömuuttujana vaan Key Vault -viittauksena.

**Flyway-migraatiot Azuressa** – nykyinen Docker Compose -pohjainen suoritustapa ei toimi Azuressa sellaisenaan. Tarvitaan Container App Job tai muu tapa ajaa migraatiot VNetin sisällä ennen deployausta.

**Log Analytics Workspace** – ilman tätä Container Appien ja PostgreSQL:n lokit eivät tallennu pysyvästi.

**Private DNS Zone** – ilman tätä PostgreSQL:n VNet-injektio ei toimi (nimenhaku epäonnistuu).

### 11.2 Parannusehdotukset

**Frontend-deployaus: Static Web App vs Container App**  
Nykyinen arkkitehtuuri (runtime_config.js nginx-skriptillä) on toimiva ratkaisu Container Appille. Jos kustannukset ovat kriittinen tekijä, kannattaa harkita Azure Static Web Appia, mutta se vaatisi ympäristökohtaisen buildin tai erillisen konfiguraaatiopalvelun. Nykyinen lähestymistapa on selkeämpi – pidä se.

**GitHub Actions workflow puuttuu tuotantokäyttöön**  
Nykyinen `release.yml` rakentaa Python-wheeliä eikä ole tarkoitettu Azure-deployaukseen. Tarvitaan uusi workflow-tiedosto (esim. `.github/workflows/deploy.yml`) joka buildaa Docker-imageet, pushaa ACR:ään ja päivittää Container Appit.

**Runnerin sijoitus**  
Runner on nyt `rg-jkr-shared`-ryhmässä, mikä on hyvä. Harkitse runnerin VNet-peering tai Private Endpoint ACR:ään, jotta kaikki liikenne kulkee privaattina.

**Container App -skaalaus**  
Dev ja test voidaan skaalata nollaan (scale-to-zero, Consumption-tier) kustannussäästöjen vuoksi. Prod tarvitsee min 1 replika jotta kylmäkäynnistysviive ei vaikuta käyttäjiin.

**Managed Identity -ketju ACR:ään**  
Container App voi vetää imageja ACR:stä ilman salasanaa Managed Identityä käyttäen. Tämä on tietoturvallisempi kuin admin-salasana. Konfigurointi:
```bash
az containerapp registry set \
  --name ca-jkr-backend-prod \
  --resource-group rg-jkr-prod \
  --server crjkr.azurecr.io \
  --identity system
```

**Yksi App Registration riittäisi** (vaihtoehtoinen näkemys)  
Kolmen erillisen App Registrationin sijaan voisi käyttää yhtä rekisteröintiä useammalla redirect URI:lla. Nykyinen kolmen rekisteröinnin malli on kuitenkin selkeämpi ja ympäristöt ovat paremmin eristettyjä – erityisesti audit trail erottaa ympäristöt selkeästi. Pidä nykyinen malli.

**Tuotannon custom domain**  
Container App saa automaattisesti `.azurecontainerapps.io`-domainin, mutta tuotannossa kannattaa konfiguroida organisaation oma domain (esim. `jkr.lahti.fi` ja `jkr-api.lahti.fi`). Tämä vaatii DNS-muutoksen ja Azure-sertifikaatin.

**Infrastructure as Code**  
Resurssien luontia ei ole vielä automatisoitu (PowerShell-skriptit kattavat vain Entra ID -rekisteröinnin). Harkitse Bicep- tai Terraform-skriptien kirjoittamista koko infrastruktuurin provisioinnin automatisoimiseksi.

### 11.3 Avoimet kysymykset

1. **Mihin Subscription/Tenant JKR kuuluu?** Onko käytössä organisaation olemassaoleva tenant vai erillinen?
2. **Custom domain:** Mikä on tuotantofrontendin ja -backendin osoite? (Tarvitaan App Registrationin redirect URI:hin.)
3. **SharePoint-site:** Mikä SharePoint-site vastaanottaa JKR-ajot? (Tarvitaan Set-JKRManagedIdentity.ps1-ajoon.)
4. **Flyway prod-migraatiot:** Kuka ajaa migraatiot tuotantoon? Automaattisesti CI/CD:ssä vai manuaalisesti?
5. **PostgreSQL-varmuuskopiot:** Riittävätkö Azuren automaattiset varmuuskopiot vai tarvitaanko erillinen pg_dump-prosessi?
6. **Runnerin elinkaari:** VM vai skaalautuva Container App Job -runner? (ARC = Actions Runner Controller on parempi pitkällä tähtäimellä.)

---

## 12. Käyttöönottojärjestys

### Vaihe 1 – Entra ID (heti, ennen muita)
1. `New-JKRAppRegistration.ps1 -Env dev`
2. `New-JKRAppRegistration.ps1 -Env test`
3. `New-JKRAppRegistration.ps1 -Env prod`
4. Luo Entra ID -ryhmät: `sg-jkr-admin-sql`, `sg-jkr-viewer-sql`

### Vaihe 2 – Jaetut resurssit
1. Luo `rg-jkr-shared`
2. Luo `crjkr` (Azure Container Registry, Standard SKU)
3. Luo `law-jkr` (Log Analytics Workspace)
4. Luo `vm-jkr-runner`, asenna GitHub Actions runner
5. Konfiguroi `id-jkr-runner` Managed Identity ja roolimääritykset

### Vaihe 3 – Ympäristökohtaiset resurssit (dev ensin, sitten test, sitten prod)
1. Luo resurssiryhmä (`rg-jkr-{env}`)
2. Luo VNet, aliverkot, NSG:t, Private DNS Zone
3. Luo PostgreSQL Flexible Server (VNet-injektoitu)
4. Luo Key Vault, tallenna salaisuudet
5. Rekisteröi Entra ID -ryhmät PostgreSQL-rooleiksi (pgaadauth_create_principal)
6. Aja Flyway-migraatiot (alkuasetus)
7. Luo Container App Environment (VNet-injektoitu)
8. Luo Container Appit (backend + frontend)
9. Konfiguroi ACR-integraatio ja ympäristömuuttujat

### Vaihe 4 – Prod: Managed Identity SharePointiin
1. Julkaise backend tuotantoon (vaihe 3)
2. `Set-JKRManagedIdentity.ps1 -ContainerAppName ca-jkr-backend-prod -ResourceGroup rg-jkr-prod -SharePointSiteId <id>`
3. Poista client secret tuotannon Container Appista
4. Poista `AZURE_CLIENT_SECRET` ympäristömuuttuja

### Vaihe 5 – CI/CD
1. Kirjoita `.github/workflows/deploy.yml`
2. Testaa pipeline deviin
3. Käyttöönota test ja prod

---

*Tiedosto: `docs/azure-arkkitehtuuri.md`*  
*Seuraava päivitys: Kun resurssien provisiointi on aloitettu ja nimet vahvistettu.*
