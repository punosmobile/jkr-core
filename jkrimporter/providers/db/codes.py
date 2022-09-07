import logging
from enum import Enum
from functools import lru_cache
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.exc import NoResultFound

from jkrimporter.model import Jatelaji
from jkrimporter.model import KeraysvalineTyyppi as KeraysvalineTyyppiEnum
from jkrimporter.model import SopimusTyyppi as SopimusTyyppiEnum

from .models import (
    Jatetyyppi,
    Keraysvalinetyyppi,
    Kohdetyyppi,
    Osapuolenlaji,
    Osapuolenrooli,
    Rakennuksenkayttotarkoitus,
    SopimusTyyppi,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


@lru_cache(maxsize=32)
def get_code_id(session: "Session", model, selite: str):
    statement = select(model).where(model.selite == selite)
    result = session.execute(statement)
    try:
        return result.scalar_one()
    except NoResultFound:
        return None


class KohdeTyyppi(Enum):
    ALUEKERAYS = "aluekeräys"
    LAHIKERAYS = "lähikeräys"
    PUTKIKERAYS = "putkikeräys"
    KIINTEISTO = "kiinteistö"


class OsapuolenlajiTyyppi(Enum):
    ASOY = "Asunto-oy tai asunto-osuuskunta"
    JULKINEN = "Valtio- tai kuntaenemmistöinen yritys"


class OsapuolenrooliTyyppi(Enum):
    ASIAKAS = "Asiakas"
    YHTEYSTIETO = "Yhteystieto"


class RakennuksenKayttotarkoitusTyyppi(Enum):
    PARITALO = "Kahden asunnon talot"


def _init_lookup_codes(session, model, enumtype: Enum):
    codes = {enum: get_code_id(session, model, enum.value) for enum in enumtype}

    return codes


kohdetyypit = {}
osapuolenlajit = {}
jatetyypit = {}
osapuolenroolit = {}
rakennuksenkayttotarkoitukset = {}
sopimustyypit = {}
keraysvalinetyypit = {}


def init_code_objects(session):
    global rakennuksenkayttotarkoitukset
    rakennuksenkayttotarkoitukset = _init_lookup_codes(
        session, Rakennuksenkayttotarkoitus, RakennuksenKayttotarkoitusTyyppi
    )

    global kohdetyypit
    # TODO: vaihda nimeksi KohdeTyyppiEnum
    kohdetyypit = _init_lookup_codes(session, Kohdetyyppi, KohdeTyyppi)

    global osapuolenlajit
    osapuolenlajit = _init_lookup_codes(session, Osapuolenlaji, OsapuolenlajiTyyppi)

    global jatetyypit
    jatetyypit = _init_lookup_codes(session, Jatetyyppi, Jatelaji)

    global osapuolenroolit
    osapuolenroolit = _init_lookup_codes(session, Osapuolenrooli, OsapuolenrooliTyyppi)

    global sopimustyypit
    sopimustyypit = _init_lookup_codes(session, SopimusTyyppi, SopimusTyyppiEnum)

    global keraysvalinetyypit
    keraysvalinetyypit = _init_lookup_codes(
        session, Keraysvalinetyyppi, KeraysvalineTyyppiEnum
    )
