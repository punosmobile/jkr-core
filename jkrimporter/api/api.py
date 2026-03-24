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
import json
import logging
import os
import subprocess
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from jkrimporter import ws_log_handler

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


async def _run_task(task_id: str, command: str, cwd: Optional[str] = None):
    """Suorittaa komennon taustalla ja päivittää tehtävän tilan."""
    task = _tasks[task_id]
    task.status = TaskStatus.running
    task.started_at = datetime.now()

    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_db_env(),
            cwd=cwd,
        )
        stdout, stderr = await proc.communicate()

        task.exit_code = proc.returncode
        task.output = stdout.decode("utf-8", errors="replace")
        task.error = stderr.decode("utf-8", errors="replace")
        task.status = TaskStatus.completed if proc.returncode == 0 else TaskStatus.failed
    except Exception as e:
        task.status = TaskStatus.failed
        task.error = str(e)
    finally:
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
async def list_tasks():
    return list(_tasks.values())


@app.get("/tasks/{task_id}", summary="Hae tehtävän tila", response_model=TaskInfo)
async def get_task(task_id: str):
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="Tehtävää ei löydy")
    return _tasks[task_id]


# ---------------------------------------------------------------------------
# Endpointit: jkr CLI -komennot
# ---------------------------------------------------------------------------
@app.post("/jkr/import", summary="jkr import – Kuljetustietojen tuonti", response_model=TaskResponse)
async def jkr_import(req: JkrImportRequest, background_tasks: BackgroundTasks):
    cmd = f"jkr import {req.siirtotiedosto} {req.tiedontuottajatunnus} {req.alkupvm} {req.loppupvm}"
    task = _create_task(cmd, f"Kuljetustietojen tuonti ({req.tiedontuottajatunnus} {req.alkupvm}-{req.loppupvm})")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/jkr/import_liete", summary="jkr import_liete – LIETE-kuljetustietojen tuonti", response_model=TaskResponse)
async def jkr_import_liete(req: JkrImportLieteRequest, background_tasks: BackgroundTasks):
    cmd = f"jkr import_liete {req.siirtotiedosto} {req.tiedontuottajatunnus} {req.alkupvm} {req.loppupvm}"
    task = _create_task(cmd, f"LIETE-kuljetustietojen tuonti ({req.alkupvm}-{req.loppupvm})")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/jkr/import_paatokset", summary="jkr import_paatokset – Päätösten tuonti", response_model=TaskResponse)
async def jkr_import_paatokset(req: JkrImportPaatoksetRequest, background_tasks: BackgroundTasks):
    cmd = f"jkr import_paatokset {req.siirtotiedosto}"
    task = _create_task(cmd, "Päätösten tuonti")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/jkr/import_ilmoitukset", summary="jkr import_ilmoitukset – Ilmoitusten tuonti", response_model=TaskResponse)
async def jkr_import_ilmoitukset(req: JkrImportIlmoituksetRequest, background_tasks: BackgroundTasks):
    cmd = f"jkr import_ilmoitukset {req.siirtotiedosto}"
    task = _create_task(cmd, "Kompostointi-ilmoitusten tuonti")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/jkr/import_liete_ilmoitukset", summary="jkr import_liete_ilmoitukset – Liete-ilmoitusten tuonti", response_model=TaskResponse)
async def jkr_import_liete_ilmoitukset(req: JkrImportLieteIlmoituksetRequest, background_tasks: BackgroundTasks):
    cmd = f"jkr import_liete_ilmoitukset {req.siirtotiedosto}"
    task = _create_task(cmd, "Liete kompostointi-ilmoitusten tuonti")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/jkr/import_lopetusilmoitukset", summary="jkr import_lopetusilmoitukset – Lopetusilmoitusten tuonti", response_model=TaskResponse)
async def jkr_import_lopetusilmoitukset(req: JkrImportLopetusilmoituksetRequest, background_tasks: BackgroundTasks):
    cmd = f"jkr import_lopetusilmoitukset {req.siirtotiedosto}"
    task = _create_task(cmd, "Lopetusilmoitusten tuonti")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/jkr/import_kaivotiedot", summary="jkr import_kaivotiedot – Kaivotietojen tuonti", response_model=TaskResponse)
async def jkr_import_kaivotiedot(req: JkrImportKaivotiedotRequest, background_tasks: BackgroundTasks):
    cmd = f"jkr import_kaivotiedot {req.siirtotiedosto} {req.tiedontuottajatunnus}"
    task = _create_task(cmd, "Kaivotietojen tuonti")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/jkr/import_kaivotiedon_lopetukset", summary="jkr import_kaivotiedon_lopetukset – Kaivotiedon lopetusten tuonti", response_model=TaskResponse)
async def jkr_import_kaivotiedon_lopetukset(req: JkrImportKaivotiedonLopetuksetRequest, background_tasks: BackgroundTasks):
    cmd = f"jkr import_kaivotiedon_lopetukset {req.siirtotiedosto} {req.tiedontuottajatunnus}"
    task = _create_task(cmd, "Kaivotiedon lopetusten tuonti")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/jkr/import_viemarit", summary="jkr import_viemarit – Viemäritietojen tuonti", response_model=TaskResponse)
async def jkr_import_viemarit(req: JkrImportViemaritRequest, background_tasks: BackgroundTasks):
    cmd = f"jkr import_viemarit {req.siirtotiedosto}"
    task = _create_task(cmd, "Viemäritietojen tuonti")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/jkr/import_lopeta_viemarit", summary="jkr import_lopeta_viemarit – Viemärin lopetusten tuonti", response_model=TaskResponse)
async def jkr_import_lopeta_viemarit(req: JkrImportLopetaViemaritRequest, background_tasks: BackgroundTasks):
    cmd = f"jkr import_lopeta_viemarit {req.siirtotiedosto}"
    task = _create_task(cmd, "Viemärin lopetusten tuonti")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/jkr/create_dvv_kohteet", summary="jkr create_dvv_kohteet – Kohteiden luonti DVV-aineistosta", response_model=TaskResponse)
async def jkr_create_dvv_kohteet(req: JkrCreateDvvKohteetRequest, background_tasks: BackgroundTasks):
    cmd = f"jkr create_dvv_kohteet {req.poimintapvm}"
    if req.perusmaksutiedosto:
        cmd += f" {req.perusmaksutiedosto}"
    task = _create_task(cmd, "Kohteiden luonti DVV-aineistosta")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/jkr/tiedontuottaja/add", summary="jkr tiedontuottaja add – Lisää tiedontuottaja", response_model=TaskResponse)
async def jkr_tiedontuottaja_add(req: TiedontuottajaAddRequest, background_tasks: BackgroundTasks):
    cmd = f"jkr tiedontuottaja add {req.tunnus} '{req.nimi}'"
    task = _create_task(cmd, f"Tiedontuottajan lisäys: {req.tunnus}")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.get("/jkr/tiedontuottaja/list", summary="jkr tiedontuottaja list – Listaa tiedontuottajat")
async def jkr_tiedontuottaja_list():
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
async def psql_exec(req: PsqlRequest, background_tasks: BackgroundTasks):
    if not req.sql and not req.file:
        raise HTTPException(status_code=400, detail="Anna joko 'sql' tai 'file'")
    cmd = _psql_cmd(sql=req.sql, file=req.file)
    desc = f"psql: {req.sql or req.file}"
    task = _create_task(cmd, desc)
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/psql/copy_csv", summary="psql \\copy CSV-tiedostosta", response_model=TaskResponse)
async def psql_copy_csv(req: CopyFromCsvRequest, background_tasks: BackgroundTasks):
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
async def psql_update_velvoitteet(background_tasks: BackgroundTasks):
    cmd = _psql_cmd(sql="SELECT jkr.update_velvoitteet();")
    task = _create_task(cmd, "Velvoitteiden päivitys")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/psql/tallenna_velvoite_status", summary="Velvoite-statuksen tallennus", response_model=TaskResponse)
async def psql_tallenna_velvoite_status(req: TallennaVelvoiteStatusRequest, background_tasks: BackgroundTasks):
    cmd = _psql_cmd(sql=f"SELECT jkr.tallenna_velvoite_status('{req.pvm}');")
    task = _create_task(cmd, f"Velvoite-statuksen tallennus ({req.pvm})")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


# ---------------------------------------------------------------------------
# Endpointit: ogr2ogr (DVV-aineiston tuonti)
# ---------------------------------------------------------------------------
@app.post("/ogr2ogr/import", summary="ogr2ogr – Tuo aineisto PostgreSQL:ään", response_model=TaskResponse)
async def ogr2ogr_import(req: Ogr2ogrRequest, background_tasks: BackgroundTasks):
    cmd = _ogr2ogr_cmd(req.source_file, req.layer_name, req.target_table, req.target_schema)
    task = _create_task(cmd, f"ogr2ogr: {req.layer_name} → {req.target_schema}.{req.target_table}")
    background_tasks.add_task(_run_task, task.id, cmd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


# ---------------------------------------------------------------------------
# Endpointit: Shell-skriptit
# ---------------------------------------------------------------------------
@app.post("/scripts/import_taajama", summary="Taajamarajausten tuonti (import_taajama.sh)", response_model=TaskResponse)
async def scripts_import_taajama(req: ImportTaajamaRequest, background_tasks: BackgroundTasks):
    cmd = f"sh import_taajama.sh {req.alkupvm}"
    task = _create_task(cmd, f"Taajamarajausten tuonti ({req.alkupvm})")
    background_tasks.add_task(_run_task, task.id, cmd, cwd=str(SCRIPTS_DIR))
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/scripts/import_viemari", summary="Viemäriverkoston tuonti (import_viemari.sh)", response_model=TaskResponse)
async def scripts_import_viemari(req: ImportViemariRequest, background_tasks: BackgroundTasks):
    cmd = f"sh import_viemari.sh {req.alkupvm} {req.shp_tiedosto}"
    task = _create_task(cmd, f"Viemäriverkoston tuonti ({req.alkupvm})")
    background_tasks.add_task(_run_task, task.id, cmd, cwd=str(SCRIPTS_DIR))
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


@app.post("/scripts/run", summary="Aja mikä tahansa shell-skripti", response_model=TaskResponse)
async def scripts_run(req: ShellScriptRequest, background_tasks: BackgroundTasks):
    args_str = " ".join(req.args)
    cmd = f"sh {req.script} {args_str}".strip()
    task = _create_task(cmd, f"Skripti: {req.script}")
    background_tasks.add_task(_run_task, task.id, cmd, cwd=str(SCRIPTS_DIR))
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


# ---------------------------------------------------------------------------
# Endpointit: Koko pipeline
# ---------------------------------------------------------------------------
@app.post("/pipeline/run", summary="Aja koko tuontiskripti (esim. 2024_start.sh)", response_model=TaskResponse)
async def pipeline_run(req: RunFullPipelineRequest, background_tasks: BackgroundTasks):
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
async def command_run(req: GenericCommandRequest, background_tasks: BackgroundTasks):
    task = _create_task(req.command, req.description)
    background_tasks.add_task(_run_task, task.id, req.command, cwd=req.cwd)
    return TaskResponse(task_id=task.id, status=task.status, description=task.description)


# ---------------------------------------------------------------------------
# Tietokantadokumentaatio
# ---------------------------------------------------------------------------
@app.get("/db/documentation", summary="Tietokantadokumentaatio (jkr-skeemat)")
async def db_documentation():
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
# Health check
# ---------------------------------------------------------------------------
@app.get("/health", summary="Terveystarkistus")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# ---------------------------------------------------------------------------
# WebSocket: Reaaliaikainen loki
# ---------------------------------------------------------------------------
@app.websocket("/ws/logs")
async def ws_logs(websocket: WebSocket):
    """
    WebSocket-endpoint reaaliaikaiselle lokille.

    Yhdistettäessä lähetetään ensin viimeisimmät puskuroidut viestit (max 500),
    jonka jälkeen uudet viestit streamataan reaaliajassa.

    Client voi lähettää JSON-viestin log-tason suodattamiseksi:
        {"min_level": 25}   # näytä vain IMPORT (25) ja sitä vakavammat
    """
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
