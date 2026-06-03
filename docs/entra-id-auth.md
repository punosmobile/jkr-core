# JKR – Microsoft Entra ID -autentikointi

## Yleiskuvaus

JKR-sovellus autentikoi käyttäjät Microsoft Entra ID:n (ent. Azure AD) avulla. Jokainen API-kutsu suoritetaan tietokannassa kirjautuneen käyttäjän tunnuksilla, jolloin Azure Database for PostgreSQL Flexible Serverin audit trail näyttää oikean käyttäjän.

```
┌─────────────┐     ┌───────────────┐     ┌──────────────────┐     ┌──────────────────────────┐
│  Flutter     │────▶│  Entra ID     │────▶│  FastAPI          │────▶│  Azure PostgreSQL         │
│  (MSAL)      │     │  (token)      │     │  (validoi token)  │     │  Flexible Server          │
│              │◀────│               │     │  (per-user conn)  │     │  (audit: käyttäjä näkyy)  │
└─────────────┘     └───────────────┘     └──────────────────┘     └──────────────────────────┘
```

## Roolimalli

### Entra ID -ryhmät → PostgreSQL-roolit

| Entra ID -ryhmä | PostgreSQL-rooli | Oikeudet |
|------------------|------------------|----------|
| `JKR_EDITOR`    | `jkr_editor`     | INSERT, UPDATE, DELETE + perii `jkr_viewer` |
| `JKR_VIEWER`    | `jkr_viewer`     | SELECT kaikista jkr-skeemoista |

**Käyttäjähallinta tapahtuu ainoastaan Azuren puolella** – käyttäjä lisätään Entra ID -ryhmään `JKR_EDITOR` tai `JKR_VIEWER`. Mitään admin-ryhmää ei tarvita.

### Nykyiset oikeudet (afterMigrate.sql)

`jkr_editor`-rooli saa seuraavat oikeudet kaikkiin skeemoihin:

```sql
-- jkr schema
GRANT USAGE ON SCHEMA jkr TO jkr_viewer;
GRANT SELECT ON ALL TABLES IN SCHEMA jkr TO jkr_viewer;
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA jkr TO jkr_editor;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA jkr TO jkr_editor;

-- jkr_koodistot schema
GRANT USAGE ON SCHEMA jkr_koodistot TO jkr_viewer;
GRANT SELECT ON ALL TABLES IN SCHEMA jkr_koodistot TO jkr_viewer;
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA jkr_koodistot TO jkr_editor;

-- jkr_osoite schema
GRANT USAGE ON SCHEMA jkr_osoite TO jkr_viewer;
GRANT SELECT ON ALL TABLES IN SCHEMA jkr_osoite TO jkr_viewer;
GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA jkr_osoite TO jkr_editor;
```

`jkr_editor` perii `jkr_viewer`-oikeudet:
```sql
GRANT jkr_viewer TO jkr_editor;
```

## Autentikointiketju (yksityiskohtainen)

### 1. Flutter-sovellus (MSAL)

```dart
// msal_flutter tai azure_ad_authentication -paketti
final config = PublicClientApplication(
  clientId: 'APP_CLIENT_ID',       // App Registration Client ID
  authority: 'https://login.microsoftonline.com/TENANT_ID',
  redirectUri: 'msauth://com.example.jkr/callback',
);

// Kirjautuminen – pyydetään token PostgreSQL-resurssia varten
final result = await config.acquireToken(
  scopes: ['https://ossrdbms-aad.database.windows.net/.default'],
);

// result.accessToken → lähetetään API:lle
```

**Tärkeä scope:** `https://ossrdbms-aad.database.windows.net/.default`  
Tämä on Azure Database for PostgreSQL -resurssin scope. Token on voimassa ~1h.

### 2. FastAPI-backend (token-validointi + per-user DB)

```python
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import httpx
import os

security = HTTPBearer()

# Entra ID -konfiguraatio (.env)
TENANT_ID = os.environ["AZURE_TENANT_ID"]
CLIENT_ID = os.environ["AZURE_CLIENT_ID"]
JWKS_URL = f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"

# JWKS-avainten cache
_jwks_cache = None

async def _get_jwks():
    """Hae Entra ID:n julkiset avaimet (cachetaan)."""
    global _jwks_cache
    if _jwks_cache is None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(JWKS_URL)
            _jwks_cache = resp.json()
    return _jwks_cache


async def validate_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Validoi Entra ID access token ja palauttaa token claimsit."""
    token = credentials.credentials
    try:
        jwks = await _get_jwks()
        unverified_header = jwt.get_unverified_header(token)
        
        # Etsi oikea avain kid:n perusteella
        key = next(
            (k for k in jwks["keys"] if k["kid"] == unverified_header["kid"]),
            None,
        )
        if not key:
            raise HTTPException(status_code=401, detail="Tuntematon allekirjoitusavain")
        
        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience="https://ossrdbms-aad.database.windows.net",
            issuer=f"https://sts.windows.net/{TENANT_ID}/",
        )
        return claims
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Token-validointi epäonnistui: {e}")


def get_user_db_session(
    request: Request,
    claims: dict = Depends(validate_token),
) -> Session:
    """Luo tietokantayhteys kirjautuneen käyttäjän tunnuksilla.
    
    PostgreSQL Flexible Server hyväksyy Entra ID access tokenin salasanana.
    Audit trail tallentuu oikean käyttäjän nimiin.
    """
    access_token = request.headers["Authorization"].split(" ")[1]
    username = claims.get("preferred_username") or claims.get("upn")
    
    if not username:
        raise HTTPException(status_code=401, detail="Käyttäjätunnus puuttuu tokenista")
    
    # Luo yhteys käyttäjän tunnuksilla – token toimii salasanana
    user_engine = create_engine(
        f"postgresql://{username}:{access_token}@{db_host}:{db_port}/{db_name}",
        connect_args={"sslmode": "require"},
        pool_size=1,
        max_overflow=0,
    )
    
    session = Session(user_engine)
    return session
```

### 3. Suojattu endpoint (esimerkki)

```python
@app.post("/jkr/import", summary="Kuljetustietojen tuonti")
async def jkr_import(
    req: JkrImportRequest,
    background_tasks: BackgroundTasks,
    claims: dict = Depends(validate_token),   # ← suojaus
):
    username = claims.get("preferred_username", "tuntematon")
    logger.info(f"Käyttäjä {username} käynnisti kuljetustietojen tuonnin")
    # ... tehtävän käynnistys
```

### 4. Azure PostgreSQL Flexible Server

Käyttäjän yhteys kantaan:
- **user** = `user@domain.onmicrosoft.com` (Entra ID UPN)
- **password** = Azure AD access token (lyhytikäinen, ~1h)
- **sslmode** = `require` (pakollinen Azure Flexible Serverissä)

## Azure-puolen konfigurointi

### Vaihe 1: App Registration (Entra ID)

1. Azure Portal → Entra ID → App registrations → New registration
2. Nimi: `JKR Tiedontuonti`
3. Supported account types: `Single tenant`
4. Redirect URI: lisää Flutter-sovelluksen redirect URI
5. API permissions: lisää `https://ossrdbms-aad.database.windows.net/user_impersonation`

**Tallenna:**
- `Application (client) ID` → `AZURE_CLIENT_ID`
- `Directory (tenant) ID` → `AZURE_TENANT_ID`

### Vaihe 2: Entra ID -ryhmien luonti

1. Azure Portal → Entra ID → Groups → New group
2. Luo ryhmät:
   - **JKR_EDITOR** (Security group) – käyttäjät jotka voivat muokata dataa
   - **JKR_VIEWER** (Security group) – vain lukuoikeus
3. Lisää käyttäjät ryhmiin

### Vaihe 3: PostgreSQL Flexible Server – Entra ID -aktivointi

1. Azure Portal → PostgreSQL Flexible Server → Authentication
2. Ota käyttöön: `Microsoft Entra authentication only` tai `PostgreSQL and Microsoft Entra authentication`
3. Lisää Entra AD admin (tarvitaan kertaluonteisesti ryhmien rekisteröintiin)

### Vaihe 4: Ryhmien rekisteröinti PostgreSQL-rooleiksi

Kirjaudu kantaan Entra AD adminina ja aja:

```sql
-- Rekisteröi Entra ID -ryhmät PostgreSQL-rooleiksi
-- Käytä ryhmien Object ID:tä (löytyy Azure Portal → Groups)

-- JKR_EDITOR-ryhmä → mapätään jkr_editor-rooliin
SELECT * FROM pgaadauth_create_principal('JKR_EDITOR', false, true);
GRANT jkr_editor TO "JKR_EDITOR";

-- JKR_VIEWER-ryhmä → mapätään jkr_viewer-rooliin
SELECT * FROM pgaadauth_create_principal('JKR_VIEWER', false, true);
GRANT jkr_viewer TO "JKR_VIEWER";
```

`pgaadauth_create_principal`-parametrit:
- `name` – Entra ID -ryhmän nimi (täsmälleen sama kuin Azuressa)
- `isAdmin` = `false` – EI admin-oikeuksia
- `isManagedIdentity` = `true` ryhmille (ryhmä tulkitaan "service principal" -tyyppiseksi)

**Tämän jälkeen jokainen ryhmän jäsen voi kirjautua kantaan omilla tunnuksillaan.**

### Vaihe 5: Ympäristömuuttujat (.env)

```env
# Entra ID
AZURE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
AZURE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Azure PostgreSQL Flexible Server
JKR_DB_HOST=jkr-server.postgres.database.azure.com
JKR_DB_PORT=5432
JKR_DB=jkr
# JKR_USER ja JKR_PASSWORD eivät ole enää tarpeen per-user yhteyksissä
```

## Audit Trail

### Mitä lokitetaan automaattisesti

Kun käyttäjä `matti.meikalainen@lahti.fi` (JKR_EDITOR-ryhmän jäsen) tekee API-kutsun:

1. **PostgreSQL log_statement** näyttää:
   ```
   LOG:  statement: INSERT INTO jkr.kuljetus (...) VALUES (...)
   DETAIL:  User: matti.meikalainen@lahti.fi
   ```

2. **pgaudit** (jos aktivoitu):
   ```
   AUDIT: SESSION,1,1,WRITE,INSERT,,jkr.kuljetus,"INSERT INTO jkr.kuljetus ...",<none>
   ```

3. **Azure Diagnostic Logs** (Log Analytics):
   - Näkyy suoraan Azure Portalissa
   - Käyttäjä, aika, SQL-lause, kesto
   - Voidaan yhdistää Azure Monitoriin ja hälytyksin

### pgaudit-aktivointi (suositus)

```sql
-- Azure Portal → Server parameters:
-- shared_preload_libraries = 'pgaudit'
-- pgaudit.log = 'write'  (tai 'all' tarkempaan seurantaan)

CREATE EXTENSION IF NOT EXISTS pgaudit;
```

## Koodiarkkitehtuurin muutokset

### Nykyinen malli (yksittäinen engine)

```
conf.py → dbconf (ympäristömuuttujat)
    ↓
database.py → engine = create_engine(...)   ← globaali, yksi käyttäjä
    ↓
dbprovider.py → Session(engine)
```

### Uusi malli (per-user engine)

```
Flutter → Entra ID token → FastAPI
    ↓
auth.py → validate_token(token) → claims (käyttäjänimi, ryhmät)
    ↓
database.py → create_user_engine(username, access_token)  ← per-request
    ↓
dbprovider.py → Session(user_engine)  ← käyttäjän tunnuksilla
```

### Muutettavat tiedostot

| Tiedosto | Muutos |
|----------|--------|
| `jkrimporter/api/auth.py` | **UUSI** – Token-validointi, JWKS-haku, käyttäjän tunnistus |
| `jkrimporter/providers/db/database.py` | Lisää `create_user_engine()` funktio |
| `jkrimporter/api/api.py` | Lisää `Depends(validate_token)` kaikkiin endpointeihin |
| `jkrimporter/conf.py` | Lisää `AZURE_TENANT_ID`, `AZURE_CLIENT_ID` |
| `.env.template` | Lisää Entra ID -muuttujat |
| `pyproject.toml` | Lisää `python-jose`, `httpx` riippuvuudet |

### Taaksepäin yhteensopivuus

Globaali `engine` säilytetään CLI-komentoja varten (jkr import, jkr tiedontuottaja add jne.).
API-endpointit käyttävät per-user engineä kun `AZURE_TENANT_ID` on asetettu.
Jos Entra ID ei ole konfiguroitu, API toimii vanhalla tavalla (kehitysympäristö).

```python
# database.py – uusi funktio
def create_user_engine(username: str, access_token: str):
    """Luo tietokanta-engine käyttäjän Entra ID -tunnuksilla."""
    from urllib.parse import quote_plus
    host = conf.dbconf["host"]
    port = conf.dbconf["port"]
    dbname = conf.dbconf["dbname"]
    
    return create_engine(
        f"postgresql://{quote_plus(username)}:{quote_plus(access_token)}"
        f"@{host}:{port}/{dbname}",
        connect_args={"sslmode": "require"},
        pool_size=1,
        max_overflow=0,
        pool_pre_ping=True,
        json_serializer=json_dumps,
    )
```

## Turvallisuus

- **Token-validointi** aina backendissä (ei luoteta frontendiin)
- **JWKS-avaimet** haetaan Microsoftin endpointista ja cachetaan
- **SSL/TLS** pakollinen kaikissa yhteyksissä (Azure vaatii)
- **Token-vanheneminen** ~1h – Flutter pyytää uuden tokenin automaattisesti (MSAL hoitaa)
- **Ei salasanoja** – ei tarvita JKR_PASSWORD-ympäristömuuttujaa API-yhteyksissä
- **Ryhmäpohjainen pääsy** – oikeudet hallitaan Entra ID:ssä, ei kantatasolla

## Jatkokehitys

1. **Token-välimuisti backendissä** – samaa engineä voi käyttää niin kauan kuin token on voimassa
2. **Refresh token** – Flutter MSAL hoitaa automaattisesti
3. **RBAC endpointeissa** – tarkista ryhmäjäsenyys tokenin `groups`-claimista
4. **Rate limiting** – per-user rajoitukset
5. **Managed Identity** – taustatehtävät (batch import) voivat käyttää Managed Identityä globaalilla enginellä
