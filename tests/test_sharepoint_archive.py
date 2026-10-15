"""Testit käsiteltyjen tiedostojen arkistoinnille ("viedyt"), LAH-625."""

import asyncio

from jkrimporter.api import api


def _clear_registry():
    api._sharepoint_sources.clear()


def test_register_and_pop_sp_source_by_full_path_and_basename():
    _clear_registry()
    api._register_sp_source(
        "/data/input/kuljetus.xlsx",
        "Shared Documents/JKR-input/kuljetus.xlsx",
    )

    # Löytyy sekä koko paikallisella polulla että pelkällä tiedostonimellä.
    assert (
        api._pop_sp_source("kuljetus.xlsx")
        == "Shared Documents/JKR-input/kuljetus.xlsx"
    )
    # Pop poistaa kytkennän → toinen haku palauttaa None.
    assert api._pop_sp_source("/data/input/kuljetus.xlsx") is None


def test_register_ignores_empty_values():
    _clear_registry()
    api._register_sp_source("", "Shared Documents/JKR-input/x.xlsx")
    api._register_sp_source("/data/input/x.xlsx", "")
    assert api._pop_sp_source("/data/input/x.xlsx") is None


def test_archive_moves_only_registered_sources(monkeypatch):
    _clear_registry()
    api._register_sp_source(
        "/data/input/pulled.xlsx",
        "Shared Documents/JKR-input/pulled.xlsx",
    )

    archived = []

    async def fake_archive_file(source_path, user_name="", user_email=""):
        archived.append(source_path)
        return {"id": "1", "name": "pulled.xlsx"}

    monkeypatch.setattr(api.sp, "SHAREPOINT_ARCHIVE_AFTER_IMPORT", True)
    monkeypatch.setattr(api.sp, "SHAREPOINT_SITE_ID", "site")
    monkeypatch.setattr(api.sp, "has_credentials", lambda: True)
    monkeypatch.setattr(api.sp, "archive_file", fake_archive_file)

    asyncio.run(
        api._archive_processed_sources(
            ["/data/input/pulled.xlsx", "/data/input/manually_uploaded.xlsx"],
            "Tester",
        )
    )

    # Vain SharePointista pullattu tiedosto arkistoidaan; käsin ladattu ohitetaan.
    assert archived == ["Shared Documents/JKR-input/pulled.xlsx"]


def test_archive_respects_disable_flag(monkeypatch):
    _clear_registry()
    api._register_sp_source(
        "/data/input/pulled.xlsx",
        "Shared Documents/JKR-input/pulled.xlsx",
    )

    archived = []

    async def fake_archive_file(source_path, user_name="", user_email=""):
        archived.append(source_path)

    monkeypatch.setattr(api.sp, "SHAREPOINT_ARCHIVE_AFTER_IMPORT", False)
    monkeypatch.setattr(api.sp, "archive_file", fake_archive_file)

    asyncio.run(api._archive_processed_sources(["/data/input/pulled.xlsx"], "Tester"))

    assert archived == []
