"""
Azure AD -autentikointi ja -auktorisointi JKR API:lle.

Validoi Azure AD:n myöntämät JWT-tokenit (access_token) ja tarkistaa
käyttäjän ryhmäjäsenyydet.

Ympäristömuuttujat:
    AZURE_TENANT_ID     - Azure AD tenant ID
    AZURE_CLIENT_ID     - App Registration client ID (yleisö/audience)
    AZURE_ADMIN_GROUP_ID  - sg-jkr-admin-sql Security Groupin Object ID
    AZURE_VIEWER_GROUP_ID - sg-jkr-viewer-sql Security Groupin Object ID (valinnainen)

Flutter-front hakee tokenin MSAL:lla ja lähettää sen Authorization-headerissa:
    Authorization: Bearer <access_token>
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional

import httpx
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

logger = logging.getLogger("jkr-auth")

# ---------------------------------------------------------------------------
# Konfiguraatio ympäristömuuttujista
# ---------------------------------------------------------------------------
AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")
AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
AZURE_ADMIN_GROUP_ID = os.environ.get("AZURE_ADMIN_GROUP_ID", "")
AZURE_VIEWER_GROUP_ID = os.environ.get("AZURE_VIEWER_GROUP_ID", "")

# App Roles -pohjainen reitti (toimii myös groups overage -tilanteessa, kun
# käyttäjä kuuluu liian moneen ryhmään jotta groups-claim tulisi tokeniin).
# Tyhjä = reitti pois käytöstä, vain groups-claimia katsotaan.
AZURE_ADMIN_APP_ROLE = os.environ.get("AZURE_ADMIN_APP_ROLE", "").strip()
AZURE_VIEWER_APP_ROLE = os.environ.get("AZURE_VIEWER_APP_ROLE", "").strip()

# Jos UNSECURE=1 tai UNSECURE=true, autentikointi ohitetaan kokonaan (vain testauskäyttöön!)
_UNSECURE = os.environ.get("UNSECURE", "").strip().lower() in ("1", "true")
if _UNSECURE:
    logger.warning("⚠️  UNSECURE-tila on päällä! Autentikointi on ohitettu. ÄLÄ käytä tuotannossa!")

def _jwks_url() -> str:
    """JWKS URL muodostetaan dynaamisesti, jotta AZURE_TENANT_ID voi tulla myöhemmin."""
    return f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/discovery/v2.0/keys"

# ---------------------------------------------------------------------------
# JWKS-avainten välimuisti
# ---------------------------------------------------------------------------
_jwks_cache: Optional[Dict] = None


async def _get_jwks() -> Dict:
    """Hakee ja cachettaa Azure AD:n julkiset avaimet (JWKS)."""
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache
    async with httpx.AsyncClient() as client:
        resp = await client.get(_jwks_url())
        resp.raise_for_status()
        _jwks_cache = resp.json()
        logger.info("Azure AD JWKS-avaimet haettu (%d avainta)", len(_jwks_cache.get("keys", [])))
        return _jwks_cache


def clear_jwks_cache():
    """Tyhjentää JWKS-välimuistin (esim. avainten kierron yhteydessä)."""
    global _jwks_cache
    _jwks_cache = None


def _find_rsa_key(token: str, jwks: Dict) -> Optional[Dict]:
    """Etsii oikean RSA-avaimen tokenin kid-headerin perusteella."""
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError:
        return None
    kid = unverified_header.get("kid")
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


# ---------------------------------------------------------------------------
# Roolit
# ---------------------------------------------------------------------------
class UserRole:
    ADMIN = "admin"
    VIEWER = "viewer"
    NONE = "none"


class CurrentUser:
    """Autentikoitu käyttäjä."""
    def __init__(
        self,
        oid: str,
        name: str,
        email: str,
        roles: List[str],
        groups: List[str],
        claims: Optional[Dict] = None,
        unverified_header: Optional[Dict] = None,
    ):
        self.oid = oid
        self.name = name
        self.email = email
        self.roles = roles
        self.groups = groups
        # Raw token-claimit ja header diagnostiikkaa varten (vain /auth/debug käyttää).
        # Jää tyhjäksi UNSECURE-tilassa ja WS-validaattorin polussa.
        self.claims = claims or {}
        self.unverified_header = unverified_header or {}

    @property
    def is_admin(self) -> bool:
        return UserRole.ADMIN in self.roles

    @property
    def is_viewer(self) -> bool:
        return UserRole.VIEWER in self.roles


# ---------------------------------------------------------------------------
# Bearer-token security scheme
# ---------------------------------------------------------------------------
_bearer_scheme = HTTPBearer(auto_error=not _UNSECURE)


async def _validate_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
) -> CurrentUser:
    """Validoi Azure AD Bearer -tokenin ja palauttaa käyttäjätiedot."""
    if _UNSECURE:
        return CurrentUser(
            oid="unsecure-test-user",
            name="Test User (UNSECURE)",
            email="test@unsecure.local",
            roles=[UserRole.ADMIN, UserRole.VIEWER],
            groups=[],
        )

    token = credentials.credentials

    if not AZURE_TENANT_ID or not AZURE_CLIENT_ID:
        logger.error("AZURE_TENANT_ID tai AZURE_CLIENT_ID puuttuu!")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Azure AD -konfiguraatio puuttuu palvelimelta",
        )

    # Hae JWKS-avaimet
    try:
        jwks = await _get_jwks()
    except Exception as e:
        logger.error("JWKS-avainten haku epäonnistui: %s", e)
        # Yritä uudelleen tyhjentämällä cache
        clear_jwks_cache()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Azure AD -avainten haku epäonnistui",
        )

    rsa_key = _find_rsa_key(token, jwks)
    if rsa_key is None:
        # Avain saattoi kiertyä – tyhjennä cache ja yritä uudelleen
        clear_jwks_cache()
        try:
            jwks = await _get_jwks()
            rsa_key = _find_rsa_key(token, jwks)
        except Exception:
            pass
        if rsa_key is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token-avainta ei löydy",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Validoi token
    try:
        # Azure AD:n access_token audience on "api://<clientId>" kun käytetään
        # custom API scopea (access_as_user).
        # python-jose ei hyväksy listaa audience-parametrina, joten
        # tarkistetaan ensin aud manuaalisesti ja annetaan decode:lle yksi arvo.
        unverified_claims = jwt.get_unverified_claims(token)
        token_aud = unverified_claims.get("aud", "")
        expected_audiences = {AZURE_CLIENT_ID, f"api://{AZURE_CLIENT_ID}"}
        if token_aud not in expected_audiences:
            raise JWTError(f"Väärä audience: {token_aud}")
        # Azure AD voi antaa issuerin v1.0- tai v2.0-muodossa riippuen
        # app registrationin ja tokenin konfiguraatiosta.
        # python-jose ei hyväksy listaa issuerille, joten tarkistetaan manuaalisesti.
        token_iss = unverified_claims.get("iss", "")
        valid_issuers = {
            f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/v2.0",
            f"https://sts.windows.net/{AZURE_TENANT_ID}/",
        }
        if token_iss not in valid_issuers:
            raise JWTError(f"Invalid issuer: {token_iss}")
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=token_aud,
            options={"verify_iss": False},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token on vanhentunut",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        logger.warning("Token-validointi epäonnistui: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Virheellinen token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Poimi käyttäjätiedot tokenista
    oid = payload.get("oid", "")
    name = payload.get("name", "")
    email = payload.get("preferred_username", payload.get("email", ""))
    groups = payload.get("groups", [])
    if not isinstance(groups, list):
        groups = []
    token_app_roles = payload.get("roles", [])
    if not isinstance(token_app_roles, list):
        token_app_roles = []

    # Määritä roolit OR-logiikalla: rooli annetaan jos joko
    #   (a) Security Groupin Object ID löytyy tokenin groups-claimista, TAI
    #   (b) konfiguroitu App Role -arvo löytyy tokenin roles-claimista.
    # App Roles -reitti toimii myös kun käyttäjä kuuluu liian moneen ryhmään
    # jotta groups-claim mahtuisi tokeniin (overage).
    is_admin = (
        (bool(AZURE_ADMIN_GROUP_ID) and AZURE_ADMIN_GROUP_ID in groups)
        or (bool(AZURE_ADMIN_APP_ROLE) and AZURE_ADMIN_APP_ROLE in token_app_roles)
    )
    is_viewer = (
        (bool(AZURE_VIEWER_GROUP_ID) and AZURE_VIEWER_GROUP_ID in groups)
        or (bool(AZURE_VIEWER_APP_ROLE) and AZURE_VIEWER_APP_ROLE in token_app_roles)
    )

    roles = []
    if is_admin:
        roles.append(UserRole.ADMIN)
    if is_viewer:
        roles.append(UserRole.VIEWER)

    logger.info(
        "Käyttäjä autentikoitu: %s (%s), roolit: %s (groups=%d, app_roles=%s)",
        name, email, roles or ["ei roolia"], len(groups), token_app_roles or "[]",
    )

    try:
        header = jwt.get_unverified_header(token)
    except JWTError:
        header = {}

    return CurrentUser(
        oid=oid,
        name=name,
        email=email,
        roles=roles,
        groups=groups,
        claims=payload,
        unverified_header=header,
    )


async def require_admin(
    user: CurrentUser = Depends(_validate_token),
) -> CurrentUser:
    """Vaatii admin-roolin (sg-jkr-admin-sql)."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tämä toiminto vaatii admin-oikeudet (sg-jkr-admin-sql)",
        )
    return user


async def require_viewer_or_admin(
    user: CurrentUser = Depends(_validate_token),
) -> CurrentUser:
    """Vaatii vähintään viewer-roolin (sg-jkr-viewer-sql tai sg-jkr-admin-sql)."""
    if not user.is_admin and not user.is_viewer:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tämä toiminto vaatii vähintään lukuoikeudet (sg-jkr-viewer-sql)",
        )
    return user


# ---------------------------------------------------------------------------
# WebSocket-autentikointi (token query-parametrista)
# ---------------------------------------------------------------------------
async def validate_ws_token(token: Optional[str]) -> CurrentUser:
    """Validoi Bearer-tokenin WebSocket-yhteyksissä (query param ?token=...).

    Palauttaa CurrentUser tai nostaa HTTPException.
    """
    if _UNSECURE:
        return CurrentUser(
            oid="unsecure-test-user",
            name="Test User (UNSECURE)",
            email="test@unsecure.local",
            roles=[UserRole.ADMIN, UserRole.VIEWER],
            groups=[],
        )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token puuttuu (käytä ?token=... query-parametria)",
        )

    # Käytetään samaa validointilogiikkaa kuin _validate_token
    from fastapi.security import HTTPAuthorizationCredentials
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    return await _validate_token(credentials=creds)


# ---------------------------------------------------------------------------
# Graph API -kutsu App Registration -diagnostiikkaan (/auth/debug käyttää)
# ---------------------------------------------------------------------------
_graph_token_cache: Dict[str, Any] = {"token": None, "expires_at": 0.0}


async def _get_graph_app_token() -> str:
    """Hakee Microsoft Graph -tokenin client_credentials-flowlla (välimuistilla).

    Käyttää samaa AZURE_CLIENT_ID/SECRET-paria kuin token-validointi (palvelimen
    oma App Registration). Vaatii Graph-oikeudet kyseiselle App Reg:lle.
    """
    now = time.time()
    if _graph_token_cache["token"] and _graph_token_cache["expires_at"] > now + 60:
        return _graph_token_cache["token"]

    client_secret = os.environ.get("AZURE_CLIENT_SECRET", "")
    if not all([AZURE_TENANT_ID, AZURE_CLIENT_ID, client_secret]):
        raise RuntimeError(
            "AZURE_TENANT_ID, AZURE_CLIENT_ID tai AZURE_CLIENT_SECRET puuttuu"
        )

    token_url = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token"
    async with httpx.AsyncClient() as http:
        resp = await http.post(
            token_url,
            data={
                "client_id": AZURE_CLIENT_ID,
                "client_secret": client_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            },
        )
        resp.raise_for_status()
        body = resp.json()

    _graph_token_cache["token"] = body["access_token"]
    _graph_token_cache["expires_at"] = now + body.get("expires_in", 3600)
    return _graph_token_cache["token"]


# Default Access -App Role:lla on aina tämä id, eikä se päädy tokenin roles-claimiin
_DEFAULT_ACCESS_APP_ROLE_ID = "00000000-0000-0000-0000-000000000000"


async def fetch_app_registration_diagnostics() -> Dict[str, Any]:
    """Hakee App Registrationin appRoles + servicePrincipal.appRoleAssignedTo.

    Käyttötarkoitus: /auth/debug-endpoint näyttää mitä App Roles -määrityksiä
    ja role-assignmentteja Azuressa on, jotta voidaan vahvistaa että käyttäjän
    Security Group on oikein assignattu App Role:lle.

    Palauttaa dictin jossa joko data tai 'error'-avain (jos Graph-kutsu kaatuu
    tai oikeudet puuttuvat).
    """
    if not AZURE_CLIENT_ID:
        return {"error": "AZURE_CLIENT_ID puuttuu palvelimelta"}

    try:
        token = await _get_graph_app_token()
    except Exception as e:  # pragma: no cover
        return {"error": f"Graph-tokenin haku epäonnistui: {e}"}

    headers = {"Authorization": f"Bearer {token}"}
    base = "https://graph.microsoft.com/v1.0"
    result: Dict[str, Any] = {"app_id": AZURE_CLIENT_ID}

    async with httpx.AsyncClient(timeout=15.0) as http:
        app_resp = await http.get(
            f"{base}/applications(appId='{AZURE_CLIENT_ID}')",
            headers=headers,
        )
        if app_resp.status_code == 403:
            return {
                "app_id": AZURE_CLIENT_ID,
                "error": (
                    "Graph-kutsu kielletty (403). Lisää App Registrationille "
                    "Graph-oikeus 'Application.Read.All' (Application-tyyppinen) ja "
                    "anna admin consent — sitten /auth/debug pystyy näyttämään "
                    "App Roles -määritykset ja assignmentit."
                ),
                "permission_needed": "Microsoft Graph 'Application.Read.All' (application)",
            }
        if app_resp.status_code != 200:
            return {
                "app_id": AZURE_CLIENT_ID,
                "error": f"Graph applications palautti {app_resp.status_code}: "
                         f"{app_resp.text[:300]}",
            }

        app_data = app_resp.json()
        result["app_display_name"] = app_data.get("displayName")
        result["app_object_id"] = app_data.get("id")
        result["sign_in_audience"] = app_data.get("signInAudience")
        result["group_membership_claims"] = app_data.get("groupMembershipClaims")

        app_roles = [
            {
                "id": r.get("id"),
                "value": r.get("value"),
                "displayName": r.get("displayName"),
                "description": r.get("description"),
                "isEnabled": r.get("isEnabled"),
                "allowedMemberTypes": r.get("allowedMemberTypes"),
            }
            for r in app_data.get("appRoles", [])
        ]
        result["app_roles_defined"] = app_roles

        sp_resp = await http.get(
            f"{base}/servicePrincipals(appId='{AZURE_CLIENT_ID}')",
            headers=headers,
        )
        if sp_resp.status_code != 200:
            result["sp_error"] = (
                f"servicePrincipals palautti {sp_resp.status_code}: "
                f"{sp_resp.text[:200]}"
            )
            return result

        sp_data = sp_resp.json()
        sp_id = sp_data["id"]
        result["service_principal_id"] = sp_id

        assign_resp = await http.get(
            f"{base}/servicePrincipals/{sp_id}/appRoleAssignedTo",
            headers=headers,
        )
        if assign_resp.status_code != 200:
            result["assignments_error"] = (
                f"appRoleAssignedTo palautti {assign_resp.status_code}: "
                f"{assign_resp.text[:200]}"
            )
            return result

        role_value_by_id = {r["id"]: r["value"] for r in app_roles if r.get("id")}
        assignments = []
        for a in assign_resp.json().get("value", []):
            role_id = a.get("appRoleId") or ""
            if role_id == _DEFAULT_ACCESS_APP_ROLE_ID:
                role_value = "(Default Access — ei roles-claimia tokeniin)"
            else:
                role_value = role_value_by_id.get(
                    role_id, f"(tuntematon role id: {role_id})"
                )
            assignments.append({
                "principal_display_name": a.get("principalDisplayName"),
                "principal_type": a.get("principalType"),
                "principal_id": a.get("principalId"),
                "app_role_value": role_value,
                "app_role_id": role_id,
                "assigned_at": a.get("createdDateTime"),
            })

        # Lajittele admin/editor ensin, default access viimeiseksi luettavuuden vuoksi
        assignments.sort(key=lambda x: (
            x["app_role_id"] == _DEFAULT_ACCESS_APP_ROLE_ID,
            (x.get("app_role_value") or "").lower(),
            (x.get("principal_display_name") or "").lower(),
        ))
        result["app_role_assignments"] = assignments

    return result


# ---------------------------------------------------------------------------
# Julkiset dependencyt endpointeille
# ---------------------------------------------------------------------------
# Käytä näitä FastAPI Depends():ssä:
#   - require_authenticated: token vaaditaan, mutta ei roolitarkistusta
#   - require_admin: vaatii sg-jkr-admin-sql -ryhmän
#   - require_viewer_or_admin: vaatii sg-jkr-viewer-sql tai admin-ryhmän
require_authenticated = _validate_token
