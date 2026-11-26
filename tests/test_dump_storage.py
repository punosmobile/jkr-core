"""Testit tietokantadumppien tallennukselle (paikallinen hakemisto ja Azure Blob).

Eivät tarvitse tietokantaa eivätkä Azurea. Endpointtien ja taustatehtävien
testit ovat tiedostossa test_dump_endpoints.py."""

import asyncio
import io
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from jkrimporter.api import dump_storage as ds


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Tiedostonimen validointi
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "name",
    ["jatehuolto_dump_20260615_143205.backup", "oma varmuuskopio (1).backup", "a"],
)
def test_valid_dump_names(name):
    assert ds.is_valid_dump_name(name)


@pytest.mark.parametrize(
    "name",
    ["", ".", "..", "../x", "a/b", "a\\b", ".hidden", ".x.backup.partial", "a\nb", "x" * 256],
)
def test_invalid_dump_names(name):
    assert not ds.is_valid_dump_name(name)


# ---------------------------------------------------------------------------
# LocalDumpStorage
# ---------------------------------------------------------------------------
def _set_mtime(path: Path, when: datetime):
    ts = when.timestamp()
    os.utime(path, (ts, ts))


def test_local_upload_list_download_delete(tmp_path):
    storage = ds.LocalDumpStorage(tmp_path / "dumps")
    src = tmp_path / "src.backup"
    src.write_bytes(b"dumpdata")

    run(storage.upload_file("a.backup", src))
    assert run(storage.exists("a.backup"))

    dumps = run(storage.list())
    assert [(d.name, d.size) for d in dumps] == [("a.backup", 8)]

    target = tmp_path / "restored"
    run(storage.download_file("a.backup", target))
    assert target.read_bytes() == b"dumpdata"

    run(storage.delete("a.backup"))
    assert not run(storage.exists("a.backup"))
    with pytest.raises(ds.DumpNotFound):
        run(storage.delete("a.backup"))
    with pytest.raises(ds.DumpNotFound):
        run(storage.download_file("a.backup", target))


def test_local_list_missing_dir_is_empty(tmp_path):
    assert run(ds.LocalDumpStorage(tmp_path / "nope").list()) == []


def test_local_does_not_overwrite(tmp_path):
    storage = ds.LocalDumpStorage(tmp_path)
    assert run(storage.upload_stream("a.backup", io.BytesIO(b"first"))) == 5
    with pytest.raises(ds.DumpAlreadyExists):
        run(storage.upload_stream("a.backup", io.BytesIO(b"second")))
    assert (tmp_path / "a.backup").read_bytes() == b"first"
    # Keskeneräisiä tiedostoja ei jää.
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a.backup"]


def test_local_failed_write_leaves_nothing(tmp_path):
    storage = ds.LocalDumpStorage(tmp_path)

    class Broken(io.RawIOBase):
        def readinto(self, b):
            raise OSError("katkesi")

    with pytest.raises(OSError):
        run(storage.upload_stream("a.backup", Broken()))
    assert list(tmp_path.iterdir()) == []


def test_local_list_hides_partials_and_dirs(tmp_path):
    (tmp_path / "ok.backup").write_bytes(b"x")
    (tmp_path / ".ok2.backup.partial").write_bytes(b"x")
    (tmp_path / "system").mkdir()
    names = [d.name for d in run(ds.LocalDumpStorage(tmp_path).list())]
    assert names == ["ok.backup"]


def test_local_rejects_traversal(tmp_path):
    storage = ds.LocalDumpStorage(tmp_path / "dumps")
    with pytest.raises(ValueError):
        run(storage.exists("../secret"))


def test_prune_keeps_newest_and_recent(tmp_path):
    storage = ds.LocalDumpStorage(tmp_path, retention_days=30)
    now = datetime.now()
    for name, age in [("new.backup", 1), ("mid.backup", 29), ("old.backup", 31), ("older.backup", 90)]:
        (tmp_path / name).write_bytes(b"x")
        _set_mtime(tmp_path / name, now - timedelta(days=age))

    removed = run(storage.prune())

    assert sorted(removed) == ["old.backup", "older.backup"]
    assert sorted(p.name for p in tmp_path.iterdir()) == ["mid.backup", "new.backup"]


def test_prune_keeps_latest_even_if_old(tmp_path):
    storage = ds.LocalDumpStorage(tmp_path, retention_days=30)
    now = datetime.now()
    for name, age in [("a.backup", 40), ("b.backup", 60)]:
        (tmp_path / name).write_bytes(b"x")
        _set_mtime(tmp_path / name, now - timedelta(days=age))

    assert run(storage.prune()) == ["b.backup"]
    assert [p.name for p in tmp_path.iterdir()] == ["a.backup"]


def test_prune_disabled(tmp_path):
    storage = ds.LocalDumpStorage(tmp_path, retention_days=0)
    (tmp_path / "a.backup").write_bytes(b"x")
    (tmp_path / "b.backup").write_bytes(b"x")
    _set_mtime(tmp_path / "b.backup", datetime.now() - timedelta(days=400))
    assert run(storage.prune()) == []
    assert len(list(tmp_path.iterdir())) == 2


# ---------------------------------------------------------------------------
# BlobDumpStorage (ContainerClient korvattu muistissa toimivalla)
# ---------------------------------------------------------------------------
class FakeContainer:
    account_name = "stdumps"
    container_name = "dbdumps"

    def __init__(self):
        self.blobs = {}  # name -> (bytes, last_modified)

    def list_blobs(self):
        for name, (data, modified) in self.blobs.items():
            yield SimpleNamespace(name=name, size=len(data), last_modified=modified)

    def get_blob_client(self, name):
        return SimpleNamespace(exists=lambda: name in self.blobs)

    def delete_blob(self, name, delete_snapshots=None):
        assert delete_snapshots == "include"
        if name not in self.blobs:
            raise ResourceNotFoundError("ei ole")
        del self.blobs[name]

    def upload_blob(self, name, data, overwrite):
        assert overwrite is False
        if name in self.blobs:
            raise ResourceExistsError("on jo")
        content = data.read()
        self.blobs[name] = (content, datetime.now(timezone.utc))
        return SimpleNamespace(get_blob_properties=lambda: SimpleNamespace(size=len(content)))

    def download_blob(self, name):
        if name not in self.blobs:
            raise ResourceNotFoundError("ei ole")
        content = self.blobs[name][0]
        return SimpleNamespace(readinto=lambda f: f.write(content))


def test_blob_roundtrip(tmp_path):
    container = FakeContainer()
    storage = ds.BlobDumpStorage(container)
    assert storage.description == "blob://stdumps/dbdumps"
    assert storage.retention_days == 30

    src = tmp_path / "src"
    src.write_bytes(b"abc")
    run(storage.upload_file("a.backup", src))
    assert run(storage.upload_stream("b.backup", io.BytesIO(b"hello"))) == 5
    assert run(storage.exists("a.backup"))

    target = tmp_path / "out"
    run(storage.download_file("b.backup", target))
    assert target.read_bytes() == b"hello"

    run(storage.delete("a.backup"))
    assert not run(storage.exists("a.backup"))


def test_blob_errors_are_translated(tmp_path):
    storage = ds.BlobDumpStorage(FakeContainer())
    run(storage.upload_stream("a.backup", io.BytesIO(b"x")))
    with pytest.raises(ds.DumpAlreadyExists):
        run(storage.upload_stream("a.backup", io.BytesIO(b"y")))
    with pytest.raises(ds.DumpNotFound):
        run(storage.delete("missing.backup"))
    with pytest.raises(ds.DumpNotFound):
        run(storage.download_file("missing.backup", tmp_path / "x"))
    with pytest.raises(ValueError):
        run(storage.upload_stream("dir/a.backup", io.BytesIO(b"y")))


def test_blob_list_filters_and_converts_time():
    container = FakeContainer()
    utc = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
    container.blobs = {
        "old.backup": (b"1", utc - timedelta(days=1)),
        "new.backup": (b"22", utc),
        "sub/x.backup": (b"333", utc),
    }
    dumps = run(ds.BlobDumpStorage(container).list())
    assert [(d.name, d.size) for d in dumps] == [("new.backup", 2), ("old.backup", 1)]
    # Naiivi paikallinen aika, kuten paikallisessa toteutuksessa.
    assert dumps[0].created_at.tzinfo is None
    assert dumps[0].created_at == utc.astimezone().replace(tzinfo=None)


# ---------------------------------------------------------------------------
# storage_from_env
# ---------------------------------------------------------------------------
_ENV = (
    "JKR_DUMPS_STORAGE_ACCOUNT",
    "JKR_DUMPS_CONTAINER",
    "JKR_DUMPS_IDENTITY_CLIENT_ID",
    "JKR_DUMPS_RETENTION_DAYS",
    "JKR_DBDUMP_DIR",
)


@pytest.fixture
def clean_env(monkeypatch):
    for key in _ENV:
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


def test_env_local_default(clean_env, tmp_path):
    clean_env.setenv("JKR_DBDUMP_DIR", str(tmp_path))
    storage = ds.storage_from_env()
    assert isinstance(storage, ds.LocalDumpStorage)
    assert storage.directory == tmp_path
    assert storage.retention_days == 0


def test_env_blob_requires_identity(clean_env):
    clean_env.setenv("JKR_DUMPS_STORAGE_ACCOUNT", "stdumps")
    with pytest.raises(RuntimeError, match="JKR_DUMPS_IDENTITY_CLIENT_ID"):
        ds.storage_from_env()


def test_env_blob_uses_managed_identity(clean_env):
    clean_env.setenv("JKR_DUMPS_STORAGE_ACCOUNT", "stdumps")
    clean_env.setenv("JKR_DUMPS_IDENTITY_CLIENT_ID", "11111111-2222-3333-4444-555555555555")
    clean_env.setenv("JKR_DUMPS_RETENTION_DAYS", "14")
    storage = ds.storage_from_env()
    assert isinstance(storage, ds.BlobDumpStorage)
    assert storage.description == "blob://stdumps/dbdumps"
    assert storage.retention_days == 14
    credential = storage.container.credential
    assert type(credential).__name__ == "ManagedIdentityCredential"
