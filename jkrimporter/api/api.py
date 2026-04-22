"""
JKR REST API

FastAPI-pohjainen REST-rajapinta JKR-komentojen ajamiseen.
Mahdollistaa scripts/2024_start.sh -tyylisten komentojen ajamisen HTTP-kutsuilla.

Käynnistys:
    uvicorn jkrimporter.api.api:app --host 0.0.0.0 --port 8000 --reload

Tai:
    python -m jkrimporter.api.api
"""

import asyncio
import collections
import json
import logging
import os
import subprocess
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import aiofiles
import hashlib

from jkrimporter import ws_log_handler
from jkrimporter.api.auth import CurrentUser, require_admin, require_authenticated, require_viewer_or_admin, validate_ws_token
from jkrimporter.api import sharepoint as sp
from jkrimporter.api import licenses as lic

# ---------------------------------------------------------------------------
# Logging (käyttää jkrimporter.__init__:ssä konfiguroitua root loggeria)
# ---------------------------------------------------------------------------
logger = logging.getLogger("jkr-api")

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="JKR API",
    description="REST-rajapinta JKR-tiedontuontikomentojen ajamiseen.",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
UPLOAD_DIR = Path("/data/input")


# ---------------------------------------------------------------------------
# Ympäristömuuttujat (samat kuin 2024_start.sh:ssa)
# ---------------------------------------------------------------------------
def _db_env() -> dict:
    """Palauttaa tietokantaympäristömuuttujat shell-komentoja varten."""
    return {
        **os.environ,
        "HOST": os.environ.get("JKR_DB_HOST", ""),
        "PORT": os.environ.get("JKR_DB_PORT", ""),
        "DB_NAME": os.environ.get("JKR_DB", ""),
        "USER": os.environ.get("JKR_USER", ""),
        "PGPASSWORD": os.environ.get("JKR_PASSWORD", ""),
        "PGCLIENTENCODING": "UTF8",
    }


# ---------------------------------------------------------------------------
# Tehtävien seuranta (in-memory)
# ---------------------------------------------------------------------------
class TaskStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class TaskInfo(BaseModel):
    id: str
    status: TaskStatus
    command: str
    description: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    exit_code: Optional[int] = None
    output: str = ""
    error: str = ""


# Yksinkertainen in-memory -varasto tehtäville
_tasks: Dict[str, TaskInfo] = {}


def _create_task(command: str, description: str) -> TaskInfo:
    task = TaskInfo(
        id=str(uuid.uuid4()),
        status=TaskStatus.pending,
        command=command,
        description=description,
    )
    _tasks[task.id] = task
    return task


_TASK_OUTPUT_TAIL = 100  # task.output/error säilyttää vain viimeiset N riviä


async def _run_task(task_id: str, command: str, cwd: Optional[str] = None):
    """Suorittaa komennon taustalla ja päivittää tehtävän tilan.

    Lukee stdout/stderr rivi kerrallaan reaaliajassa, jotta:
    - rivit logitetaan Pythonin loggeriin (→ WebSocket-loki, tiedostoloki, konsoli)
    - task.output/error sisältää vain viimeiset _TASK_OUTPUT_TAIL riviä (kevyt JSON)
    """
    task = _tasks[task_id]
    task.status = TaskStatus.running
    task.started_at = datetime.now()
    task_logger = logging.getLogger(f"task.{task_id[:8]}")

    output_buf: collections.deque = collections.deque(maxlen=_TASK_OUTPUT_TAIL)
    error_buf: collections.deque = collections.deque(maxlen=_TASK_OUTPUT_TAIL)

    async def _read_stream(stream, buf: collections.deque, level: int):
        """Lukee streamin rivi kerrallaan ja logittaa jokaisen.

        Käyttää read()-chunkkeja readline():n sijaan, jotta ylipitkät rivit
        (esim. debug-printit) eivät aiheuta asyncio LimitOverrunError-virhettä.
        """
        remainder = b""
        while True:
            chunk = await stream.read(65536)  # 64 KiB kerrallaan
            if not chunk:
                # Käsittele viimeinen pätkä
                if remainder:
                    line = remainder.decode("utf-8", errors="replace").rstrip("\n")
                    if line:
                        buf.append(line)
                        task_logger.log(level, line[:2000])
                break
            data = remainder + chunk
            # Jaa riveihin
            while b"\n" in data:
                line_bytes, data = data.split(b"\n", 1)
                line = line_bytes.decode("utf-8", errors="replace")
                if line:
                    buf.append(line)
                    task_logger.log(level, line[:2000])  # Rajoita logiviesti 2000 merkkiin
            remainder = data
            # Päivitä task.output/error reaaliajassa (vain viimeiset rivit)
            if level <= logging.INFO:
                task.output = "\n".join(output_buf)
            else:
                task.error = "\n".join(error_buf)

    proc = None
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_db_env(),
            cwd=cwd,
        )

        await asyncio.gather(
            _read_stream(proc.stdout, output_buf, logging.INFO),
            _read_stream(proc.stderr, error_buf, logging.WARNING),
        )
        await proc.wait()

        task.exit_code = proc.returncode
        task.output = "\n".join(output_buf)
        task.error = "\n".join(error_buf)
        task.status = TaskStatus.completed if proc.returncode == 0 else TaskStatus.failed
    except Exception as e:
        task.status = TaskStatus.failed
        task.error = "\n".join(error_buf) + "\n" + str(e) if error_buf else str(e)
    finally:
        # Varmista exit_code myös virhetilanteissa
        if proc is not None and task.exit_code is None:
            try:
                if proc.returncode is None:
                    await proc.wait()
                task.exit_code = proc.returncode
            except Exception:
                pass
        task.output = "\n".join(output_buf)
        task.finished_at = datetime.now()
        if task.started_at:
            task.duration_seconds = (task.finished_at - task.started_at).total_seconds()

    logger.info(
        "Tehtävä %s (%s) valmis – status=%s, kesto=%.1fs",
        task.id,
        task.description,
        task.status,
        task.duration_seconds or 0,
    )


# ---------------------------------------------------------------------------
# Pyynnöt (Request models)
# ---------------------------------------------------------------------------
class JkrImportRequest(BaseModel):
    """jkr import <siirtotiedosto> <tiedontuottaja> <alkupvm> <loppupvm>"""
    siirtotiedosto: str = Field(..., description="Siirtotiedoston kansio")
    tiedontuottajatunnus: str = Field(..., description="Esim. 'LSJ'")
    alkupvm: str = Field(..., description="Alkupvm, esim. '1.1.2024'")
    loppupvm: str = Field(..., description="Loppupvm, esim. '31.3.2024'")


class JkrImportLieteRequest(BaseModel):
    """jkr import_liete <siirtotiedosto> <tiedontuottaja> <alkupvm> <loppupvm>"""
    siirtotiedosto: str = Field(..., description="LIETE Excel-tiedoston polku")
    tiedontuottajatunnus: str = Field("LSJ")
    alkupvm: str = Field(..., description="Alkupvm, esim. '1.1.2024'")
    loppupvm: str = Field(..., description="Loppupvm, esim. '31.3.2024'")


class JkrImportPaatoksetRequest(BaseModel):
    """jkr import_paatokset <siirtotiedosto>"""
    siirtotiedosto: str = Field(..., description="Päätöstiedoston polku")


class JkrImportIlmoituksetRequest(BaseModel):
    """jkr import_ilmoitukset <siirtotiedosto>"""
    siirtotiedosto: str = Field(..., description="Kompostointi-ilmoitustiedoston polku")


class JkrImportLieteIlmoituksetRequest(BaseModel):
    """jkr import_liete_ilmoitukset <siirtotiedosto>"""
    siirtotiedosto: str = Field(..., description="Liete kompostointi-ilmoitustiedoston polku")


class JkrImportLopetusilmoituksetRequest(BaseModel):
    """jkr import_lopetusilmoitukset <siirtotiedosto>"""
    siirtotiedosto: str = Field(..., description="Lopetusilmoitustiedoston polku")


class JkrImportKaivotiedotRequest(BaseModel):
    """jkr import_kaivotiedot <siirtotiedosto> <tiedontuottaja>"""
    siirtotiedosto: str = Field(..., description="Kaivotiedot Excel-tiedoston polku")
    tiedontuottajatunnus: str = Field("LSJ")


class JkrImportKaivotiedonLopetuksetRequest(BaseModel):
    """jkr import_kaivotiedon_lopetukset <siirtotiedosto> <tiedontuottaja>"""
    siirtotiedosto: str = Field(..., description="Kaivotiedon lopetus Excel-tiedoston polku")
    tiedontuottajatunnus: str = Field("LSJ")


class JkrImportViemaritRequest(BaseModel):
    """jkr import_viemarit <siirtotiedosto>"""
    siirtotiedosto: str = Field(..., description="Viemäritiedoston polku")


class JkrImportLopetaViemaritRequest(BaseModel):
    """jkr import_lopeta_viemarit <siirtotiedosto>"""
    siirtotiedosto: str = Field(..., description="Viemärin lopetustiedoston polku")


class JkrCreateDvvKohteetRequest(BaseModel):
    """jkr create_dvv_kohteet <poimintapvm> <perusmaksutiedosto>"""
    poimintapvm: str = Field(..., description="Poimintapvm, esim. '07.03.2024'")
    perusmaksutiedosto: Optional[str] = Field(None, description="Perusmaksurekisteritiedoston polku")


class TiedontuottajaAddRequest(BaseModel):
    """jkr tiedontuottaja add <tunnus> <nimi>"""
    tunnus: str
    nimi: str


class PsqlRequest(BaseModel):
    """Aja psql-komento (SQL-lause tai -f tiedosto)."""
    sql: Optional[str] = Field(None, description="SQL-lause suoritettavaksi (-c)")
    file: Optional[str] = Field(None, description="SQL-tiedoston polku (-f)")


class Ogr2ogrRequest(BaseModel):
    """Aja ogr2ogr-komento DVV-aineiston tuontiin."""
    source_file: str = Field(..., description="Lähdetiedoston polku (esim. Excel)")
    layer_name: str = Field(..., description="Lähdetiedoston taulun/välilehden nimi")
    target_table: str = Field(..., description="Kohdetaulun nimi PostgreSQL:ssä")
    target_schema: str = Field("jkr_dvv", description="Kohdeschema")


class ShellScriptRequest(BaseModel):
    """Aja shell-skripti parametreilla."""
    script: str = Field(..., description="Skriptin polku, esim. 'import_taajama.sh'")
    args: List[str] = Field(default_factory=list, description="Skriptin parametrit")


class TallennaVelvoiteStatusRequest(BaseModel):
    """psql: SELECT jkr.tallenna_velvoite_status(<pvm>)"""
    pvm: str = Field(..., description="Päivämäärä, esim. '2024-03-31'")


class CopyFromCsvRequest(BaseModel):
    """psql \\copy -komento CSV-tiedoston tuontiin."""
    table: str = Field(..., description="Kohdetaulu, esim. 'jkr_koodistot.tiedontuottaja(tunnus, nimi)'")
    file_path: str = Field(..., description="CSV-tiedoston polku")
    delimiter: str = Field(";", description="Sarake-erotin")
    header: bool = Field(True)
    encoding: str = Field("UTF8")


class ImportTaajamaRequest(BaseModel):
    """import_taajama.sh <alkupvm>"""
    alkupvm: str = Field(..., description="Taajamarajausten alkupvm, esim. '2026-01-01'")


class ImportViemariRequest(BaseModel):
    """import_viemari.sh <alkupvm> <shp_tiedosto>"""
    alkupvm: str = Field(..., description="Viemäriverkoston alkupvm, esim. '2023-01-01'")
    shp_tiedosto: str = Field(..., description="SHP-tiedoston polku")


class RunFullPipelineRequest(BaseModel):
    """Aja koko 2024_start.sh -tyylinen pipeline."""
    script_path: str = Field("scripts/2024_start.sh", description="Skriptin polku")


# ---------------------------------------------------------------------------
# Apufunktiot komentojen muodostamiseen
# ---------------------------------------------------------------------------
def _psql_cmd(sql: Optional[str] = None, file: Optional[str] = None) -> str:
    host = os.environ.get("JKR_DB_HOST", "")
    port = os.environ.get("JKR_DB_PORT", "")
    db = os.environ.get("JKR_DB", "")
    user = os.environ.get("JKR_USER", "")
    base = f'psql -h {host} -p {port} -d {db} -U {user}'
    if sql:
        return f'{base} -c "{sql}"'
    if file:
        return f'{base} -f {file}'
    raise ValueError("sql tai file vaaditaan")


def _ogr2ogr_cmd(source: str, layer: str, table: str, schema: str) -> str:
    host = os.environ.get("JKR_DB_HOST", "")
    port = os.environ.get("JKR_DB_PORT", "")
    db = os.environ.get("JKR_DB", "")
    user = os.environ.get("JKR_USER", "")
    pw = os.environ.get("JKR_PASSWORD", "")
    pg_conn = f'PG:"host={host} port={port} dbname={db} user={user} password={pw} ACTIVE_SCHEMA={schema}"'
    return f'ogr2ogr -f PostgreSQL -overwrite -progress {pg_conn} -nln {table} "{source}" "{layer}"'


SCRIPTS_DIR = Path(__file__).resolve().parent.parent.parent / "scripts"


# ---------------------------------------------------------------------------
# Vastaus (Response model)
# ---------------------------------------------------------------------------
class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    description: str
    message: str = "Tehtävä käynnistetty. Seuraa tilaa GET /tasks/{task_id}"


# ---------------------------------------------------------------------------
# Endpointit: Tehtävien hallinta
# ---------------------------------------------------------------------------
@app.get("/tasks", summary="Listaa kaikki tehtävät")
async def list_tasks(user: CurrentUser = Depends(require_authenticated)):
    return list(_tasks.values())


@app.get("/tasks/{task_id}", summary="Hae tehtävän tila", response_model=TaskInfo)
async def get_task(task_id: str, user: CurrentUser = Depends(require_authenticated)):
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Tehtävää ei löydy")
    return _tasks[task_id]


# ---------------------------------------------------------------------------
# Endpointit: jkr CLI -komennot
# ---------------------------------------------------------------------------
@app.post("/jkr/import", summary="jkr import – Kuljetustietojen tuonti", response_model=TaskResponse)
async def jkr_import(req: JkrImportRequest, background_tasks: BackgroundTasks, user: CurrentUser = Depends(require_admin)):
    cmd = f"jkr import {req.siirtotiedosto} {req.tiedontuottajatunnus} {req.alkupvm} {req.loppupvm}"
    task = _create_task(cmd, f"Kuljetustietojen tuonti ({req.tiedontuottajatunnus} {req.alkupvm}-{req.loppupvm})")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/jkr/import_liete", summary="jkr import_liete – LIETE-kuljetustietojen tuonti", response_model=TaskResponse)
async def jkr_import_liete(req: JkrImportLieteRequest, background_tasks: BackgroundTasks, user: CurrentUser = Depends(require_admin)):
    cmd = f"jkr import_liete {req.siirtotiedosto} {req.tiedontuottajatunnus} {req.alkupvm} {req.loppupvm}"
    task = _create_task(cmd, f"LIETE-kuljetustietojen tuonti ({req.alkupvm}-{req.loppupvm})")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/jkr/import_paatokset", summary="jkr import_paatokset – Päätösten tuonti", response_model=TaskResponse)
async def jkr_import_paatokset(req: JkrImportPaatoksetRequest, background_tasks: BackgroundTasks, user: CurrentUser = Depends(require_admin)):
    cmd = f"jkr import_paatokset {req.siirtotiedosto}"
    task = _create_task(cmd, "Päätösten tuonti")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/jkr/import_ilmoitukset", summary="jkr import_ilmoitukset – Ilmoitusten tuonti", response_model=TaskResponse)
async def jkr_import_ilmoitukset(req: JkrImportIlmoituksetRequest, background_tasks: BackgroundTasks, user: CurrentUser = Depends(require_admin)):
    cmd = f"jkr import_ilmoitukset {req.siirtotiedosto}"
    task = _create_task(cmd, "Kompostointi-ilmoitusten tuonti")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/jkr/import_liete_ilmoitukset", summary="jkr import_liete_ilmoitukset – Liete-ilmoitusten tuonti", response_model=TaskResponse)
async def jkr_import_liete_ilmoitukset(req: JkrImportLieteIlmoituksetRequest, background_tasks: BackgroundTasks, user: CurrentUser = Depends(require_admin)):
    cmd = f"jkr import_liete_ilmoitukset {req.siirtotiedosto}"
    task = _create_task(cmd, "Liete kompostointi-ilmoitusten tuonti")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/jkr/import_lopetusilmoitukset", summary="jkr import_lopetusilmoitukset – Lopetusilmoitusten tuonti", response_model=TaskResponse)
async def jkr_import_lopetusilmoitukset(req: JkrImportLopetusilmoituksetRequest, background_tasks: BackgroundTasks, user: CurrentUser = Depends(require_admin)):
    cmd = f"jkr import_lopetusilmoitukset {req.siirtotiedosto}"
    task = _create_task(cmd, "Lopetusilmoitusten tuonti")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/jkr/import_kaivotiedot", summary="jkr import_kaivotiedot – Kaivotietojen tuonti", response_model=TaskResponse)
async def jkr_import_kaivotiedot(req: JkrImportKaivotiedotRequest, background_tasks: BackgroundTasks, user: CurrentUser = Depends(require_admin)):
    cmd = f"jkr import_kaivotiedot {req.siirtotiedosto} {req.tiedontuottajatunnus}"
    task = _create_task(cmd, "Kaivotietojen tuonti")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/jkr/import_kaivotiedon_lopetukset", summary="jkr import_kaivotiedon_lopetukset – Kaivotiedon lopetusten tuonti", response_model=TaskResponse)
async def jkr_import_kaivotiedon_lopetukset(req: JkrImportKaivotiedonLopetuksetRequest, background_tasks: BackgroundTasks, user: CurrentUser = Depends(require_admin)):
    cmd = f"jkr import_kaivotiedon_lopetukset {req.siirtotiedosto} {req.tiedontuottajatunnus}"
    task = _create_task(cmd, "Kaivotiedon lopetusten tuonti")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/jkr/import_viemarit", summary="jkr import_viemarit – Viemäritietojen tuonti", response_model=TaskResponse)
async def jkr_import_viemarit(req: JkrImportViemaritRequest, background_tasks: BackgroundTasks, user: CurrentUser = Depends(require_admin)):
    cmd = f"jkr import_viemarit {req.siirtotiedosto}"
    task = _create_task(cmd, "Viemäritietojen tuonti")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/jkr/import_lopeta_viemarit", summary="jkr import_lopeta_viemarit – Viemärin lopetusten tuonti", response_model=TaskResponse)
async def jkr_import_lopeta_viemarit(req: JkrImportLopetaViemaritRequest, background_tasks: BackgroundTasks, user: CurrentUser = Depends(require_admin)):
    cmd = f"jkr import_lopeta_viemarit {req.siirtotiedosto}"
    task = _create_task(cmd, "Viemärin lopetusten tuonti")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/jkr/create_dvv_kohteet", summary="jkr create_dvv_kohteet – Kohteiden luonti DVV-aineistosta", response_model=TaskResponse)
async def jkr_create_dvv_kohteet(req: JkrCreateDvvKohteetRequest, background_tasks: BackgroundTasks, user: CurrentUser = Depends(require_admin)):
    cmd = f"jkr create_dvv_kohteet {req.poimintapvm}"
    if req.perusmaksutiedosto:
        cmd += f" {req.perusmaksutiedosto}"
    task = _create_task(cmd, "Kohteiden luonti DVV-aineistosta")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/jkr/tiedontuottaja/add", summary="jkr tiedontuottaja add – Lisää tiedontuottaja", response_model=TaskResponse)
async def jkr_tiedontuottaja_add(req: TiedontuottajaAddRequest, background_tasks: BackgroundTasks, user: CurrentUser = Depends(require_admin)):
    cmd = f"jkr tiedontuottaja add {req.tunnus} '{req.nimi}'"
    task = _create_task(cmd, f"Tiedontuottajan lisäys: {req.tunnus}")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.get("/jkr/tiedontuottaja/list", summary="jkr tiedontuottaja list – Listaa tiedontuottajat")
async def jkr_tiedontuottaja_list(user: CurrentUser = Depends(require_authenticated)):
    proc = subprocess.run(
        "jkr tiedontuottaja list",
        shell=True,
        capture_output=True,
        text=True,
        env=_db_env(),
    )
    return {"output": proc.stdout, "exit_code": proc.returncode}


# ---------------------------------------------------------------------------
# Endpointit: psql-komennot
# ---------------------------------------------------------------------------
@app.post("/psql/exec", summary="Suorita psql-komento (SQL tai tiedosto)", response_model=TaskResponse)
async def psql_exec(req: PsqlRequest, background_tasks: BackgroundTasks, user: CurrentUser = Depends(require_admin)):
    if not req.sql and not req.file:
        raise HTTPException(status_code=400, detail="Anna joko 'sql' tai 'file'")
    cmd = _psql_cmd(sql=req.sql, file=req.file)
    desc = f"psql: {req.sql or req.file}"
    task = _create_task(cmd, desc)
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/psql/copy_csv", summary="psql \\copy CSV-tiedostosta", response_model=TaskResponse)
async def psql_copy_csv(req: CopyFromCsvRequest, background_tasks: BackgroundTasks, user: CurrentUser = Depends(require_admin)):
    header_str = "true" if req.header else "false"
    copy_cmd = (
        f"\\copy {req.table} FROM '{req.file_path}' "
        f"WITH (FORMAT CSV, DELIMITER '{req.delimiter}', HEADER {header_str}, "
        f"ENCODING '{req.encoding}', NULL '')"
    )
    cmd = _psql_cmd(sql=copy_cmd)
    task = _create_task(cmd, f"CSV-tuonti: {req.file_path} → {req.table}")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/psql/update_velvoitteet", summary="Velvoitteiden päivitys", response_model=TaskResponse)
async def psql_update_velvoitteet(background_tasks: BackgroundTasks, user: CurrentUser = Depends(require_admin)):
    cmd = _psql_cmd(sql="SELECT jkr.update_velvoitteet();")
    task = _create_task(cmd, "Velvoitteiden päivitys")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/psql/tallenna_velvoite_status", summary="Velvoite-statuksen tallennus", response_model=TaskResponse)
async def psql_tallenna_velvoite_status(req: TallennaVelvoiteStatusRequest, background_tasks: BackgroundTasks, user: CurrentUser = Depends(require_admin)):
    cmd = _psql_cmd(sql=f"SELECT jkr.tallenna_velvoite_status('{req.pvm}');")
    task = _create_task(cmd, f"Velvoite-statuksen tallennus ({req.pvm})")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


# ---------------------------------------------------------------------------
# Endpointit: ogr2ogr (DVV-aineiston tuonti)
# ---------------------------------------------------------------------------
@app.post("/ogr2ogr/import", summary="ogr2ogr – Tuo aineisto PostgreSQL:ään", response_model=TaskResponse)
async def ogr2ogr_import(req: Ogr2ogrRequest, background_tasks: BackgroundTasks, user: CurrentUser = Depends(require_admin)):
    cmd = _ogr2ogr_cmd(req.source_file, req.layer_name, req.target_table, req.target_schema)
    task = _create_task(cmd, f"ogr2ogr: {req.layer_name} → {req.target_schema}.{req.target_table}")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


# ---------------------------------------------------------------------------
# Endpointit: Shell-skriptit
# ---------------------------------------------------------------------------
@app.post("/scripts/import_taajama", summary="Taajamarajausten tuonti (import_taajama.sh)", response_model=TaskResponse)
async def scripts_import_taajama(req: ImportTaajamaRequest, background_tasks: BackgroundTasks, user: CurrentUser = Depends(require_admin)):
    cmd = f"sh import_taajama.sh {req.alkupvm}"
    task = _create_task(cmd, f"Taajamarajausten tuonti ({req.alkupvm})")
    background_tasks.add_task(_run_task, task.id, cmd, cwd=str(SCRIPTS_DIR))
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/scripts/import_viemari", summary="Viemäriverkoston tuonti (import_viemari.sh)", response_model=TaskResponse)
async def scripts_import_viemari(req: ImportViemariRequest, background_tasks: BackgroundTasks, user: CurrentUser = Depends(require_admin)):
    cmd = f"sh import_viemari.sh {req.alkupvm} {req.shp_tiedosto}"
    task = _create_task(cmd, f"Viemäriverkoston tuonti ({req.alkupvm})")
    background_tasks.add_task(_run_task, task.id, cmd, cwd=str(SCRIPTS_DIR))
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/scripts/run", summary="Aja mikä tahansa shell-skripti", response_model=TaskResponse)
async def scripts_run(req: ShellScriptRequest, background_tasks: BackgroundTasks, user: CurrentUser = Depends(require_admin)):
    args_str = " ".join(req.args)
    cmd = f"sh {req.script} {args_str}".strip()
    task = _create_task(cmd, f"Skripti: {req.script}")
    background_tasks.add_task(_run_task, task.id, cmd, cwd=str(SCRIPTS_DIR))
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


# ---------------------------------------------------------------------------
# Endpointit: Koko pipeline
# ---------------------------------------------------------------------------
@app.post("/pipeline/run", summary="Aja koko tuontiskripti (esim. 2024_start.sh)", response_model=TaskResponse)
async def pipeline_run(req: RunFullPipelineRequest, background_tasks: BackgroundTasks, user: CurrentUser = Depends(require_admin)):
    project_root = Path(__file__).resolve().parent.parent.parent
    script = project_root / req.script_path
    if not script.exists():
        raise HTTPException(status_code=404, detail=f"Skriptiä ei löydy: {req.script_path}")
    cmd = f"bash {script}"
    task = _create_task(cmd, f"Pipeline: {req.script_path}")
    background_tasks.add_task(_run_task, task.id, cmd, cwd=str(SCRIPTS_DIR))
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


# ---------------------------------------------------------------------------
# Endpointit: Yleinen komento (vapaa komento)
# ---------------------------------------------------------------------------
class GenericCommandRequest(BaseModel):
    """Aja mikä tahansa komento."""
    command: str = Field(..., description="Suoritettava komento")
    description: str = Field("Vapaa komento", description="Kuvaus")
    cwd: Optional[str] = Field(None, description="Työhakemisto")


@app.post("/command/run", summary="Aja vapaa komento", response_model=TaskResponse)
async def command_run(req: GenericCommandRequest, background_tasks: BackgroundTasks, user: CurrentUser = Depends(require_admin)):
    task = _create_task(req.command, req.description)
    background_tasks.add_task(_run_task, task.id, req.command, cwd=req.cwd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


# ---------------------------------------------------------------------------
# Tietokantadokumentaatio
# ---------------------------------------------------------------------------
@app.get("/db/documentation", summary="Tietokantadokumentaatio (jkr-skeemat)")
async def db_documentation(user: CurrentUser = Depends(require_authenticated)):
    """Palauttaa jkr-skeemojen taulut, kentät, kommentit ja tyypit."""
    env = _db_env()
    sql = r"""
SELECT json_agg(row_to_json(t)) FROM (
    SELECT
        c.table_schema as skeema,
        c.table_name as taulu,
        obj_description((c.table_schema || '.' || c.table_name)::regclass) as taulun_kommentti,
        c.column_name as kentta,
        col_description((c.table_schema || '.' || c.table_name)::regclass, c.ordinal_position) as kentan_kommentti,
        COALESCE(
            upper(g.type),
            CASE
                WHEN c.data_type = 'character varying' THEN 'character varying'
                WHEN c.data_type = 'character' THEN 'character'
                WHEN c.data_type = 'USER-DEFINED' THEN c.udt_name
                ELSE c.data_type
            END
        ) AS tyyppi,
        g.coord_dimension AS dimensions,
        g.srid AS coordinate_system,
        c.is_nullable
    FROM information_schema.columns c
    LEFT JOIN geometry_columns g
        ON c.table_schema = g.f_table_schema
        AND c.table_name = g.f_table_name
        AND c.column_name = g.f_geometry_column
    WHERE c.table_schema ILIKE 'jkr%%'
    ORDER BY c.table_schema, c.table_name, c.ordinal_position
) t;
"""
    try:
        cmd = [
            "psql", "-h", env.get("HOST", ""),
            "-p", env.get("PORT", "5432"),
            "-U", env.get("USER", ""),
            "-d", env.get("DB_NAME", ""),
            "-t", "-A",
            "-c", sql,
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, env=env, timeout=30,
        )
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=result.stderr.strip())

        import json as _json
        raw = result.stdout.strip()
        if not raw:
            return []
        rows = _json.loads(raw)
        return rows if rows else []
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Tietokantakysely aikakatkaistiin")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Open Source Compliance / Third-Party Notices / SBOM
# ---------------------------------------------------------------------------
@app.get(
    "/licenses",
    summary="Backendin kirjastojen lisenssit (Open Source Compliance / SBOM)",
)
async def licenses_list(
    format: str = Query("json", pattern="^(json|text)$", description="Palautusmuoto: 'json' tai 'text' (NOTICE-tiedosto)."),
    user: CurrentUser = Depends(require_authenticated),
):
    """Listaa kaikki asennetut Python-paketit lisenssitietoineen.

    - `format=json` (oletus): rakenteinen lista SBOM-tyylisesti.
    - `format=text`: tekstimuotoinen THIRD-PARTY-NOTICES attribuutiovaatimukseen.

    Tiedot luetaan Python-pakettien omasta metadatasta (`importlib.metadata`),
    joten listassa näkyvät myös transitiiviset riippuvuudet ja niiden
    todelliset asennetut versiot.
    """
    try:
        dists = lic.list_distributions()
        app_info = {
            "name": app.title,
            "version": app.version,
            "license": "GPL-3.0-or-later",
        }
        if format == "text":
            from fastapi.responses import PlainTextResponse
            body = lic.render_notices_text(dists)
            header = (
                f"{app_info['name']} v{app_info['version']}\n"
                f"Päätuotteen lisenssi: {app_info['license']}\n\n"
            )
            return PlainTextResponse(content=header + body, media_type="text/plain; charset=utf-8")
        return {
            "application": app_info,
            "count": len(dists),
            "dependencies": dists,
        }
    except Exception as e:
        logger.exception("Lisenssilistan haku epäonnistui: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get(
    "/licenses/{package_name}",
    summary="Yksittäisen kirjaston lisenssitiedot ja lisenssitiedoston sisältö",
)
async def license_detail(
    package_name: str,
    user: CurrentUser = Depends(require_authenticated),
):
    """Palauttaa paketin metatiedot, SPDX-lisenssi-ilmaisun ja mahdolliset
    lisenssitiedostot (LICENSE/COPYING/NOTICE) kokonaisuudessaan."""
    try:
        return lic.get_distribution(package_name)
    except LookupError:
        raise HTTPException(status_code=404, detail=f"Pakettia ei löydy: {package_name}")
    except Exception as e:
        logger.exception("Lisenssitietojen haku epäonnistui (%s): %s", package_name, e)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Auth: Käyttäjätiedot (Flutter-frontin käyttöön)
# ---------------------------------------------------------------------------
@app.get("/auth/me", summary="Kirjautuneen käyttäjän tiedot ja roolit")
async def auth_me(user: CurrentUser = Depends(require_authenticated)):
    """Palauttaa tokenista puretut käyttäjätiedot. Flutter kutsuu tätä kirjautumisen jälkeen."""
    return {
        "oid": user.oid,
        "name": user.name,
        "email": user.email,
        "roles": user.roles,
        "is_admin": user.is_admin,
        "is_viewer": user.is_viewer,
    }


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", summary="Terveystarkistus")
async def health():
    db_ok = False
    db_error = None
    try:
        from jkrimporter.providers.db.database import engine
        from sqlalchemy import text as sa_text
        with engine.connect() as conn:
            conn.execute(sa_text("SELECT 1"))
            conn.commit()
        db_ok = True
    except Exception as e:
        db_error = str(e)

    status = "ok" if db_ok else "degraded"
    return {
        "status": status,
        "version": app.version,
        "timestamp": datetime.now().isoformat(),
        "database": {
            "connected": db_ok,
            "error": db_error,
        },
    }


# ---------------------------------------------------------------------------
# WebSocket: Reaaliaikainen loki
# ---------------------------------------------------------------------------
@app.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket, token: Optional[str] = Query(None)):
    """
    WebSocket-endpoint reaaliaikaiselle lokille.

    Yhdistettäessä lähetetään ensin viimeisimmät puskuroidut viestit (max 500),
    jonka jälkeen uudet viestit streamataan reaaliajassa.

    Client voi lähettää JSON-viestin log-tason suodattamiseksi:
        {"min_level": 25}   # näytä vain IMPORT (25) ja sitä vakavammat

    Autentikointi: ws://host/ws/logs?token=<bearer_token>
    """
    try:
        await validate_ws_token(token)
    except Exception:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    min_level = 0
    queue: asyncio.Queue = asyncio.Queue()

    async def _sender(text: str):
        await queue.put(text)

    ws_log_handler.register(_sender)
    try:
        # Lähetä puskuroidut viestit
        for entry in ws_log_handler.get_buffer():
            if entry.get("levelno", 0) >= min_level:
                await websocket.send_json(entry)

        # Kuuntele sekä uusia logeja että clientin viestejä rinnakkain
        async def _read_client():
            nonlocal min_level
            while True:
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                    if "min_level" in msg:
                        min_level = int(msg["min_level"])
                except (json.JSONDecodeError, ValueError):
                    pass

        async def _write_logs():
            while True:
                raw = await queue.get()
                try:
                    entry = json.loads(raw)
                    if entry.get("levelno", 0) >= min_level:
                        await websocket.send_text(raw)
                except Exception:
                    pass

        await asyncio.gather(_read_client(), _write_logs())

    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        ws_log_handler.unregister(_sender)


# ---------------------------------------------------------------------------
# Endpointit: Tiedostojen chunked upload
# ---------------------------------------------------------------------------
_active_uploads: Dict[str, dict] = {}


class UploadInitRequest(BaseModel):
    """Aloita chunked upload."""
    filename: str = Field(..., description="Tiedoston nimi")
    total_size: int = Field(..., description="Tiedoston kokonaiskoko tavuina")
    chunk_size: int = Field(5 * 1024 * 1024, description="Chunkin koko tavuina (oletus 5 MB)")
    subfolder: Optional[str] = Field(None, description="Alikansio /data/input -kansion alla")


class UploadInitResponse(BaseModel):
    upload_id: str
    filename: str
    total_size: int
    chunk_size: int
    total_chunks: int
    target_path: str


class UploadStatusResponse(BaseModel):
    upload_id: str
    filename: str
    total_chunks: int
    received_chunks: List[int]
    complete: bool
    target_path: str


@app.post("/upload/init", summary="Aloita chunked file upload", response_model=UploadInitResponse)
async def upload_init(req: UploadInitRequest, user: CurrentUser = Depends(require_admin)):
    """Aloittaa uuden chunked upload -session."""
    upload_id = str(uuid.uuid4())
    total_chunks = -(-req.total_size // req.chunk_size)  # ceil division

    target_dir = UPLOAD_DIR / req.subfolder if req.subfolder else UPLOAD_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / req.filename

    # Luo tyhjä temp-tiedosto
    temp_path = target_dir / f".{upload_id}.part"

    _active_uploads[upload_id] = {
        "filename": req.filename,
        "total_size": req.total_size,
        "chunk_size": req.chunk_size,
        "total_chunks": total_chunks,
        "received_chunks": set(),
        "target_path": str(target_path),
        "temp_path": str(temp_path),
        "created_at": datetime.now(),
    }

    logger.info("Upload aloitettu: %s -> %s (%d chunks)", upload_id[:8], req.filename, total_chunks)
    return UploadInitResponse(
        upload_id=upload_id,
        filename=req.filename,
        total_size=req.total_size,
        chunk_size=req.chunk_size,
        total_chunks=total_chunks,
        target_path=str(target_path),
    )


@app.post("/upload/{upload_id}/chunk", summary="Lähetä tiedoston chunk")
async def upload_chunk(
    upload_id: str,
    chunk_index: int = Form(...),
    chunk: UploadFile = File(...),
    user: CurrentUser = Depends(require_admin),
):
    """Vastaanottaa yksittäisen chunkin."""
    if upload_id not in _active_uploads:
        raise HTTPException(status_code=404, detail="Upload-sessiota ei löydy")

    session = _active_uploads[upload_id]
    if chunk_index < 0 or chunk_index >= session["total_chunks"]:
        raise HTTPException(status_code=400, detail=f"Virheellinen chunk_index: {chunk_index}")

    data = await chunk.read()
    temp_path = session["temp_path"]
    offset = chunk_index * session["chunk_size"]

    async with aiofiles.open(temp_path, mode="r+b" if os.path.exists(temp_path) else "wb") as f:
        await f.seek(offset)
        await f.write(data)

    session["received_chunks"].add(chunk_index)
    received = len(session["received_chunks"])
    total = session["total_chunks"]

    logger.info("Upload %s chunk %d/%d vastaanotettu (%d tavua)", upload_id[:8], chunk_index + 1, total, len(data))

    return {
        "upload_id": upload_id,
        "chunk_index": chunk_index,
        "received_chunks": received,
        "total_chunks": total,
        "complete": received == total,
    }


@app.post("/upload/{upload_id}/complete", summary="Viimeistele chunked upload")
async def upload_complete(upload_id: str, user: CurrentUser = Depends(require_admin)):
    """Viimeistelee uploadn: nimeää temp-tiedoston lopulliseksi."""
    if upload_id not in _active_uploads:
        raise HTTPException(status_code=404, detail="Upload-sessiota ei löydy")

    session = _active_uploads[upload_id]
    received = len(session["received_chunks"])
    total = session["total_chunks"]

    if received < total:
        missing = sorted(set(range(total)) - session["received_chunks"])
        raise HTTPException(
            status_code=400,
            detail=f"Puuttuu {total - received} chunkkia: {missing[:20]}",
        )

    temp_path = Path(session["temp_path"])
    target_path = Path(session["target_path"])

    if target_path.exists():
        target_path.unlink()
    temp_path.rename(target_path)

    file_size = target_path.stat().st_size
    del _active_uploads[upload_id]

    logger.info("Upload %s valmis: %s (%d tavua)", upload_id[:8], session["filename"], file_size)
    return {
        "upload_id": upload_id,
        "filename": session["filename"],
        "target_path": str(target_path),
        "file_size": file_size,
        "status": "completed",
    }


@app.get("/upload/{upload_id}/status", summary="Tarkista upload-session tila", response_model=UploadStatusResponse)
async def upload_status(upload_id: str, user: CurrentUser = Depends(require_authenticated)):
    if upload_id not in _active_uploads:
        raise HTTPException(status_code=404, detail="Upload-sessiota ei löydy")
    session = _active_uploads[upload_id]
    received = sorted(session["received_chunks"])
    return UploadStatusResponse(
        upload_id=upload_id,
        filename=session["filename"],
        total_chunks=session["total_chunks"],
        received_chunks=received,
        complete=len(received) == session["total_chunks"],
        target_path=session["target_path"],
    )


@app.post("/upload/file", summary="Lataa tiedosto kerralla")
async def upload_file(
    file: UploadFile = File(...),
    subfolder: Optional[str] = Form(None),
    user: CurrentUser = Depends(require_admin),
):
    """Lataa yksittäisen tiedoston kerralla /data/input -kansioon."""
    target_dir = UPLOAD_DIR / subfolder if subfolder else UPLOAD_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / file.filename

    async with aiofiles.open(str(target_path), "wb") as f:
        while True:
            chunk = await file.read(1024 * 1024)  # 1 MB kerrallaan
            if not chunk:
                break
            await f.write(chunk)

    file_size = target_path.stat().st_size
    logger.info("Tiedosto ladattu: %s (%d tavua)", file.filename, file_size)
    return {
        "filename": file.filename,
        "target_path": str(target_path),
        "file_size": file_size,
    }


@app.get("/upload/files", summary="Listaa /data/input -kansion tiedostot")
async def upload_list_files(subfolder: Optional[str] = Query(None), user: CurrentUser = Depends(require_authenticated)):
    target_dir = UPLOAD_DIR / subfolder if subfolder else UPLOAD_DIR
    if not target_dir.exists():
        return []
    files = []
    for f in sorted(target_dir.iterdir()):
        if f.is_file() and not f.name.startswith("."):
            files.append({
                "name": f.name,
                "path": str(f),
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
    return files


# ---------------------------------------------------------------------------
# SharePoint-integraatio
# ---------------------------------------------------------------------------

@app.get("/sharepoint/status", summary="SharePoint-integraation tila")
async def sharepoint_status(user: CurrentUser = Depends(require_authenticated)):
    configured = await sp.is_configured()
    return {
        "configured": configured,
        "site_id": sp.SHAREPOINT_SITE_ID or None,
        "input_folder": sp.SHAREPOINT_INPUT_FOLDER or None,
        "output_folder": sp.SHAREPOINT_OUTPUT_FOLDER or None,
    }


@app.get("/sharepoint/files", summary="Listaa SharePoint-kansion sisältö")
async def sharepoint_list_files(
    folder: Optional[str] = Query(None, description="Kansion polku (oletus: SHAREPOINT_INPUT_FOLDER)"),
    user: CurrentUser = Depends(require_authenticated),
):
    if not await sp.is_configured():
        raise HTTPException(status_code=503, detail="SharePoint-integraatio ei ole konfiguroitu")
    try:
        items = await sp.list_folder(folder)
        return items
    except Exception as e:
        logger.error("SharePoint listaus epäonnistui: %s", e)
        raise HTTPException(status_code=500, detail=f"SharePoint-virhe: {e}")


@app.get("/sharepoint/download", summary="Lataa tiedosto SharePointista")
async def sharepoint_download(
    path: str = Query(..., description="Tiedoston polku SharePointissa"),
    user: CurrentUser = Depends(require_authenticated),
):
    if not await sp.is_configured():
        raise HTTPException(status_code=503, detail="SharePoint-integraatio ei ole konfiguroitu")
    try:
        content, filename, content_type = await sp.download_file(path)
        from fastapi.responses import Response
        return Response(
            content=content,
            media_type=content_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        logger.error("SharePoint download epäonnistui: %s", e)
        raise HTTPException(status_code=500, detail=f"SharePoint-virhe: {e}")


@app.post("/sharepoint/pull", summary="Lataa tiedosto(t) SharePointista palvelimen /data/input -kansioon")
async def sharepoint_pull(
    paths: List[str] = Query(..., description="SharePoint-tiedostopolut ladattavaksi"),
    subfolder: Optional[str] = Query(None, description="Alikansio /data/input alla"),
    user: CurrentUser = Depends(require_admin),
):
    """Lataa valitut tiedostot SharePointista suoraan palvelimen levylle.

    Tiedostot streamataan suoraan /data/input -hakemistoon ilman,
    että ne kulkevat selaimen kautta.
    """
    if not await sp.is_configured():
        raise HTTPException(status_code=503, detail="SharePoint-integraatio ei ole konfiguroitu")

    target_dir = str(UPLOAD_DIR / subfolder) if subfolder else str(UPLOAD_DIR)
    results = []
    errors = []
    for path in paths:
        try:
            result = await sp.download_file_to_disk(
                path, target_dir,
                user_name=user.name, user_email=user.email,
            )
            results.append(result)
            logger.info("SharePoint pull: %s -> %s", path, result["target_path"])
        except Exception as e:
            logger.error("SharePoint pull epäonnistui: %s – %s", path, e)
            errors.append({"path": path, "error": str(e)})

    return {
        "downloaded": results,
        "errors": errors,
        "target_dir": target_dir,
    }


@app.post("/sharepoint/upload", summary="Lataa tiedosto SharePointiin")
async def sharepoint_upload(
    file: UploadFile = File(...),
    folder: Optional[str] = Form(None, description="Kohdekansio (oletus: SHAREPOINT_FOLDER)"),
    user: CurrentUser = Depends(require_admin),
):
    if not await sp.is_configured():
        raise HTTPException(status_code=503, detail="SharePoint-integraatio ei ole konfiguroitu")
    try:
        content = await file.read()
        result = await sp.upload_file(content, file.filename, folder, user_name=user.name, user_email=user.email)
        logger.info("SharePoint upload: %s (%d tavua)", file.filename, len(content))
        return result
    except Exception as e:
        logger.error("SharePoint upload epäonnistui: %s", e)
        raise HTTPException(status_code=500, detail=f"SharePoint-virhe: {e}")


@app.delete("/sharepoint/delete", summary="Poista tiedosto SharePointista")
async def sharepoint_delete(
    path: str = Query(..., description="Tiedoston polku SharePointissa"),
    user: CurrentUser = Depends(require_admin),
):
    if not await sp.is_configured():
        raise HTTPException(status_code=503, detail="SharePoint-integraatio ei ole konfiguroitu")
    try:
        await sp.delete_file(path, user_name=user.name, user_email=user.email)
        logger.info("SharePoint delete: %s", path)
        return {"deleted": True, "path": path}
    except Exception as e:
        logger.error("SharePoint delete epäonnistui: %s", e)
        raise HTTPException(status_code=500, detail=f"SharePoint-virhe: {e}")


@app.post("/sharepoint/move", summary="Siirrä tiedosto SharePointissa")
async def sharepoint_move(
    source: str = Query(..., description="Lähdetiedoston polku"),
    dest_folder: str = Query(..., description="Kohdekansion polku"),
    new_name: Optional[str] = Query(None, description="Uusi tiedostonimi (valinnainen)"),
    user: CurrentUser = Depends(require_admin),
):
    if not await sp.is_configured():
        raise HTTPException(status_code=503, detail="SharePoint-integraatio ei ole konfiguroitu")
    try:
        result = await sp.move_file(source, dest_folder, new_name, user_name=user.name, user_email=user.email)
        logger.info("SharePoint move: %s -> %s", source, dest_folder)
        return result
    except Exception as e:
        logger.error("SharePoint move epäonnistui: %s", e)
        raise HTTPException(status_code=500, detail=f"SharePoint-virhe: {e}")


@app.post("/sharepoint/folder", summary="Luo kansio SharePointiin")
async def sharepoint_create_folder(
    path: str = Query(..., description="Luotavan kansion polku (esim. Shared Documents/JKR-output/2024)"),
    user: CurrentUser = Depends(require_admin),
):
    if not await sp.is_configured():
        raise HTTPException(status_code=503, detail="SharePoint-integraatio ei ole konfiguroitu")
    try:
        result = await sp.create_folder(path, user_name=user.name, user_email=user.email)
        logger.info("SharePoint folder created: %s", path)
        return result
    except Exception as e:
        logger.error("SharePoint folder creation epäonnistui: %s", e)
        raise HTTPException(status_code=500, detail=f"SharePoint-virhe: {e}")


# ---------------------------------------------------------------------------
# Staattisten tiedostojen tarjoilu (HUOM: tämä pitää olla viimeisenä,
# jotta API-reitit ovat prioriteetissa)
# ---------------------------------------------------------------------------
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

# ---------------------------------------------------------------------------
# Käynnistys
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("jkrimporter.api.api:app", host="0.0.0.0", port=8000, reload=True)
