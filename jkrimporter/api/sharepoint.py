"""
SharePoint Graph API -integraatio.

Käyttää client credentials -flowta (AZURE_CLIENT_ID + AZURE_CLIENT_SECRET)
ja Sites.Selected -oikeutta SharePoint-siten tiedostojen hallintaan.

Ympäristömuuttujat:
    AZURE_TENANT_ID        - Azure AD tenant ID
    AZURE_CLIENT_ID        - App Registration client ID
    AZURE_CLIENT_SECRET    - App Registrationin client secret
    SHAREPOINT_SITE_ID     - SharePoint Site ID (esim. contoso.sharepoint.com,guid1,guid2)
    SHAREPOINT_INPUT_FOLDER  - Syöttökansio (esim. /Shared Documents/JKR-input)
    SHAREPOINT_OUTPUT_FOLDER - Tuloskansio (esim. /Shared Documents/JKR-output)
"""

import logging
import os
import time
from datetime import datetime, timezone
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
SHAREPOINT_INPUT_FOLDER = os.environ.get("SHAREPOINT_INPUT_FOLDER", "/Shared Documents/JKR-input")
SHAREPOINT_OUTPUT_FOLDER = os.environ.get("SHAREPOINT_OUTPUT_FOLDER", "/Shared Documents/JKR-output")

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


def _resolve_folder_path(folder: Optional[str] = None, default: Optional[str] = None) -> str:
    """Palauttaa kansion polun Graph API -muodossa."""
    path = folder or default or SHAREPOINT_INPUT_FOLDER
    # Poista alku- ja loppuslashit normalisointia varten
    path = path.strip("/")
    return path


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------

async def _set_audit_description(
    token: str,
    item_id: str,
    action: str,
    user_name: str,
    user_email: str,
    details: str = "",
) -> None:
    """Asettaa DriveItem:n description-kenttään audit-tiedot."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    desc = f"[{ts}] {action} — {user_name} ({user_email})"
    if details:
        desc += f" | {details}"

    url = f"{_graph_base()}/items/{item_id}"
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={"description": desc},
            timeout=15.0,
        )
        if resp.status_code >= 400:
            logger.warning("Audit description asetus epäonnistui (item %s): %s", item_id, resp.text)
        else:
            logger.info("Audit: %s", desc)


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


async def download_file_to_disk(
    file_path: str,
    target_dir: str,
    user_name: str = "",
    user_email: str = "",
) -> Dict[str, Any]:
    """Lataa tiedoston SharePointista suoraan palvelimen levylle.

    Streamaa sisällön suoraan tiedostoon ilman, että koko tiedosto
    pidetään muistissa. Sopii suurillekin tiedostoille.

    Palauttaa dict: filename, target_path, size
    """
    import aiofiles
    from pathlib import Path

    token = await _get_app_token()
    path = file_path.strip("/")

    # Hae tiedoston metadata + download URL
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
    file_size = meta.get("size", 0)

    # Varmista kohdehakemisto
    dest_dir = Path(target_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename

    # Streamaa tiedosto levylle
    written = 0
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", download_url, timeout=300.0) as stream:
            stream.raise_for_status()
            async with aiofiles.open(str(dest_path), "wb") as f:
                async for chunk in stream.aiter_bytes(chunk_size=1024 * 1024):
                    await f.write(chunk)
                    written += len(chunk)

    logger.info(
        "SharePoint -> disk: %s (%d tavua) -> %s",
        filename, written, str(dest_path),
    )

    # Audit trail
    item_id = meta.get("id")
    if item_id and user_name:
        await _set_audit_description(
            token, item_id, "Download to server", user_name, user_email,
            f"{filename} -> {target_dir}",
        )

    return {
        "filename": filename,
        "target_path": str(dest_path),
        "size": written,
        "sharepoint_path": file_path,
    }


async def upload_file(
    file_content: bytes,
    filename: str,
    folder: Optional[str] = None,
    user_name: str = "",
    user_email: str = "",
) -> Dict[str, Any]:
    """Lataa tiedoston SharePointiin.

    Käyttää yksinkertaista PUT-uploadia (< 4 MB) tai upload sessionia (>= 4 MB).
    """
    token = await _get_app_token()
    folder_path = _resolve_folder_path(folder, default=SHAREPOINT_OUTPUT_FOLDER)
    target = f"{folder_path}/{filename}"

    if len(file_content) < 4 * 1024 * 1024:
        result = await _upload_small(token, target, file_content)
    else:
        result = await _upload_large(token, target, file_content)

    if result.get("id") and user_name:
        await _set_audit_description(
            token, result["id"], "Upload", user_name, user_email,
            f"{filename} ({len(file_content)} tavua)",
        )
    return result


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


async def delete_file(file_path: str, user_name: str = "", user_email: str = "") -> None:
    """Poistaa tiedoston SharePointista."""
    token = await _get_app_token()
    path = file_path.strip("/")

    # Logita audit ennen poistoa (koska poiston jälkeen itemiä ei voi päivittää)
    logger.info(
        "Audit: Delete — %s (%s) poisti tiedoston: %s",
        user_name, user_email, file_path,
    )

    url = f"{_graph_base()}/root:/{path}"
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            url,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        resp.raise_for_status()

    logger.info("Tiedosto poistettu SharePointista: %s", file_path)


async def move_file(source_path: str, dest_folder: str, new_name: Optional[str] = None, user_name: str = "", user_email: str = "") -> Dict[str, Any]:
    """Siirtää tiedoston toiseen kansioon SharePointissa.

    Args:
        source_path: Lähdetiedoston polku (esim. Shared Documents/JKR-input/data.csv)
        dest_folder: Kohdekansion polku (esim. Shared Documents/JKR-output)
        new_name: Uusi tiedostonimi (valinnainen, oletus: sama nimi)
    """
    token = await _get_app_token()
    src = source_path.strip("/")
    dst = dest_folder.strip("/")

    # Hae lähdetiedoston item ID
    url = f"{_graph_base()}/root:/{src}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
            params={"$select": "id,name"},
            timeout=30.0,
        )
        resp.raise_for_status()
        item = resp.json()

    item_id = item["id"]
    filename = new_name or item["name"]

    # Hae kohdekansion item ID
    folder_url = f"{_graph_base()}/root:/{dst}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            folder_url,
            headers={"Authorization": f"Bearer {token}"},
            params={"$select": "id"},
            timeout=30.0,
        )
        resp.raise_for_status()
        dest_item = resp.json()

    # PATCH: siirrä tiedosto
    patch_url = f"{_graph_base()}/items/{item_id}"
    body = {
        "parentReference": {"id": dest_item["id"]},
        "name": filename,
    }
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            patch_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=30.0,
        )
        resp.raise_for_status()
        result = resp.json()

    logger.info("Tiedosto siirretty: %s -> %s/%s", source_path, dest_folder, filename)

    if result.get("id") and user_name:
        await _set_audit_description(
            token, result["id"], "Move", user_name, user_email,
            f"{source_path} -> {dest_folder}/{filename}",
        )

    return {
        "id": result.get("id"),
        "name": result.get("name"),
        "webUrl": result.get("webUrl"),
    }


async def create_folder(folder_path: str, user_name: str = "", user_email: str = "") -> Dict[str, Any]:
    """Luo kansion SharePointiin.

    Args:
        folder_path: Kansion polku (esim. Shared Documents/JKR-output/2024)
    """
    token = await _get_app_token()
    path = folder_path.strip("/")

    # Erota parent-kansio ja uuden kansion nimi
    if "/" in path:
        parent = path.rsplit("/", 1)[0]
        name = path.rsplit("/", 1)[1]
        url = f"{_graph_base()}/root:/{parent}:/children"
    else:
        name = path
        url = f"{_graph_base()}/root/children"

    body = {
        "name": name,
        "folder": {},
        "@microsoft.graph.conflictBehavior": "fail",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=body,
            timeout=30.0,
        )
        resp.raise_for_status()
        result = resp.json()

    logger.info("Kansio luotu SharePointiin: %s", folder_path)

    if result.get("id") and user_name:
        await _set_audit_description(
            token, result["id"], "Create folder", user_name, user_email,
            folder_path,
        )

    return {
        "id": result.get("id"),
        "name": result.get("name"),
        "webUrl": result.get("webUrl"),
    }
