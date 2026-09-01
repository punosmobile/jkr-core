"""
Järjestelmätapahtumien pysyvä tallennus (LAH-623).

Dashboardin "viimeisimmät järjestelmätapahtumat" pidetään ajon aikana
muistissa (api._tasks), mutta ne katoavat kontin uudelleenkäynnistyksessä.
Tämä moduuli tallentaa tapahtumat pysyvästi.

MIKSI OMA POSTGRES-KANTA (muutettu 31.8.2026)
---------------------------------------------
Aiemmin tapahtumat tallennettiin SQLite-kantaan `/dbdumps`-hakemistoon.
Se ei toiminut kertaakaan: `/dbdumps` on Azure Files (SMB) -verkkolevy, eikä
SMB tue luotettavasti SQLiten vaatimia tiedostotason lukkoja. Skeeman luonti
kaatui joka käynnistyksessä virheeseen

    sqlite3.OperationalError: database is locked

ja kaikki luku- ja kirjoitusyritykset sen jälkeen virheeseen
"no such table: jarjestelmatapahtuma". Kanta jäi 0-tavuiseksi tiedostoksi.
Todennettu 31.8.2026: tiedoston poisto ja kontin uudelleenkäynnistys toistivat
saman virheen, joten kyse ei ollut jumiin jääneestä tiedostosta vaan SMB:stä.
Container Apps tukee vain Azure Files- ja ephemeral-tallennusta, joten SQLitelle
ei ole tässä ajoympäristössä kelvollista pysyvää sijaintia lainkaan.

Tapahtumat ovat nyt OMASSA Postgres-kannassaan (oletus `systemevents`), samalla
palvelininstanssilla kuin `jatehuolto` mutta eri kantana. Tämä on tarkoituksellista
eikä vain siisteyssyy:

    Varmuuskopion palautus ja kannan nollaus OVAT itsessään järjestelmätapahtumia.
    Jos tämä taulu olisi `jatehuolto`-kannassa, palautus pyyhkisi juuri sen
    merkinnän joka kertoo palautuksen tapahtuneen — loki ei voi elää kannassa
    jonka elinkaarta se seuraa.

Erillinen kanta ratkaisee samalla sen, mitä SQLite ei olisi tässä ympäristössä
koskaan kestänyt: usean replikan yhtäaikaisen kirjoituksen ja revisiovaihdon
päällekkäisyyden.

EDELLYTYS: kannan `systemevents` on oltava olemassa ja JKR_USER-käyttäjällä on
oltava siihen oikeudet. Luonti on infra-askel (ks. create-systemevents-db.ps1);
tämä moduuli luo vain taulun ja indeksin.

Käyttö (rajapinta ennallaan):
    events_store.ensure_schema()          # luo taulu jos puuttuu
    events_store.upsert(task)             # tallenna/päivitä tapahtuma
    events_store.recent(limit=50)         # viimeisimmät tapahtumat (dict-listana)
    events_store.prune(keep=2000)         # siivoa vanhat pois
"""

import json
import logging
import os
import re
from contextlib import contextmanager
from datetime import datetime
from typing import Any, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger("jkr-events")

# Sama salasanasensurointi kuin tuontilokissa (api._tuontiloki_alku).
_PASSWORD_RE = re.compile(r"password=\S+")


def _conn_params() -> dict:
    """Yhteysasetukset: sama palvelin ja tunnus kuin jatehuolto-kannalla, ERI kanta.

    Kannan nimi on ylikirjoitettavissa JKR_EVENTS_DB-muuttujalla. HUOM: aiemmin
    sama muuttuja tarkoitti SQLite-tiedoston polkua; nyt se on kannan NIMI.
    """
    return {
        "host": os.environ.get("JKR_DB_HOST", ""),
        "port": os.environ.get("JKR_DB_PORT", "5432") or "5432",
        "dbname": os.environ.get("JKR_EVENTS_DB", "systemevents"),
        "user": os.environ.get("JKR_USER", ""),
        "password": os.environ.get("JKR_PASSWORD", ""),
        # Sama oletus kuin sovelluksen muulla yhteydellä (SQLAlchemy ei aseta
        # sslmodea, jolloin psycopg2 kayttaa 'prefer'). Azure vaatii SSL:n,
        # joten 'prefer' neuvottelee sen kayttoon.
        "sslmode": os.environ.get("JKR_DB_SSLMODE", "prefer"),
        "connect_timeout": 10,
    }


def target() -> str:
    """Kuvaus kohteesta lokitusta varten (ei sisällä salasanaa)."""
    p = _conn_params()
    return f"{p['user']}@{p['host']}:{p['port']}/{p['dbname']}"


_SCHEMA = """
CREATE TABLE IF NOT EXISTS jarjestelmatapahtuma (
    id               text PRIMARY KEY,
    task_type        text NOT NULL,
    status           text NOT NULL,
    command          text,
    runner           text,
    description      text,
    started_at       text,
    finished_at      text,
    duration_seconds double precision,
    exit_code        integer,
    output           text,
    error            text,
    result_file      text,
    occurred_at      text
);
CREATE INDEX IF NOT EXISTS ix_tapahtuma_occurred
    ON jarjestelmatapahtuma (occurred_at DESC NULLS LAST);
"""


@contextmanager
def _connect():
    """Avaa yhteyden tapahtumakantaan, commitoi onnistuessa ja sulkee aina."""
    conn = psycopg2.connect(**_conn_params())
    try:
        yield conn
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


def ensure_schema() -> None:
    """Varmistaa että taulu ja indeksi ovat olemassa (luo puuttuvat)."""
    try:
        with _connect() as conn:
            with conn.cursor() as cur:
                cur.execute(_SCHEMA)
        logger.info("Järjestelmätapahtumakanta valmiina: %s", target())
    except Exception:
        logger.exception("Tapahtumakannan alustus epäonnistui (%s)", target())


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
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO jarjestelmatapahtuma (
                        id, task_type, status, command, runner, description,
                        started_at, finished_at, duration_seconds, exit_code,
                        output, error, result_file, occurred_at
                    ) VALUES (
                        %(id)s, %(task_type)s, %(status)s, %(command)s, %(runner)s,
                        %(description)s, %(started_at)s, %(finished_at)s,
                        %(duration_seconds)s, %(exit_code)s, %(output)s, %(error)s,
                        %(result_file)s, %(occurred_at)s
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        task_type=EXCLUDED.task_type,
                        status=EXCLUDED.status,
                        command=EXCLUDED.command,
                        runner=EXCLUDED.runner,
                        description=EXCLUDED.description,
                        started_at=EXCLUDED.started_at,
                        finished_at=EXCLUDED.finished_at,
                        duration_seconds=EXCLUDED.duration_seconds,
                        exit_code=EXCLUDED.exit_code,
                        output=EXCLUDED.output,
                        error=EXCLUDED.error,
                        result_file=EXCLUDED.result_file,
                        occurred_at=EXCLUDED.occurred_at
                    """,
                    row,
                )
    except Exception:
        logger.exception("Tapahtuman tallennus epäonnistui (id=%s)", getattr(task, "id", "?"))


def recent(limit: int = 50) -> List[dict]:
    """Palauttaa viimeisimmät tapahtumat dict-listana (TaskInfo-kentännimillä).

    Lajittelu occurred_at DESC; NULL-arvot (esim. ajamattomat) jäävät loppuun.
    HUOM: Postgres asettaa DESC-lajittelussa NULLit ENSIN, toisin kuin SQLite,
    joten NULLS LAST on kirjoitettava näkyviin jotta järjestys säilyy ennallaan.
    """
    try:
        with _connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT * FROM jarjestelmatapahtuma
                    ORDER BY occurred_at DESC NULLS LAST
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
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
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM jarjestelmatapahtuma
                    WHERE id NOT IN (
                        SELECT id FROM jarjestelmatapahtuma
                        ORDER BY occurred_at DESC NULLS LAST
                        LIMIT %s
                    )
                    """,
                    (keep,),
                )
    except Exception:
        logger.exception("Tapahtumien siivous epäonnistui")
