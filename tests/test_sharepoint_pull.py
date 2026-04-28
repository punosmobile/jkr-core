import asyncio
from types import SimpleNamespace

from jkrimporter.api import api
from jkrimporter.api.util import FileInfo


def test_pull_sharepoint_paths_uses_bounded_concurrency(monkeypatch, tmp_path):
    active_downloads = 0
    peak_downloads = 0
    verified_paths = []

    async def fake_download_file_to_disk(path, target_dir, user_name="", user_email=""):
        nonlocal active_downloads, peak_downloads
        active_downloads += 1
        peak_downloads = max(peak_downloads, active_downloads)
        await asyncio.sleep(0.02)
        active_downloads -= 1
        filename = path.split("/")[-1]
        if filename == "broken.xlsx":
            raise RuntimeError("download failed")
        return {
            "filename": filename,
            "target_path": str(tmp_path / filename),
            "size": 123,
            "sharepoint_path": path,
        }

    def fake_verify_contents(raw):
        verified_paths.append(raw["sharepoint_path"])
        return FileInfo(
            filename=raw["filename"],
            target_path=raw["target_path"],
            size=raw["size"],
            sharepoint_path=raw["sharepoint_path"],
            runnable=True,
        )

    monkeypatch.setattr(api.sp, "download_file_to_disk", fake_download_file_to_disk)
    monkeypatch.setattr(api.utilities, "verify_contents", fake_verify_contents)
    monkeypatch.setattr(api, "_sharepoint_pull_concurrency", lambda: 2)

    result = asyncio.run(
        api._pull_sharepoint_paths(
            [
                "Shared Documents/JKR-input/first.xlsx",
                "Shared Documents/JKR-input/broken.xlsx",
                "Shared Documents/JKR-input/third.xlsx",
            ],
            str(tmp_path),
            SimpleNamespace(name="Tester", email="tester@example.com"),
        )
    )

    assert peak_downloads == 2
    assert verified_paths == [
        "Shared Documents/JKR-input/first.xlsx",
        "Shared Documents/JKR-input/third.xlsx",
    ]
    assert [item.filename for item in result["downloaded"]] == ["first.xlsx", "third.xlsx"]
    assert result["errors"] == [
        {
            "path": "Shared Documents/JKR-input/broken.xlsx",
            "error": "download failed",
        }
    ]
    assert result["timing"]["concurrency"] == 2
