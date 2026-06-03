import logging
import os
import re
from datetime import date, datetime, time
from typing import Any, Optional, Sequence

from pydantic import BaseModel, Field
from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from jkrimporter.providers.db.database import engine
from jkrimporter.providers.db.models import Kompostori, Kuljetus, Viranomaispaatokset

logger = logging.getLogger("jkr-dashboard")

_LIETE_JATETYYPPI_IDS = (5, 6, 7)
_RECENT_EVENTS_LIMIT = 10
_LOG_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:,\d+)? \[[A-Z]+\]\s*")
_FILEINFO_FILENAME_RE = re.compile(r"filename='([^']+)'")
_FILEINFO_FILETYPE_RE = re.compile(r"fileType=<FileType\.[^:]+: '([^']+)'>")
_DATE_RANGE_RE = re.compile(r"\((?:[^\s)]+\s+)?(\d{4}-\d{2}-\d{2})-(\d{4}-\d{2}-\d{2})\)")
_REPORT_OUTPUT_RE = re.compile(r"Raportti luotu onnistuneesti:\s+(.+)$")


def _strip_log_prefix(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    return _LOG_PREFIX_RE.sub("", text).strip()


def _quarter_label_from_dates(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    match = _DATE_RANGE_RE.search(text)
    if not match:
        return None
    try:
        start = date.fromisoformat(match.group(1))
        end = date.fromisoformat(match.group(2))
    except ValueError:
        return None

    quarter = ((start.month - 1) // 3) + 1
    expected_end_month = quarter * 3
    if start.month != (expected_end_month - 2) or start.day != 1:
        return None
    if end.month != expected_end_month:
        return None
    if start.year != end.year:
        return None
    return f"Q{quarter}/{start.year}"


def _title_case_label(value: str) -> str:
    cleaned = value.replace("_", " ").replace("-", " ").strip()
    if not cleaned:
        return value
    return cleaned[0].upper() + cleaned[1:]


def _import_subject_from_description(description: Optional[str], command: Optional[str]) -> Optional[str]:
    text = f"{description or ''}\n{command or ''}"
    quarter_label = _quarter_label_from_dates(description) or _quarter_label_from_dates(command)

    if "Kohteiden luonti DVV-aineistosta" in text or "create_dvv_kohteet" in text:
        return f"DVV-aineisto ({quarter_label})" if quarter_label else "DVV-aineisto"
    if "LIETE-kuljetustietojen tuonti" in text or "Liete_kuljetustiedot" in text:
        return f"LIETE-kuljetustiedot ({quarter_label})" if quarter_label else "LIETE-kuljetustiedot"
    if "Kuljetustietojen tuonti" in text or "Kiintea_kuljetustiedot" in text:
        return f"Kuljetustiedot ({quarter_label})" if quarter_label else "Kuljetustiedot"
    if "Päätösten tuonti" in text:
        return f"Päätöstiedot ({quarter_label})" if quarter_label else "Päätöstiedot"
    if "Liete kompostointi-ilmoitusten tuonti" in text:
        return f"Lietteen kompostointi-ilmoitukset ({quarter_label})" if quarter_label else "Lietteen kompostointi-ilmoitukset"
    if "Kompostointi-ilmoitusten tuonti" in text:
        return f"Kompostointi-ilmoitukset ({quarter_label})" if quarter_label else "Kompostointi-ilmoitukset"
    if "Lopetusilmoitusten tuonti" in text:
        return f"Lopetusilmoitukset ({quarter_label})" if quarter_label else "Lopetusilmoitukset"
    if "Kaivotietojen tuonti" in text:
        return f"Kaivotiedot ({quarter_label})" if quarter_label else "Kaivotiedot"
    if "Kaivotiedon lopetusten tuonti" in text:
        return f"Kaivotiedon lopetukset ({quarter_label})" if quarter_label else "Kaivotiedon lopetukset"
    if "Viemäritietojen tuonti" in text:
        return f"Viemäritiedot ({quarter_label})" if quarter_label else "Viemäritiedot"
    if "Viemärin lopetusten tuonti" in text:
        return f"Viemärin lopetukset ({quarter_label})" if quarter_label else "Viemärin lopetukset"
    if "Taajamarajausten tuonti" in text:
        return f"Taajamarajaukset ({quarter_label})" if quarter_label else "Taajamarajaukset"
    if "Viemäriverkoston tuonti" in text:
        return f"Viemäriverkosto ({quarter_label})" if quarter_label else "Viemäriverkosto"
    if "Tietojen joukko tuonti" not in (description or ""):
        return None

    filenames = _FILEINFO_FILENAME_RE.findall(description or "")
    filetypes = _FILEINFO_FILETYPE_RE.findall(description or "")
    labels = filenames or filetypes
    if not labels:
        return "Aineisto"

    pretty_labels = [_title_case_label(label) for label in labels]
    if len(pretty_labels) == 1:
        return pretty_labels[0]
    return f"{pretty_labels[0]} + {len(pretty_labels) - 1} muuta"


def _format_event_title(task: Any) -> str:
    description = getattr(task, "description", None) or ""
    command = getattr(task, "command", None) or ""
    task_type = getattr(task, "taskType", None)

    if "Velvoite-statuksen tallennus" in description:
        return "Velvoitetarkistus ajettu"
    if description == "Velvoitteiden päivitys":
        return "Velvoitteet päivitetty"
    if task_type == "report":
        return "Raportti generoitu"
    if task_type == "import":
        subject = _import_subject_from_description(description, command)
        if subject:
            return f"{subject} tuotu"

    return description or command or "Järjestelmätapahtuma"


def _is_technical_detail(text: str) -> bool:
    if not text:
        return False
    if text == "VALMIS!":
        return True
    if text == "(1 row)":
        return True
    if "TyhjennysSopimus(" in text:
        return True
    if "FileInfo(" in text:
        return True
    return False


def _format_event_detail(task: Any) -> Optional[str]:
    detail = _strip_log_prefix(_task_detail(task))
    if not detail:
        return None
    if _is_technical_detail(detail):
        return None

    report_match = _REPORT_OUTPUT_RE.search(detail)
    if report_match:
        output_path = report_match.group(1).strip()
        return f"Tiedosto: {os.path.basename(output_path)}"

    if detail == "Tehtävä pysäytettiin käyttäjän pyynnöstä.":
        return detail

    if len(detail) > 180:
        return None

    return detail


class DashboardSummaryItem(BaseModel):
    occurred_at: Optional[datetime] = None
    status: Optional[str] = None
    detail: Optional[str] = None
    runner: Optional[str] = None


class DashboardEventItem(BaseModel):
    id: str
    title: str
    status: Optional[str] = None
    taskType: str
    occurred_at: Optional[datetime] = None
    detail: Optional[str] = None
    runner: Optional[str] = None


class DashboardOverviewResponse(BaseModel):
    velvoitetarkistus_ajettu: DashboardSummaryItem
    viimeisin_raportti_generoitu: DashboardSummaryItem
    uusin_paatos_kannassa: DashboardSummaryItem
    uusin_kompostointi_ilmoitus: DashboardSummaryItem
    lietekuljetus_viimeisin_tyhjennys: DashboardSummaryItem
    kiintea_kuljetus_viimeisin_kvartaali: DashboardSummaryItem
    viimeisin_tuonti: DashboardSummaryItem
    viimeisimmat_jarjestelmatapahtumat: list[DashboardEventItem] = Field(default_factory=list)


def _as_datetime(value: Optional[date | datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.combine(value, time.min)


def _task_status_value(task: Any) -> Optional[str]:
    status = getattr(task, "status", None)
    if status is None:
        return None
    return getattr(status, "value", str(status))


def _task_occurred_at(task: Any) -> Optional[datetime]:
    return getattr(task, "finished_at", None) or getattr(task, "started_at", None)


def _last_non_empty_line(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    for line in reversed(text.splitlines()):
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _task_detail(task: Any) -> Optional[str]:
    status = _task_status_value(task)
    if status == "failed":
        return (
            _last_non_empty_line(getattr(task, "error", None))
            or _last_non_empty_line(getattr(task, "output", None))
            or getattr(task, "description", None)
        )
    return (
        _last_non_empty_line(getattr(task, "output", None))
        or _last_non_empty_line(getattr(task, "error", None))
        or getattr(task, "description", None)
    )


def _empty_summary() -> DashboardSummaryItem:
    return DashboardSummaryItem()


def _task_to_summary(task: Optional[Any]) -> DashboardSummaryItem:
    if task is None:
        return _empty_summary()
    return DashboardSummaryItem(
        occurred_at=_task_occurred_at(task),
        status=_task_status_value(task),
        detail=_task_detail(task),
        runner=getattr(task, "runner", None),
    )


def _db_date_to_summary(value: Optional[date | datetime]) -> DashboardSummaryItem:
    return DashboardSummaryItem(occurred_at=_as_datetime(value))


def _latest_matching_task(tasks: Sequence[Any], predicate) -> Optional[Any]:
    matching_tasks = [task for task in tasks if predicate(task)]
    if not matching_tasks:
        return None
    matching_tasks.sort(key=lambda task: _task_occurred_at(task) or datetime.min, reverse=True)
    return matching_tasks[0]


def _recent_task_events(tasks: Sequence[Any], limit: int = _RECENT_EVENTS_LIMIT) -> list[DashboardEventItem]:
    ordered_tasks = sorted(
        (task for task in tasks if _task_occurred_at(task) is not None),
        key=lambda task: _task_occurred_at(task) or datetime.min,
        reverse=True,
    )
    return [
        DashboardEventItem(
            id=str(getattr(task, "id", "")),
            title=_format_event_title(task),
            status=_task_status_value(task),
            taskType=getattr(task, "taskType", "unknown") or "unknown",
            occurred_at=_task_occurred_at(task),
            detail=_format_event_detail(task),
            runner=getattr(task, "runner", None),
        )
        for task in ordered_tasks[:limit]
    ]


def _safe_session_date(statement, value_getter=None) -> Optional[date | datetime]:
    try:
        with Session(engine) as session:
            result = session.execute(statement).first()
            if result is None:
                return None
            if value_getter is not None:
                return value_getter(result)
            return result[0]
    except Exception as exc:
        logger.warning("Dashboard-kysely epäonnistui: %s", exc)
        return None


def _latest_paatos_date() -> Optional[date | datetime]:
    statement = (
        select(Viranomaispaatokset.alkupvm)
        .where(Viranomaispaatokset.alkupvm.is_not(None))
        .order_by(desc(Viranomaispaatokset.alkupvm))
        .limit(1)
    )
    return _safe_session_date(statement)


def _latest_kompostointi_date() -> Optional[date | datetime]:
    statement = (
        select(Kompostori.alkupvm)
        .where(
            Kompostori.alkupvm.is_not(None),
            or_(Kompostori.onko_liete.is_(False), Kompostori.onko_liete.is_(None)),
        )
        .order_by(desc(Kompostori.alkupvm))
        .limit(1)
    )
    return _safe_session_date(statement)


def _latest_liete_tyhjennys_date() -> Optional[date | datetime]:
    statement = (
        select(Kuljetus.lietteentyhjennyspaiva)
        .where(
            Kuljetus.lietteentyhjennyspaiva.is_not(None),
            Kuljetus.jatetyyppi_id.in_(_LIETE_JATETYYPPI_IDS),
        )
        .order_by(desc(Kuljetus.lietteentyhjennyspaiva))
        .limit(1)
    )
    return _safe_session_date(statement)


def _latest_kiintea_kuljetus_date() -> Optional[date | datetime]:
    statement = (
        select(Kuljetus.loppupvm, Kuljetus.alkupvm)
        .where(
            ~Kuljetus.jatetyyppi_id.in_(_LIETE_JATETYYPPI_IDS),
            or_(Kuljetus.loppupvm.is_not(None), Kuljetus.alkupvm.is_not(None)),
        )
        .order_by(desc(Kuljetus.loppupvm), desc(Kuljetus.alkupvm))
        .limit(1)
    )
    return _safe_session_date(statement, value_getter=lambda row: row[0] or row[1])


def build_dashboard_overview(tasks: Sequence[Any]) -> DashboardOverviewResponse:
    return DashboardOverviewResponse(
        velvoitetarkistus_ajettu=_task_to_summary(
            _latest_matching_task(tasks, lambda task: "tallenna_velvoite_status" in (getattr(task, "command", "") or ""))
        ),
        viimeisin_raportti_generoitu=_task_to_summary(
            _latest_matching_task(tasks, lambda task: getattr(task, "taskType", None) == "report")
        ),
        uusin_paatos_kannassa=_db_date_to_summary(_latest_paatos_date()),
        uusin_kompostointi_ilmoitus=_db_date_to_summary(_latest_kompostointi_date()),
        lietekuljetus_viimeisin_tyhjennys=_db_date_to_summary(_latest_liete_tyhjennys_date()),
        kiintea_kuljetus_viimeisin_kvartaali=_db_date_to_summary(_latest_kiintea_kuljetus_date()),
        viimeisin_tuonti=_task_to_summary(
            _latest_matching_task(tasks, lambda task: getattr(task, "taskType", None) == "import")
        ),
        viimeisimmat_jarjestelmatapahtumat=_recent_task_events(tasks),
    )
