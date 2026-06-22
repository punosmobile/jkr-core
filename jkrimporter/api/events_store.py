"""
Järjestelmätapahtumien pysyvä tallennus (LAH-623).

Dashboardin "viimeisimmät järjestelmätapahtumat" pidetään ajon aikana
muistissa (api._tasks), mutta ne katoavat kontin uudelleenkäynnistyksessä.
Tämä moduuli tallentaa tapahtumat SQLite-kantaan, joka sijaitsee
varmuuskopioiden kanssa samalla levyllä mutta omassa alikansiossaan, jolloin
se ei näy varmuuskopiolistauksessa (api.list_db_dumps iteroi vain juuren
tiedostot, ei alikansioita).

Käyttö:
    events_store.ensure_schema()          # luo kansio + kanta jos puuttuu
    events_store.upsert(task)             # tallenna/päivitä tapahtuma
    events_store.recent(limit=50)         # viimeisimmät tapahtumat (dict-listana)
    events_store.prune(keep=2000)         # siivoa vanhat pois
"""

import json
import logging
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

logger = logging.getLogger("jkr-events")

# Sama salasanasensurointi kuin tuontilokissa (api._tuontiloki_alku).
_PASSWORD_RE = re.compile(r"password=\S+")

# Kannan sijainti: oletuksena varmuuskopiokansion (JKR_DBDUMP_DIR) alikansio.
# Alikansio on tarkoituksella – api.list_db_dumps ohittaa alikansiot, joten
# tapahtumakanta ei valu käyttöliittymän varmuuskopiolistaan.
_DEFAULT_DB_PATH = Path(os.environ.get("JKR_DBDUMP_DIR", "/dbdumps")) / "system" / "jarjestelmatapahtumat.db"


def db_path() -> Path:
    """Tapahtumakannan polku (ylikirjoitettavissa JKR_EVENTS_DB-muuttujalla)."""
    return Path(os.environ.get("JKR_EVENTS_DB", str(_DEFAULT_DB_PATH)))


_SCHEMA = """
CREATE TABLE IF NOT EXISTS jarjestelmatapahtuma (
    id               TEXT PRIMARY KEY,
    task_type        TEXT NOT NULL,
    status           TEXT NOT NULL,
    command          TEXT,
    runner           TEXT,
    description      TEXT,
    started_at       TEXT,
    finished_at      TEXT,
    duration_seconds REAL,
    exit_code        INTEGER,
    output           TEXT,
    error            TEXT,
    result_file      TEXT,
    occurred_at      TEXT
);
CREATE INDEX IF NOT EXISTS ix_tapahtuma_occurred
    ON jarjestelmatapahtuma(occurred_at DESC);
"""


def _connect() -> sqlite3.Connection:
    """Avaa yhteyden tapahtumakantaan. Kansio ja tiedosto luodaan tarvittaessa."""
    path = db_path()
    # Jos kansio puuttuu, se luodaan. Jos kanta puuttuu, sqlite3.connect luo sen.
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=30.0)
    conn.row_factory = sqlite3.Row
    # WAL kestää paremmin samanaikaiset luvut kirjoituksen rinnalla.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def ensure_schema() -> None:
    """Varmistaa että kansio, kanta ja taulu ovat olemassa (luo puuttuvat)."""
    try:
        with _connect() as conn:
            conn.executescript(_SCHEMA)
        logger.info("Järjestelmätapahtumakanta valmiina: %s", db_path())
    except Exception:
        logger.exception("Tapahtumakannan alustus epäonnistui (%s)", db_path())


def _iso(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _status_value(task: Any) -> str:
    status = getattr(task, "status", None)
    return getattr(status, "value", str(status)) if status is not None else "unknown"


def upsert(task: Any) -> None:
    """Tallentaa tai päivittää tapahtuman id:n perusteella. Ei koskaan nosta."""
    try:
        started = _iso(getattr(task, "started_at", None))
        finished = _iso(getattr(task, "finished_at", None))
        result_file = getattr(task, "result_file", None)
        command = getattr(task, "command", None)
        row = {
            "id": str(getattr(task, "id", "")),
            "task_type": getattr(task, "taskType", "unknown") or "unknown",
            "status": _status_value(task),
            "command": _PASSWORD_RE.sub("password=***", command) if command else command,
            "runner": getattr(task, "runner", None),
            "description": getattr(task, "description", None),
            "started_at": started,
            "finished_at": finished,
            "duration_seconds": getattr(task, "duration_seconds", None),
            "exit_code": getattr(task, "exit_code", None),
            "output": getattr(task, "output", "") or "",
            "error": getattr(task, "error", "") or "",
            "result_file": json.dumps(result_file, ensure_ascii=False) if result_file else None,
            "occurred_at": finished or started,
        }
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO jarjestelmatapahtuma (
                    id, task_type, status, command, runner, description,
                    started_at, finished_at, duration_seconds, exit_code,
                    output, error, result_file, occurred_at
                ) VALUES (
                    :id, :task_type, :status, :command, :runner, :description,
                    :started_at, :finished_at, :duration_seconds, :exit_code,
                    :output, :error, :result_file, :occurred_at
                )
                ON CONFLICT(id) DO UPDATE SET
                    task_type=excluded.task_type,
                    status=excluded.status,
                    command=excluded.command,
                    runner=excluded.runner,
                    description=excluded.description,
                    started_at=excluded.started_at,
                    finished_at=excluded.finished_at,
                    duration_seconds=excluded.duration_seconds,
                    exit_code=excluded.exit_code,
                    output=excluded.output,
                    error=excluded.error,
                    result_file=excluded.result_file,
                    occurred_at=excluded.occurred_at
                """,
                row,
            )
    except Exception:
        logger.exception("Tapahtuman tallennus epäonnistui (id=%s)", getattr(task, "id", "?"))


def recent(limit: int = 50) -> List[dict]:
    """Palauttaa viimeisimmät tapahtumat dict-listana (TaskInfo-kentännimillä).

    Lajittelu occurred_at DESC; NULL-arvot (esim. ajamattomat) jäävät loppuun.
    """
    try:
        with _connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM jarjestelmatapahtuma
                ORDER BY occurred_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    except Exception:
        logger.exception("Tapahtumien luku epäonnistui")
        return []

    result: List[dict] = []
    for r in rows:
        result.append(
            {
                "id": r["id"],
                "taskType": r["task_type"],
                "status": r["status"],
                "command": r["command"] or "",
                "runner": r["runner"],
                "description": r["description"] or "",
                "started_at": r["started_at"],
                "finished_at": r["finished_at"],
                "duration_seconds": r["duration_seconds"],
                "exit_code": r["exit_code"],
                "output": r["output"] or "",
                "error": r["error"] or "",
                "result_file": json.loads(r["result_file"]) if r["result_file"] else None,
            }
        )
    return result


def prune(keep: int = 2000) -> None:
    """Säilyttää vain keep viimeisintä tapahtumaa, poistaa loput."""
    try:
        with _connect() as conn:
            conn.execute(
                """
                DELETE FROM jarjestelmatapahtuma
                WHERE id NOT IN (
                    SELECT id FROM jarjestelmatapahtuma
                    ORDER BY occurred_at DESC
                    LIMIT ?
                )
                """,
                (keep,),
            )
    except Exception:
        logger.exception("Tapahtumien siivous epäonnistui")
