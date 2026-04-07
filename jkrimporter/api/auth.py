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
from typing import Dict, List, Optional

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
    def __init__(self, oid: str, name: str, email: str, roles: List[str], groups: List[str]):
        self.oid = oid
        self.name = name
        self.email = email
        self.roles = roles
        self.groups = groups

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

    # Määritä roolit ryhmäjäsenyyksien perusteella
    roles = []
    if AZURE_ADMIN_GROUP_ID and AZURE_ADMIN_GROUP_ID in groups:
        roles.append(UserRole.ADMIN)
    if AZURE_VIEWER_GROUP_ID and AZURE_VIEWER_GROUP_ID in groups:
        roles.append(UserRole.VIEWER)

    logger.info(
        "Käyttäjä autentikoitu: %s (%s), roolit: %s",
        name, email, roles or ["ei roolia"],
    )

    return CurrentUser(oid=oid, name=name, email=email, roles=roles, groups=groups)


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
# Julkiset dependencyt endpointeille
# ---------------------------------------------------------------------------
# Käytä näitä FastAPI Depends():ssä:
#   - require_authenticated: token vaaditaan, mutta ei roolitarkistusta
#   - require_admin: vaatii sg-jkr-admin-sql -ryhmän
#   - require_viewer_or_admin: vaatii sg-jkr-viewer-sql tai admin-ryhmän
require_authenticated = _validate_token
