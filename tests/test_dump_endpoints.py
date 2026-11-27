"""Testit /db/dump*-endpointeille ja dump/restore-taustatehtäville.

api-moduulin import vaatii testikannan (kuten muutkin api-testit), mutta
dumppien tallennus ajetaan paikallisena hakemistona tai muistissa toimivana
blob-konttina, eikä pg_dump/pg_restorea ajeta.
"""

import asyncio
import io
import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks, HTTPException, UploadFile

from jkrimporter.api import api
from jkrimporter.api import dump_storage as ds
from test_dump_storage import FakeContainer  # tests/ on sys.pathissa (rootdir-import)


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Endpointit
# ---------------------------------------------------------------------------
# Endpoint-funktioita kutsutaan suoraan: Starlette 0.27:n TestClient ei toimi
# httpx >= 0.28:n kanssa. Autentikointi on Depends-parametri, joten se ohitetaan
# antamalla käyttäjä suoraan.
USER = SimpleNamespace(name="testi")


@pytest.fixture
def storage(monkeypatch, tmp_path):
    storage = ds.LocalDumpStorage(tmp_path / "dumps")
    monkeypatch.setattr(api, "DUMP_STORAGE", storage)
    monkeypatch.setattr(api, "_db_operations", {})
    return storage


def _upload(name, data):
    return run(api.upload_db_dump(file=UploadFile(file=io.BytesIO(data), filename=name), user=USER))


def _status(coro):
    with pytest.raises(HTTPException) as exc:
        run(coro)
    return exc.value.status_code


def test_upload_list_delete_endpoints(storage):
    assert _upload("a.backup", b"abc")["file_size"] == 3

    with pytest.raises(HTTPException) as exc:
        _upload("a.backup", b"zzz")
    assert exc.value.status_code == 409
    assert (storage.directory / "a.backup").read_bytes() == b"abc"

    backups = run(api.list_db_dumps(user=USER))
    assert [(b.filename, b.size) for b in backups] == [("a.backup", 3)]

    run(api.delete_db_dump("a.backup", user=USER))
    assert _status(api.delete_db_dump("a.backup", user=USER)) == 404
    assert _status(api.delete_db_dump(".hidden", user=USER)) == 400


def test_upload_rejects_bad_name(storage):
    for name in (".x", "../x", "a/b"):
        with pytest.raises(HTTPException) as exc:
            _upload(name, b"abc")
        assert exc.value.status_code == 400


def test_restore_missing_or_bad_name(storage):
    bg = BackgroundTasks()
    assert _status(api.db_restore(api.RestoreRequest(filename="nope.backup"), bg, user=USER)) == 404
    assert _status(api.db_restore(api.RestoreRequest(filename="../x"), bg, user=USER)) == 400
    assert bg.tasks == []


def test_delete_refused_while_dump_in_use(storage, monkeypatch):
    _upload("a.backup", b"abc")
    busy = SimpleNamespace(id="t1")
    monkeypatch.setattr(api, "_active_db_task", lambda: busy)
    api._db_operations["t1"] = {"kind": "restore", "filename": "a.backup"}
    assert _status(api.delete_db_dump("a.backup", user=USER)) == 409
    assert (storage.directory / "a.backup").exists()


# ---------------------------------------------------------------------------
# Taustatehtävät: dump → tallennus, tallennus → restore
# ---------------------------------------------------------------------------
@pytest.fixture
def quiet_tasks(monkeypatch, tmp_path):
    """Ohittaa _run_taskin sivuvaikutukset (tapahtumakanta, SharePoint-loki)."""
    monkeypatch.setattr(api, "_persist_event", lambda task: None)
    monkeypatch.setattr(api, "__log_path__", str(tmp_path / "no-log"))
    monkeypatch.setattr(api, "_db_env", lambda: dict(os.environ))


def _task(cmd):
    return api._create_task(cmd, "testi", username="testi", task_type=api.TaskType.maintenance)


def test_dump_task_uploads_and_cleans_up(quiet_tasks, monkeypatch, tmp_path):
    storage = ds.BlobDumpStorage(FakeContainer())
    monkeypatch.setattr(api, "DUMP_STORAGE", storage)
    tmp = tmp_path / "dump.tmp"
    cmd = f"printf dumpdata > {tmp}"
    task = _task(cmd)

    run(api._run_dump_task(task.id, cmd, "x.backup", tmp))

    assert task.status == api.TaskStatus.completed, task.error
    assert storage.container.blobs["x.backup"][0] == b"dumpdata"
    assert not tmp.exists()
    assert "Varmuuskopio tallennettu." in task.output


def test_dump_task_fails_if_upload_fails(quiet_tasks, monkeypatch, tmp_path):
    container = FakeContainer()
    container.blobs["x.backup"] = (b"old", datetime.now(timezone.utc))
    monkeypatch.setattr(api, "DUMP_STORAGE", ds.BlobDumpStorage(container))
    tmp = tmp_path / "dump.tmp"
    cmd = f"printf dumpdata > {tmp}"
    task = _task(cmd)

    run(api._run_dump_task(task.id, cmd, "x.backup", tmp))

    assert task.status == api.TaskStatus.failed
    assert container.blobs["x.backup"][0] == b"old"
    assert "on jo olemassa" in task.error
    assert not tmp.exists()


def test_dump_task_failed_pg_dump_uploads_nothing(quiet_tasks, monkeypatch, tmp_path):
    storage = ds.BlobDumpStorage(FakeContainer())
    monkeypatch.setattr(api, "DUMP_STORAGE", storage)
    tmp = tmp_path / "dump.tmp"
    tmp.write_bytes(b"")
    cmd = "exit 3"
    task = _task(cmd)

    run(api._run_dump_task(task.id, cmd, "x.backup", tmp))

    assert task.status == api.TaskStatus.failed
    assert storage.container.blobs == {}
    assert not tmp.exists()


def test_dump_task_prunes_old_dumps(quiet_tasks, monkeypatch, tmp_path):
    container = FakeContainer()
    container.blobs["ancient.backup"] = (b"1", datetime.now(timezone.utc) - timedelta(days=45))
    monkeypatch.setattr(api, "DUMP_STORAGE", ds.BlobDumpStorage(container, retention_days=30))
    tmp = tmp_path / "dump.tmp"
    cmd = f"printf new > {tmp}"
    task = _task(cmd)

    run(api._run_dump_task(task.id, cmd, "x.backup", tmp))

    assert task.status == api.TaskStatus.completed, task.error
    assert set(container.blobs) == {"x.backup"}


def test_restore_task_downloads_then_cleans_up(quiet_tasks, monkeypatch, tmp_path):
    container = FakeContainer()
    container.blobs["x.backup"] = (b"restoreme", datetime.now(timezone.utc))
    monkeypatch.setattr(api, "DUMP_STORAGE", ds.BlobDumpStorage(container))
    tmp = tmp_path / "restore.tmp"
    seen = tmp_path / "seen"
    cmd = f"cp {tmp} {seen}"
    task = _task(cmd)

    run(api._run_restore_task(task.id, cmd, "x.backup", tmp))

    assert task.status == api.TaskStatus.completed, task.error
    assert seen.read_bytes() == b"restoreme"
    assert not tmp.exists()


def test_restore_task_fails_without_running_if_download_fails(quiet_tasks, monkeypatch, tmp_path):
    monkeypatch.setattr(api, "DUMP_STORAGE", ds.BlobDumpStorage(FakeContainer()))
    tmp = tmp_path / "restore.tmp"
    tmp.write_bytes(b"")
    marker = tmp_path / "ran"
    cmd = f"touch {marker}"
    task = _task(cmd)

    run(api._run_restore_task(task.id, cmd, "missing.backup", tmp))

    assert task.status == api.TaskStatus.failed
    assert not marker.exists()
    assert "ei löydy" in task.error
    assert not tmp.exists()
