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
    Rakennuksenolotila,
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
    # Definitions at https://github.com/GispoCoding/jkr-lahti/issues/96
    OMISTAJA = "Omistaja"
    VANHIN_ASUKAS = "Vanhin asukas"
    SEKAJATE_TILAAJA = "Tilaaja sekajäte"
    BIOJATE_TILAAJA = "Tilaaja biojäte"
    MUOVI_TILAAJA = "Tilaaja muovipakkaus"
    KARTONKI_TILAAJA = "Tilaaja kartonkipakkaus"
    LASI_TILAAJA = "Tilaaja lasipakkaus"
    METALLI_TILAAJA = "Tilaaja metalli"
    MONILOKERO_TILAAJA = "Tilaaja monilokero"
    LIETE_TILAAJA = "Tilaaja liete"
    SEKAJATE_KIMPPAISANTA = "Kimppaisäntä sekajäte"
    BIOJATE_KIMPPAISANTA = "Kimppaisäntä biojäte"
    MUOVI_KIMPPAISANTA = "Kimppaisäntä muovipakkaus"
    KARTONKI_KIMPPAISANTA = "Kimppaisäntä kartonkipakkaus"
    LASI_KIMPPAISANTA = "Kimppaisäntä lasipakkaus"
    METALLI_KIMPPAISANTA = "Kimppaisäntä metalli"
    SEKAJATE_KIMPPAOSAKAS = "Kimppaosakas sekajäte"
    BIOJATE_KIMPPAOSAKAS = "Kimppaosakas biojäte"
    MUOVI_KIMPPAOSAKAS = "Kimppaosakas muovipakkaus"
    KARTONKI_KIMPPAOSAKAS = "Kimppaosakas kartonkipakkaus"
    LASI_KIMPPAOSAKAS = "Kimppaosakas lasipakkaus"
    METALLI_KIMPPAOSAKAS = "Kimppaosakas metalli"


class RakennuksenKayttotarkoitusTyyppi(Enum):
    YKSITTAISTALO = "Yhden asunnon talot"
    PARITALO = "Kahden asunnon talot"
    MUU_PIENTALO = "Muut erilliset pientalot"
    RIVITALO = "Rivitalot"
    KETJUTALO = "Ketjutalot"
    LUHTITALO = "Luhtitalot"
    KERROSTALO = "Muut asuinkerrostalot"
    VAPAA_AJANASUNTO = "Vapaa-ajan asuinrakennukset"
    MUU_ASUNTOLA = "Muut asuntolarakennukset"
    VANHAINKOTI = "Vanhainkodit"
    LASTENKOTI = "Lasten- ja koulukodit"
    KEHITYSVAMMAHOITOLAITOS = "Kehitysvammaisten hoitolaitokset"
    MUU_HUOLTOLAITOS = "Muut huoltolaitosrakennukset"
    PAIVAKOTI = "Lasten päiväkodit"
    MUU_SOSIAALITOIMEN_RAKENNUS = (
        "Muualla luokittelemattomat sosiaalitoimen rakennukset"
    )
    YLEISSIVISTAVA_OPPILAITOS = "Yleissivistävien oppilaitosten rakennukset"
    AMMATILLINEN_OPPILAITOS = "Ammatillisten oppilaitosten rakennukset"
    KORKEAKOULU = "Korkeakoulurakennukset"
    TUTKIMUSLAITOS = "Tutkimuslaitosrakennukset"
    OPETUSRAKENNUS = "Järjestöjen, liittojen, työnantajien yms. opetusrakennukset"
    MUU_OPETUSRAKENNUS = "Muualla luokittelemattomat opetusrakennukset"
    SAUNA = "Saunarakennukset"
    TALOUSRAKENNUS = "Talousrakennukset"


class RakennuksenOlotilaTyyppi(Enum):
    MUU = "muu (sauna, liiteri, kellotapuli, ym.)"
    TYHJILLAAN = "tyhjillään (esim. myynnissä)"


def _init_lookup_codes(session, model, enumtype: Enum):
    codes = {enum: get_code_id(session, model, enum.value) for enum in enumtype}

    return codes


kohdetyypit = {}
osapuolenlajit = {}
jatetyypit = {}
osapuolenroolit = {}
rakennuksenkayttotarkoitukset = {}
rakennuksenolotilat = {}
sopimustyypit = {}
keraysvalinetyypit = {}


def init_code_objects(session):
    global rakennuksenkayttotarkoitukset
    rakennuksenkayttotarkoitukset = _init_lookup_codes(
        session, Rakennuksenkayttotarkoitus, RakennuksenKayttotarkoitusTyyppi
    )
    global rakennuksenolotilat
    rakennuksenolotilat = _init_lookup_codes(
        session, Rakennuksenolotila, RakennuksenOlotilaTyyppi
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
