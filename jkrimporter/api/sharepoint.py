"""
SharePoint Graph API -integraatio.

Käyttää client credentials -flowta (AZURE_CLIENT_ID + AZURE_CLIENT_SECRET)
ja Sites.Selected -oikeutta SharePoint-siten tiedostojen hallintaan.

Ympäristömuuttujat:
    AZURE_TENANT_ID        - Azure AD tenant ID
    AZURE_CLIENT_ID        - App Registration client ID
    AZURE_CLIENT_SECRET    - App Registrationin client secret
    SHAREPOINT_SITE_ID     - SharePoint Site ID (esim. contoso.sharepoint.com,guid1,guid2)
    SHAREPOINT_FOLDER      - Oletuskansio (esim. /Shared Documents/JKR-ajot)
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("jkr-sharepoint")

# ---------------------------------------------------------------------------
# Konfiguraatio
# ---------------------------------------------------------------------------
AZURE_TENANT_ID = os.environ.get("AZURE_TENANT_ID", "")
AZURE_CLIENT_ID = os.environ.get("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET = os.environ.get("AZURE_CLIENT_SECRET", "")
SHAREPOINT_SITE_ID = os.environ.get("SHAREPOINT_SITE_ID", "")
SHAREPOINT_FOLDER = os.environ.get("SHAREPOINT_FOLDER", "/Shared Documents/JKR-ajot")

# ---------------------------------------------------------------------------
# Token-välimuisti
# ---------------------------------------------------------------------------
_token_cache: Dict[str, Any] = {"access_token": None, "expires_at": 0}


async def _get_app_token() -> str:
    """Hakee application-tokenin client credentials -flowlla (välimuistilla)."""
    now = time.time()
    if _token_cache["access_token"] and _token_cache["expires_at"] > now + 60:
        return _token_cache["access_token"]

    if not all([AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET]):
        raise RuntimeError(
            "SharePoint-konfiguraatio puuttuu: AZURE_TENANT_ID, AZURE_CLIENT_ID "
            "ja AZURE_CLIENT_SECRET ympäristömuuttujat vaaditaan."
        )

    token_url = f"https://login.microsoftonline.com/{AZURE_TENANT_ID}/oauth2/v2.0/token"
    data = {
        "client_id": AZURE_CLIENT_ID,
        "client_secret": AZURE_CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
        "grant_type": "client_credentials",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, data=data)
        resp.raise_for_status()
        body = resp.json()

    _token_cache["access_token"] = body["access_token"]
    _token_cache["expires_at"] = now + body.get("expires_in", 3600)
    logger.info("SharePoint application-token haettu (voimassa %ds)", body.get("expires_in", 0))
    return _token_cache["access_token"]


def _graph_base() -> str:
    """Graph API base URL siten drive:lle."""
    return f"https://graph.microsoft.com/v1.0/sites/{SHAREPOINT_SITE_ID}/drive"


def _resolve_folder_path(folder: Optional[str] = None) -> str:
    """Palauttaa kansion polun Graph API -muodossa."""
    path = folder or SHAREPOINT_FOLDER
    # Poista alku- ja loppuslashit normalisointia varten
    path = path.strip("/")
    return path


# ---------------------------------------------------------------------------
# Julkiset funktiot
# ---------------------------------------------------------------------------

async def is_configured() -> bool:
    """Tarkistaa onko SharePoint-integraatio konfiguroitu."""
    return bool(AZURE_TENANT_ID and AZURE_CLIENT_ID and AZURE_CLIENT_SECRET and SHAREPOINT_SITE_ID)


async def list_folder(folder: Optional[str] = None) -> List[Dict[str, Any]]:
    """Listaa kansion sisällön SharePointista.

    Palauttaa listan dict-olioista:
        name, size, lastModified, type ("file"/"folder"), webUrl, id
    """
    token = await _get_app_token()
    folder_path = _resolve_folder_path(folder)

    url = f"{_graph_base()}/root:/{folder_path}:/children"
    params = {"$select": "id,name,size,lastModifiedDateTime,file,folder,webUrl"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params=params,
            timeout=30.0,
        )
        resp.raise_for_status()
        data = resp.json()

    items = []
    for item in data.get("value", []):
        items.append({
            "id": item.get("id"),
            "name": item.get("name"),
            "size": item.get("size"),
            "lastModified": item.get("lastModifiedDateTime"),
            "type": "folder" if "folder" in item else "file",
            "webUrl": item.get("webUrl"),
            "childCount": item.get("folder", {}).get("childCount") if "folder" in item else None,
        })
    return items


async def download_file(file_path: str) -> tuple:
    """Lataa tiedoston SharePointista.

    Palauttaa (content_bytes, filename, content_type).
    """
    token = await _get_app_token()
    path = file_path.strip("/")

    # Hae tiedoston metadata + download URL
    # HUOM: @microsoft.graph.downloadUrl ei palaudu $select:n kanssa,
    # joten haetaan ilman $select-rajausta.
    url = f"{_graph_base()}/root:/{path}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        resp.raise_for_status()
        meta = resp.json()

    download_url = meta.get("@microsoft.graph.downloadUrl") or meta.get("@content.downloadUrl")
    if not download_url:
        raise RuntimeError(f"Download URL ei saatavilla tiedostolle: {file_path}")

    filename = meta.get("name", file_path.split("/")[-1])
    content_type = meta.get("file", {}).get("mimeType", "application/octet-stream")

    async with httpx.AsyncClient() as client:
        resp = await client.get(download_url, timeout=120.0)
        resp.raise_for_status()

    return resp.content, filename, content_type


async def upload_file(
    file_content: bytes,
    filename: str,
    folder: Optional[str] = None,
) -> Dict[str, Any]:
    """Lataa tiedoston SharePointiin.

    Käyttää yksinkertaista PUT-uploadia (< 4 MB) tai upload sessionia (>= 4 MB).
    """
    token = await _get_app_token()
    folder_path = _resolve_folder_path(folder)
    target = f"{folder_path}/{filename}"

    if len(file_content) < 4 * 1024 * 1024:
        return await _upload_small(token, target, file_content)
    else:
        return await _upload_large(token, target, file_content)


async def _upload_small(token: str, target_path: str, content: bytes) -> Dict[str, Any]:
    """PUT-upload pienille tiedostoille (< 4 MB)."""
    url = f"{_graph_base()}/root:/{target_path}:/content"
    async with httpx.AsyncClient() as client:
        resp = await client.put(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/octet-stream",
            },
            content=content,
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()

    logger.info("Tiedosto ladattu SharePointiin: %s (%d tavua)", target_path, len(content))
    return {
        "id": data.get("id"),
        "name": data.get("name"),
        "size": data.get("size"),
        "webUrl": data.get("webUrl"),
    }


async def _upload_large(token: str, target_path: str, content: bytes) -> Dict[str, Any]:
    """Upload session isoille tiedostoille (>= 4 MB)."""
    # 1. Luo upload session
    session_url = f"{_graph_base()}/root:/{target_path}:/createUploadSession"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            session_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"item": {"@microsoft.graph.conflictBehavior": "replace"}},
            timeout=30.0,
        )
        resp.raise_for_status()
        upload_url = resp.json()["uploadUrl"]

    # 2. Lähetä 3.5 MB chunkeissa
    chunk_size = 3_500_000  # ~3.5 MB (pitää olla jaollinen 320 KiB:llä)
    chunk_size = (chunk_size // 327680) * 327680  # Pyöristä alas
    total = len(content)
    result = None

    async with httpx.AsyncClient() as client:
        offset = 0
        while offset < total:
            end = min(offset + chunk_size, total)
            chunk = content[offset:end]
            content_range = f"bytes {offset}-{end - 1}/{total}"

            resp = await client.put(
                upload_url,
                headers={
                    "Content-Length": str(len(chunk)),
                    "Content-Range": content_range,
                },
                content=chunk,
                timeout=120.0,
            )
            resp.raise_for_status()
            offset = end

            if resp.status_code in (200, 201):
                result = resp.json()

    if not result:
        raise RuntimeError("Upload session päättyi ilman vastausta")

    logger.info("Iso tiedosto ladattu SharePointiin: %s (%d tavua)", target_path, total)
    return {
        "id": result.get("id"),
        "name": result.get("name"),
        "size": result.get("size"),
        "webUrl": result.get("webUrl"),
    }
