"""
Tietokantadumppien (pg_dump) tallennus.

Kaksi toteutusta, valitaan ympäristömuuttujista käynnistyksessä
(ks. `storage_from_env`):

- `BlobDumpStorage`: Azure Blob Storage, kun `JKR_DUMPS_STORAGE_ACCOUNT` on
  asetettu. Tunnistautuu AINA sovelluksen user-assigned managed identityllä
  (`JKR_DUMPS_IDENTITY_CLIENT_ID`), ei DefaultAzureCredentialilla eikä tilin
  avaimella: tilillä on shared key -pääsy pois päältä, ja datatason rooli on
  vain tällä identiteetillä ja vain kontin `JKR_DUMPS_CONTAINER` scopessa.
- `LocalDumpStorage`: paikallinen hakemisto (`JKR_DBDUMP_DIR`, oletus
  `/dbdumps`) docker-compose-kehitykseen.

pg_dump ja pg_restore tarvitsevat tiedoston levyllä, joten API ajaa ne
väliaikaistiedoston kautta (`JKR_DUMPS_TMP_DIR`, oletus järjestelmän temp).
Tämä moduuli vain siirtää tiedostoja tallennuksen ja levyn välillä.

Säilytys: `prune()` poistaa yli `retention_days` vanhat dumpit, mutta jättää
aina uusimman, vaikka sekin olisi vanha. Tätä ei voi tehdä blobin
lifecycle-politiikalla (se ei tiedä, mikä blob on uusin), joten API kutsuu
`prune()`:a jokaisen onnistuneen varmuuskopioinnin jälkeen.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import BinaryIO, List, Optional

logger = logging.getLogger("jkr-api.dumps")

DEFAULT_CONTAINER = "dbdumps"
DEFAULT_LOCAL_DIR = "/dbdumps"
DEFAULT_BLOB_RETENTION_DAYS = 30

# Kirjoitus kesken -tiedostot paikallisessa toteutuksessa. Piste alussa, jotta
# ne eivät kelpaa dumpin nimeksi eivätkä näy listauksessa.
_PARTIAL_SUFFIX = ".partial"

_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")


class DumpNotFound(Exception):
    """Pyydettyä dumppia ei ole."""


class DumpAlreadyExists(Exception):
    """Samanniminen dumppi on jo olemassa (ylikirjoitusta ei sallita)."""


@dataclass(frozen=True)
class DumpInfo:
    name: str
    size: int
    # Naiivi paikallinen aika, kuten API on aina palauttanut (frontend
    # tulkitsee sen paikalliseksi ajaksi).
    created_at: datetime


def is_valid_dump_name(name: str) -> bool:
    """Hyväksyy vain pelkän tiedostonimen.

    Ei hakemisto-osia (`/`, `\\`), ei `.`/`..`, ei pistealkuisia nimiä eikä
    ohjausmerkkejä. Blob-nimissä `/` loisi virtuaalihakemiston, joten sama
    sääntö koskee molempia toteutuksia.
    """
    if not name or len(name) > 255:
        return False
    if "/" in name or "\\" in name or name.startswith("."):
        return False
    if _CONTROL_CHARS_RE.search(name):
        return False
    return True


class DumpStorage(ABC):
    """Dumppien tallennuksen rajapinta. Kaikki metodit ovat asynkronisia;
    toteutukset ajavat blokkaavan I/O:n säikeessä."""

    #: Ihmisluettava kohde lokeihin ja tehtävän kuvaukseen.
    description: str
    #: Yli tämän vanhat dumpit poistetaan (uusin säilyy aina). 0 = ei poistoa.
    retention_days: int

    @abstractmethod
    async def list(self) -> List[DumpInfo]:
        """Dumpit uusin ensin."""

    @abstractmethod
    async def exists(self, name: str) -> bool:
        ...

    @abstractmethod
    async def delete(self, name: str) -> None:
        """Heittää DumpNotFound, jos dumppia ei ole."""

    @abstractmethod
    async def upload_file(self, name: str, source: Path) -> None:
        """Tallentaa levyllä olevan tiedoston. Heittää DumpAlreadyExists."""

    @abstractmethod
    async def upload_stream(self, name: str, stream: BinaryIO) -> int:
        """Tallentaa tiedosto-olion sisällön, palauttaa koon tavuina.
        Heittää DumpAlreadyExists."""

    @abstractmethod
    async def download_file(self, name: str, target: Path) -> None:
        """Kirjoittaa dumpin levylle. Heittää DumpNotFound."""

    async def prune(self) -> List[str]:
        """Poistaa yli `retention_days` vanhat dumpit; uusin säilyy aina.

        Palauttaa poistettujen nimet.
        """
        if self.retention_days <= 0:
            return []
        dumps = await self.list()
        if len(dumps) <= 1:
            return []
        cutoff = datetime.now() - timedelta(days=self.retention_days)
        removed = []
        # list() palauttaa uusimman ensin → dumps[0] säilyy aina.
        for dump in dumps[1:]:
            if dump.created_at >= cutoff:
                continue
            try:
                await self.delete(dump.name)
                removed.append(dump.name)
            except DumpNotFound:
                pass
        return removed


# ---------------------------------------------------------------------------
# Paikallinen hakemisto (docker-compose-kehitys)
# ---------------------------------------------------------------------------
class LocalDumpStorage(DumpStorage):
    def __init__(self, directory: Path, retention_days: int = 0):
        self.directory = Path(directory)
        self.retention_days = retention_days
        self.description = str(self.directory)

    def _path(self, name: str) -> Path:
        if not is_valid_dump_name(name):
            raise ValueError(f"Virheellinen tiedostonimi: {name!r}")
        directory = self.directory.resolve()
        path = (directory / name).resolve()
        if path.parent != directory:
            raise ValueError(f"Virheellinen tiedostonimi: {name!r}")
        return path

    def _list_sync(self) -> List[DumpInfo]:
        if not self.directory.exists():
            return []
        dumps = []
        for path in self.directory.iterdir():
            if not path.is_file() or not is_valid_dump_name(path.name):
                continue
            stat = path.stat()
            dumps.append(
                DumpInfo(
                    name=path.name,
                    size=stat.st_size,
                    created_at=datetime.fromtimestamp(stat.st_mtime),
                )
            )
        dumps.sort(key=lambda d: d.created_at, reverse=True)
        return dumps

    async def list(self) -> List[DumpInfo]:
        return await asyncio.to_thread(self._list_sync)

    async def exists(self, name: str) -> bool:
        return await asyncio.to_thread(self._path(name).is_file)

    def _delete_sync(self, name: str) -> None:
        try:
            self._path(name).unlink()
        except FileNotFoundError:
            raise DumpNotFound(name) from None

    async def delete(self, name: str) -> None:
        await asyncio.to_thread(self._delete_sync, name)

    def _write_sync(self, name: str, writer) -> int:
        """Kirjoittaa ensin piilotettuun .partial-tiedostoon ja siirtää sen
        lopulliseen nimeen vasta onnistuneen kirjoituksen jälkeen."""
        target = self._path(name)
        self.directory.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise DumpAlreadyExists(name)
        partial = target.with_name(f".{name}{_PARTIAL_SUFFIX}")
        try:
            with open(partial, "wb") as out:
                writer(out)
            if target.exists():
                raise DumpAlreadyExists(name)
            os.replace(partial, target)
        finally:
            partial.unlink(missing_ok=True)
        return target.stat().st_size

    async def upload_file(self, name: str, source: Path) -> None:
        def copy(out):
            with open(source, "rb") as src:
                shutil.copyfileobj(src, out, 1024 * 1024)

        await asyncio.to_thread(self._write_sync, name, copy)

    async def upload_stream(self, name: str, stream: BinaryIO) -> int:
        return await asyncio.to_thread(
            self._write_sync, name, lambda out: shutil.copyfileobj(stream, out, 1024 * 1024)
        )

    def _download_sync(self, name: str, target: Path) -> None:
        source = self._path(name)
        if not source.is_file():
            raise DumpNotFound(name)
        shutil.copyfile(source, target)

    async def download_file(self, name: str, target: Path) -> None:
        await asyncio.to_thread(self._download_sync, name, target)


# ---------------------------------------------------------------------------
# Azure Blob Storage (Container Apps -ympäristöt)
# ---------------------------------------------------------------------------
class BlobDumpStorage(DumpStorage):
    def __init__(self, container_client, retention_days: int = DEFAULT_BLOB_RETENTION_DAYS):
        # azure.storage.blob.ContainerClient (synkroninen; kutsut säikeessä).
        self.container = container_client
        self.retention_days = retention_days
        self.description = f"blob://{container_client.account_name}/{container_client.container_name}"

    @classmethod
    def from_managed_identity(
        cls,
        account_name: str,
        container_name: str,
        identity_client_id: str,
        retention_days: int = DEFAULT_BLOB_RETENTION_DAYS,
    ) -> "BlobDumpStorage":
        # Importit tässä, jotta paikallinen kehitys ja testit eivät tarvitse
        # Azure SDK:ta ladattuna.
        from azure.identity import ManagedIdentityCredential
        from azure.storage.blob import ContainerClient

        credential = ManagedIdentityCredential(client_id=identity_client_id)
        client = ContainerClient(
            account_url=f"https://{account_name}.blob.core.windows.net",
            container_name=container_name,
            credential=credential,
        )
        return cls(client, retention_days=retention_days)

    @staticmethod
    def _check(name: str) -> None:
        if not is_valid_dump_name(name):
            raise ValueError(f"Virheellinen tiedostonimi: {name!r}")

    def _list_sync(self) -> List[DumpInfo]:
        dumps = []
        for blob in self.container.list_blobs():
            # Vain kontin juuren nimet, joita API itse voi käsitellä.
            if not is_valid_dump_name(blob.name):
                continue
            dumps.append(
                DumpInfo(
                    name=blob.name,
                    size=blob.size,
                    created_at=_to_naive_local(blob.last_modified),
                )
            )
        dumps.sort(key=lambda d: d.created_at, reverse=True)
        return dumps

    async def list(self) -> List[DumpInfo]:
        return await asyncio.to_thread(self._list_sync)

    async def exists(self, name: str) -> bool:
        self._check(name)
        return await asyncio.to_thread(self.container.get_blob_client(name).exists)

    def _delete_sync(self, name: str) -> None:
        from azure.core.exceptions import ResourceNotFoundError

        self._check(name)
        try:
            self.container.delete_blob(name, delete_snapshots="include")
        except ResourceNotFoundError:
            raise DumpNotFound(name) from None

    async def delete(self, name: str) -> None:
        await asyncio.to_thread(self._delete_sync, name)

    def _upload_sync(self, name: str, data: BinaryIO) -> int:
        from azure.core.exceptions import ResourceExistsError

        self._check(name)
        try:
            client = self.container.upload_blob(name, data, overwrite=False)
        except ResourceExistsError:
            raise DumpAlreadyExists(name) from None
        return client.get_blob_properties().size

    async def upload_file(self, name: str, source: Path) -> None:
        def upload():
            with open(source, "rb") as src:
                self._upload_sync(name, src)

        await asyncio.to_thread(upload)

    async def upload_stream(self, name: str, stream: BinaryIO) -> int:
        return await asyncio.to_thread(self._upload_sync, name, stream)

    def _download_sync(self, name: str, target: Path) -> None:
        from azure.core.exceptions import ResourceNotFoundError

        self._check(name)
        try:
            downloader = self.container.download_blob(name)
            with open(target, "wb") as out:
                downloader.readinto(out)
        except ResourceNotFoundError:
            raise DumpNotFound(name) from None

    async def download_file(self, name: str, target: Path) -> None:
        await asyncio.to_thread(self._download_sync, name, target)


def _to_naive_local(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone().replace(tzinfo=None)


def _retention_from_env(default: int) -> int:
    raw = os.environ.get("JKR_DUMPS_RETENTION_DAYS", "").strip()
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        raise RuntimeError(f"JKR_DUMPS_RETENTION_DAYS ei ole kokonaisluku: {raw!r}") from None


def storage_from_env() -> DumpStorage:
    """Valitsee toteutuksen ympäristömuuttujista.

    Jos `JKR_DUMPS_STORAGE_ACCOUNT` on asetettu, `JKR_DUMPS_IDENTITY_CLIENT_ID`
    on pakollinen: puuttuva identiteetti kaataa käynnistyksen sen sijaan, että
    sovellus palaisi hiljaa paikalliseen (ephemeral) hakemistoon.
    """
    account = os.environ.get("JKR_DUMPS_STORAGE_ACCOUNT", "").strip()
    if account:
        client_id = os.environ.get("JKR_DUMPS_IDENTITY_CLIENT_ID", "").strip()
        if not client_id:
            raise RuntimeError(
                "JKR_DUMPS_STORAGE_ACCOUNT on asetettu, mutta JKR_DUMPS_IDENTITY_CLIENT_ID puuttuu."
            )
        container = os.environ.get("JKR_DUMPS_CONTAINER", "").strip() or DEFAULT_CONTAINER
        return BlobDumpStorage.from_managed_identity(
            account,
            container,
            client_id,
            retention_days=_retention_from_env(DEFAULT_BLOB_RETENTION_DAYS),
        )
    return LocalDumpStorage(
        Path(os.environ.get("JKR_DBDUMP_DIR", DEFAULT_LOCAL_DIR)),
        retention_days=_retention_from_env(0),
    )


def temp_dir() -> Optional[str]:
    """Väliaikaistiedostojen hakemisto pg_dumpille ja pg_restorelle."""
    return os.environ.get("JKR_DUMPS_TMP_DIR") or None
