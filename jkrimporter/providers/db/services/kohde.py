from dataclasses import dataclass
import datetime
import re
import logging
from collections import defaultdict
from datetime import date, datetime as dt
from datetime import timedelta
from functools import lru_cache
from typing import TypeVar, DefaultDict, Set, List, Dict,TYPE_CHECKING,NamedTuple, FrozenSet, Optional, Generic, Iterable, Callable

from openpyxl import load_workbook
from psycopg2.extras import DateRange
from sqlalchemy import and_, exists, or_, select, update, case, delete, func, text
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm.decl_api import DeclarativeMeta
from sqlalchemy.orm import Session
from pathlib import Path

from jkrimporter.model import Asiakas, JkrIlmoitukset, LopetusIlmoitus, Yhteystieto

from .. import codes
from ..codes import KohdeTyyppi, OsapuolenrooliTyyppi, RakennuksenKayttotarkoitusTyyppi
from ..models import (
    Katu,
    Kohde,
    KohteenOsapuolet,
    KohteenRakennukset,
    Kompostori,
    KompostorinKohteet,
    Kuljetus,
    Osapuoli,
    Osoite,
    RakennuksenOmistajat,
    RakennuksenVanhimmat,
    Rakennus,
    Sopimus,
    UlkoinenAsiakastieto,
    Viranomaispaatokset,
)
from ..utils import clean_asoy_name, form_display_name, is_asoy, is_company, is_yhteiso
from .buildings import DISTANCE_LIMIT, create_nearby_buildings_lookup, minimum_distance_of_buildings

T = TypeVar('T')

if TYPE_CHECKING:
    from pathlib import Path
    from typing import (
        Callable,
        DefaultDict,
        Dict,
        FrozenSet,
        Hashable,
        List,
        NamedTuple,
        Optional,
        Set,
        Tuple,
        Union,
    )

    from sqlalchemy.orm import Session
    from sqlalchemy.sql.selectable import Select

    from jkrimporter.model import Asiakas, JkrIlmoitukset, Tunnus

    class Kohdetiedot(NamedTuple):
        kohde: Kohde
        rakennukset: FrozenSet[KohteenRakennukset]
        lisarakennukset: FrozenSet[KohteenRakennukset]
        asukkaat: FrozenSet[KohteenOsapuolet]
        omistajat: FrozenSet[KohteenOsapuolet]

@dataclass
class BuildingInfo:
    """Apurakennuksen tiedot"""
    id: int
    prt: str
    owner_ids: Set[int]
    address_ids: Set[tuple]  # (katu_id, osoitenumero)
    is_auxiliary: bool


class BatchProgressTracker(Generic[T]):
    """
    Seuraa eräajon edistymistä ja tulostaa säännöllisiä tilannepäivityksiä.
    """
    def __init__(self, total: int, operation_name: str, update_interval: int = 1):
        self.total = total
        self.current = 0
        self.start_time = dt.now()
        self.last_update = self.start_time
        self.operation_name = operation_name
        self.update_interval = update_interval
        self.logger = logging.getLogger(__name__)
        
        # Tulosta aloitusviesti
        self.logger.info(f"\nAloitetaan {operation_name}")
        self.logger.info(f"Käsitellään yhteensä {total:,} kohdetta")

    def update(self, increment: int = 1) -> None:
        """Päivitä laskuri ja tulosta edistyminen jos on kulunut tarpeeksi aikaa."""
        self.current += increment
        now = dt.now()
        
        if (now - self.last_update).seconds >= self.update_interval:
            self._print_progress(now)
            self.last_update = now

    def _print_progress(self, now: dt) -> None:
        elapsed = now - self.start_time
        if self.current > 0:
            items_per_second = self.current / elapsed.total_seconds()
            remaining_items = self.total - self.current
            eta = timedelta(seconds=int(remaining_items / items_per_second)) if items_per_second > 0 else "---"
        else:
            items_per_second = 0
            eta = "---"

        self.logger.info(
            f"{self.operation_name}: "
            f"({self.current:,}/{self.total:,}) "
            f"nopeudella {items_per_second:.1f}/s, "
            f"aikaa jäljellä {eta}"
        )

    def done(self) -> None:
        """Tulosta yhteenveto kun prosessi on valmis."""
        elapsed = dt.now() - self.start_time
        items_per_second = self.current / elapsed.total_seconds()
        
        self.logger.info(
            f"\n{self.operation_name} valmis!\n"
            f"Käsitelty {self.current:,} kohdetta, "
            f"aikaa kului {elapsed}, "
            f"keskimääräinen nopeus {items_per_second:.1f}/s"
        )


def process_with_progress(
    items: Iterable[T],
    operation_name: str,
    process_func: Callable[[T], None],
    total: Optional[int] = None
) -> None:
    """
    Kääre-funktio, joka prosessoi kokoelman ja näyttää edistymisen.
    
    Args:
        items: Käsiteltävä kokoelma
        operation_name: Operaation nimi logeissa
        process_func: Funktio joka käsittelee yhden kohteen
        total: Kohteiden kokonaismäärä (jos ei ole len(items))
    """
    if total is None:
        try:
            total = len(items)
        except TypeError:
            total = 0  # Jos kokoelman kokoa ei voi määrittää
            
    progress = BatchProgressTracker(total, operation_name)
    
    try:
        for item in items:
            process_func(item)
            progress.update()
    finally:
        progress.done()

class Rakennustiedot(NamedTuple):
    rakennus: 'Rakennus'
    vanhimmat: FrozenSet['RakennuksenVanhimmat']
    omistajat: FrozenSet['RakennuksenOmistajat'] 
    osoitteet: FrozenSet['Osoite']


separators = [r"\s\&\s", r"\sja\s"]
separator_regex = r"|".join(separators)


def match_name(first: str, second: str) -> bool:
    """
    Returns true if one name is subset of the other, i.e. the same name without extra
    parts. Consider typical separators combining names.
    """
    first = re.split(separator_regex, first)
    second = re.split(separator_regex, second)
    if len(first) > 1 or len(second) > 1:
        # TODO: if names have common surname, paste it to the name that is missing
        # surname. Will take some detective work tho.
        return any(
            match_name(first_name, second_name)
            for first_name in first
            for second_name in second
        )
    first_parts = set(first[0].lower().split())
    second_parts = set(second[0].lower().split())
    return first_parts.issubset(second_parts) or second_parts.issubset(first_parts)


def is_aluekerays(asiakas: "Asiakas") -> bool:
    return "aluejätepiste" in asiakas.haltija.nimi.lower()


def get_ulkoinen_asiakastieto(
    session: "Session", ulkoinen_tunnus: "Tunnus"
) -> "Union[UlkoinenAsiakastieto, None]":
    query = select(UlkoinenAsiakastieto).where(
        UlkoinenAsiakastieto.tiedontuottaja_tunnus == ulkoinen_tunnus.jarjestelma,
        UlkoinenAsiakastieto.ulkoinen_id == ulkoinen_tunnus.tunnus,
    )
    try:
        return session.execute(query).scalar_one()
    except NoResultFound:
        return None


def update_ulkoinen_asiakastieto(ulkoinen_asiakastieto, asiakas: "Asiakas"):
    if ulkoinen_asiakastieto.ulkoinen_asiakastieto != asiakas.ulkoinen_asiakastieto:
        ulkoinen_asiakastieto.ulkoinen_asiakastieto = asiakas.ulkoinen_asiakastieto


def find_kohde_by_prt(
    session: "Session", asiakas: "Union[Asiakas, JkrIlmoitukset, LopetusIlmoitus]"
) -> "Union[Kohde, None]":
    if isinstance(asiakas, JkrIlmoitukset):
        return _find_kohde_by_asiakastiedot(
            session, Rakennus.prt.in_(asiakas.sijainti_prt), asiakas
        )
    elif isinstance(asiakas, Asiakas):
        return _find_kohde_by_asiakastiedot(
            session, Rakennus.prt.in_(asiakas.rakennukset), asiakas
        )
    elif isinstance(asiakas, LopetusIlmoitus):
        return _find_kohde_by_ilmoitustiedot(
            session, Rakennus.prt.in_(asiakas.prt), asiakas
        )
    else:
        raise ValueError("Invalid asiakas type")


def find_kohteet_by_prt(
        session: "Session",
        asiakas: "JkrIlmoitukset"
) -> "Tuple[List[Kohde], List[str]]":
    found_kohteet = []
    not_found_prts = []

    for kompostoija in asiakas.kompostoijat:
        kompostoija_info = f"Nimi: {kompostoija.nimi}, Rakennus: {kompostoija.rakennus}"
        print(f"Kompostoija: {kompostoija_info}")
        query = (
            select(Kohde.id, Osapuoli.nimi)
            .join(Kohde.rakennus_collection)
            .join(KohteenOsapuolet, isouter=True)
            .join(Osapuoli, isouter=True)
            .join(Osoite, isouter=True)
            .where(
                Kohde.voimassaolo.overlaps(
                    DateRange(
                        asiakas.voimassa.lower or datetime.date.min,
                        asiakas.voimassa.upper or datetime.date.max,
                    )
                ),
                Rakennus.prt.in_(kompostoija.rakennus)
            )
            .distinct()
        )

        try:
            kohteet = session.execute(query).all()
        except NoResultFound:
            print("Ei löytynyt kohdetta, prt: {kompostoija.rakennus}")
            not_found_prts.append(kompostoija.rakennus)
            continue

        kompostoija_nimi = clean_asoy_name(kompostoija.nimi)
        if len(kohteet) > 1:
            names_by_kohde_id = defaultdict(set)
            for kohde_id, db_osapuoli_name in kohteet:
                names_by_kohde_id[kohde_id].add(db_osapuoli_name)
            for kohde_id, db_osapuoli_names in names_by_kohde_id.items():
                for db_osapuoli_name in db_osapuoli_names:
                    if db_osapuoli_name is not None:
                        db_osapuoli_name = clean_asoy_name(db_osapuoli_name)
                        print(kompostoija_nimi)
                        print(db_osapuoli_name)
                        if (
                            match_name(kompostoija_nimi, db_osapuoli_name)
                        ):
                            print(f"{db_osapuoli_name} match")
                            kohde = session.get(Kohde, kohde_id)
                            print("Adding kohde to list")
                            found_kohteet.append(kohde)
        elif len(kohteet) == 1:
            kohde_id = kohteet[0][0]
            kohde = session.get(Kohde, kohde_id)
            found_kohteet.append(kohde)
        else:
            print("Ei löytynyt kohdetta, prt: {kompostoija.rakennus}")
            not_found_prts.append(kompostoija.rakennus)

    return found_kohteet, not_found_prts


def find_kohde_by_address(
    session: "Session", asiakas: "Asiakas"
) -> "Union[Kohde, None]":
    print("matching by address:")
    # The osoitenumero may contain dash. In that case, the buildings may be
    # listed as separate in DVV data.
    if (
        asiakas.haltija.osoite.osoitenumero
        and "-" in asiakas.haltija.osoite.osoitenumero
    ):
        osoitenumerot = asiakas.haltija.osoite.osoitenumero.split("-", maxsplit=1)
    else:
        osoitenumerot = [asiakas.haltija.osoite.osoitenumero]

    print(osoitenumerot)
    # The address parser parses Metsätie 33 A so that 33 is osoitenumero and A is
    # huoneistotunnus. While the parsing is correct, it may very well also mean (and
    # in many cases it means) osoitenumero 33a and empty huoneistonumero.
    potential_osoitenumero_suffix = (
        asiakas.haltija.osoite.huoneistotunnus.lower()
        if asiakas.haltija.osoite.huoneistotunnus
        else ""
    )
    if potential_osoitenumero_suffix:
        osoitenumerot_with_suffix = [
            osoitenumero + potential_osoitenumero_suffix
            for osoitenumero in osoitenumerot
        ]
    else:
        osoitenumerot_with_suffix = []
    print(osoitenumerot_with_suffix)

    # - Do *NOT* find Sokeritopankatu 18 *AND* Sokeritopankatu 18a by
    # Sokeritopankatu 18 A. Looks like Sokeritopankatu 18, 18 A and 18 B are *all*
    # separate.
    # - Do *NOT* find Mukkulankatu 51 *AND* Mukkulankatu 51b by Mukkulankatu 51.
    # - Find Mukkulankatu 51 by Mukkulankatu 51 B.
    # - Only find Mukkulankatu 51 by Mukkulankatu 51.
    # - Only find Mukkulankatu 51b by Mukkulankatu 51b.
    if osoitenumerot_with_suffix:
        osoitenumero_filter = or_(
            # first, check if the letter is actually part of osoitenumero
            Osoite.osoitenumero.in_(osoitenumerot_with_suffix),
            # if the letter is not found in osoitenumero, it is huoneistotunnus
            and_(
                ~exists(Osoite.osoitenumero.in_(osoitenumerot_with_suffix)),
                Osoite.osoitenumero.in_(osoitenumerot),
            ),
        )
    else:
        osoitenumero_filter = Osoite.osoitenumero.in_(osoitenumerot)
    print(osoitenumero_filter)

    filter = and_(
        func.lower(Osoite.posti_numero) == asiakas.haltija.osoite.postinumero,
        or_(
            func.lower(Katu.katunimi_fi)
            == asiakas.haltija.osoite.katunimi.lower(),
            func.lower(Katu.katunimi_sv)
            == asiakas.haltija.osoite.katunimi.lower(),
        ),
        osoitenumero_filter,
    )
    print(filter)

    return _find_kohde_by_asiakastiedot(session, filter, asiakas)


def _find_kohde_by_ilmoitustiedot(
        session: "Session",
        filter,
        ilmoitus: "LopetusIlmoitus"
) -> "Union[Kohde, None]":
    print(f"LopetusIlmoitus.nimi: {ilmoitus.nimi}")
    query = (
        select(Kohde.id, Osapuoli.nimi)
        .join(Kohde.rakennus_collection)
        .join(KohteenOsapuolet, isouter=True)
        .join(Osapuoli, isouter=True)
        .join(Osoite, isouter=True)
        .where(
            Kohde.voimassaolo.overlaps(
                DateRange(
                    ilmoitus.Vastausaika
                )
            ),
            filter,
        )
        .distinct()
    )
    print(query)

    try:
        kohteet = session.execute(query).all()
    except NoResultFound:
        return None
    print(kohteet)

    names_by_kohde_id = defaultdict(set)
    for kohde_id, db_osapuoli_name in kohteet:
        names_by_kohde_id[kohde_id].add(db_osapuoli_name)
    if len(names_by_kohde_id) > 1:
        print(
            "Found multiple kohteet with the same address. Checking owners/inhabitants..."
        )
        vastuuhenkilo_nimi = clean_asoy_name(ilmoitus.nimi)

        for kohde_id, db_osapuoli_names in names_by_kohde_id.items():
            for db_osapuoli_name in db_osapuoli_names:
                if db_osapuoli_name is not None:
                    db_osapuoli_name = clean_asoy_name(db_osapuoli_name)
                    print(vastuuhenkilo_nimi)
                    print(db_osapuoli_name)
                    if (
                        match_name(vastuuhenkilo_nimi, db_osapuoli_name)
                    ):
                        print(f"{db_osapuoli_name} match")
                        kohde = session.get(Kohde, kohde_id)
                        print("returning kohde")
                        return kohde
    elif len(names_by_kohde_id) == 1:
        return session.get(Kohde, next(iter(names_by_kohde_id.keys())))

    return None


def _find_kohde_by_asiakastiedot(
    session: "Session",
    filter,
    asiakas: "Union[Asiakas, JkrIlmoitukset]"
) -> "Union[Kohde, None]":
    if isinstance(asiakas, JkrIlmoitukset):
        query = (
            select(Kohde.id, Osapuoli.nimi)
            .join(Kohde.rakennus_collection)
            .join(KohteenOsapuolet, isouter=True)
            .join(Osapuoli, isouter=True)
            .join(Osoite, isouter=True)
            .where(
                Kohde.voimassaolo.overlaps(
                    DateRange(
                        asiakas.voimassa.lower or datetime.date.min,
                        asiakas.voimassa.upper or datetime.date.max,
                    )
                ),
                filter,
            )
            .distinct()
        )
        print(query)

        try:
            kohteet = session.execute(query).all()
        except NoResultFound:
            return None
        print(kohteet)

        names_by_kohde_id = defaultdict(set)
        for kohde_id, db_osapuoli_name in kohteet:
            names_by_kohde_id[kohde_id].add(db_osapuoli_name)
        if len(names_by_kohde_id) > 1:
            print(
                "Found multiple kohteet with the same address. Checking owners/inhabitants..."
            )
            vastuuhenkilo_nimi = clean_asoy_name(asiakas.vastuuhenkilo.nimi)
            kompostoija_nimet = [
                clean_asoy_name(kompostoija.nimi)
                for kompostoija in asiakas.kompostoijat
            ]

            for kohde_id, db_osapuoli_names in names_by_kohde_id.items():
                for db_osapuoli_name in db_osapuoli_names:
                    if db_osapuoli_name is not None:
                        db_osapuoli_name = clean_asoy_name(db_osapuoli_name)
                        print(vastuuhenkilo_nimi)
                        print(db_osapuoli_name)
                        if any(
                            match_name(vastuuhenkilo_nimi, db_osapuoli_name) or
                            match_name(kompostoija_nimi, db_osapuoli_name)
                            for kompostoija_nimi in kompostoija_nimet
                        ):
                            print(f"{db_osapuoli_name} match")
                            kohde = session.get(Kohde, kohde_id)
                            print("returning kohde")
                            return kohde
        elif len(names_by_kohde_id) == 1:
            return session.get(Kohde, next(iter(names_by_kohde_id.keys())))

        return None

    # The same kohde may be client at multiple urakoitsijat and have multiple customer
    # ids. Do *not* filter by missing/existing customer id.
    elif isinstance(asiakas, Asiakas):
        query = (
            select(Kohde.id, Osapuoli.nimi)
            .join(Kohde.rakennus_collection)
            .join(KohteenOsapuolet, isouter=True)
            .join(Osapuoli, isouter=True)
            .join(Osoite, isouter=True)
            .join(Katu, isouter=True)
            .where(
                Kohde.voimassaolo.overlaps(
                    DateRange(
                        asiakas.voimassa.lower or datetime.date.min,
                        asiakas.voimassa.upper or datetime.date.max,
                    )
                ),
                # Any yhteystieto will do. The bill might not always go
                # to the oldest person. It might be the owner.
                # KohteenOsapuolet.osapuolenrooli
                # == codes.osapuolenroolit[OsapuolenrooliTyyppi.ASIAKAS],
                filter,
            )
            .distinct()
        )
        print(query)

        try:
            kohteet = session.execute(query).all()
        except NoResultFound:
            return None
        print(kohteet)

        names_by_kohde_id = defaultdict(set)
        for kohde_id, db_osapuoli_name in kohteet:
            names_by_kohde_id[kohde_id].add(db_osapuoli_name)
        if len(names_by_kohde_id) > 1:
            # The address has multiple kohteet for the same date period.
            # We may have
            # 1) multiple perusmaksut for the same building (not paritalo),
            # 2) paritalo,
            # 3) multiple buildings in the same address (not paritalo),
            # 4) multiple people moving in or out of the building in the same time period.
            # Since we have no customer id here, we just have to check if the name is
            # actually an osapuoli of an existing kohde or not. If not, we will return
            # None and create a new kohde later. If an osapuoli exists, the new kohde may
            # have been created from a kuljetus already.
            print(
                "Found multiple kohteet with the same address. Checking owners/inhabitants..."
            )
            haltija_nimi = clean_asoy_name(asiakas.haltija.nimi)
            yhteystieto_nimi = clean_asoy_name(asiakas.yhteyshenkilo.nimi)
            for kohde_id, db_osapuoli_names in names_by_kohde_id.items():
                for db_osapuoli_name in db_osapuoli_names:
                    if db_osapuoli_name is not None:
                        db_osapuoli_name = clean_asoy_name(db_osapuoli_name)
                        print(haltija_nimi)
                        print(db_osapuoli_name)
                        if match_name(haltija_nimi, db_osapuoli_name) or match_name(
                            yhteystieto_nimi, db_osapuoli_name
                        ):
                            print(f"{db_osapuoli_name} match")
                            kohde = session.get(Kohde, kohde_id)
                            print("returning kohde")
                            return kohde
        elif len(names_by_kohde_id) == 1:
            return session.get(Kohde, next(iter(names_by_kohde_id.keys())))

    return None


def update_kohde(kohde: Kohde, asiakas: "Asiakas"):
    if kohde.alkupvm != asiakas.voimassa.lower:
        kohde.alkupvm = asiakas.voimassa.lower
    if kohde.loppupvm != asiakas.voimassa.upper:
        kohde.loppupvm = asiakas.voimassa.upper


def get_kohde_by_asiakasnumero(
    session: "Session", tunnus: "Tunnus"
) -> "Union[Kohde, None]":
    query = (
        select(Kohde)
        .join(UlkoinenAsiakastieto)
        .where(
            UlkoinenAsiakastieto.tiedontuottaja_tunnus == tunnus.jarjestelma,
            UlkoinenAsiakastieto.ulkoinen_id == tunnus.tunnus,
        )
    )
    try:
        kohde = session.execute(query).scalar_one()
    except NoResultFound:
        kohde = None

    return kohde


@lru_cache(maxsize=32)
def get_or_create_pseudokohde(session: "Session", nimi: str, kohdetyyppi) -> Kohde:
    kohdetyyppi = codes.kohdetyypit[kohdetyyppi]
    query = select(Kohde).where(Kohde.nimi == nimi, Kohde.kohdetyyppi == kohdetyyppi)
    try:
        kohde = session.execute(query).scalar_one()
    except NoResultFound:
        kohde = Kohde(nimi=nimi, kohdetyyppi=kohdetyyppi)
        session.add(kohde)

    return kohde


def get_kohde_by_address(
    session: "Session", asiakas: "Asiakas"
) -> "Union[Kohde, None]":
    ...



def get_dvv_rakennustiedot_without_kohde(
    session: "Session",
    poimintapvm: "Optional[datetime.date]",
    loppupvm: "Optional[datetime.date]",
) -> "Dict[int, Rakennustiedot]":
    # Fastest to load everything to memory first.
    if loppupvm is None:
        rakennus_id_with_current_kohde = (
            select(Rakennus.id)
            .join(KohteenRakennukset)
            .join(Kohde)
            .filter(poimintapvm < Kohde.loppupvm)
        )
    else:
        rakennus_id_with_current_kohde = (
            select(Rakennus.id)
            .join(KohteenRakennukset)
            .join(Kohde)
            .filter(Kohde.voimassaolo.overlaps(DateRange(poimintapvm, loppupvm)))
        )
    # Import *all* buildings, also those without inhabitants, owners and/or addresses
    rows = session.execute(
        select(Rakennus, RakennuksenVanhimmat, RakennuksenOmistajat, Osoite)
        .join_from(Rakennus, RakennuksenVanhimmat, isouter=True)
        .join_from(Rakennus, RakennuksenOmistajat, isouter=True)
        .join(Rakennus.osoite_collection, isouter=True)
        .filter(~Rakennus.id.in_(rakennus_id_with_current_kohde))
        # Do not import rakennus that have been removed from DVV data
        .filter(
            or_(
                Rakennus.kaytostapoisto_pvm.is_(None),
                Rakennus.kaytostapoisto_pvm > poimintapvm,
            )
        )
    ).all()
    rakennustiedot_by_id = dict()
    for row in rows:
        rakennus_id = row[0].id
        if rakennus_id not in rakennustiedot_by_id:
            rakennustiedot_by_id[rakennus_id] = (row[0], set(), set(), set())
        if row[1]:
            rakennustiedot_by_id[rakennus_id][1].add(row[1])
        if row[2]:
            rakennustiedot_by_id[rakennus_id][2].add(row[2])
        if row[3]:
            rakennustiedot_by_id[rakennus_id][3].add(row[3])
    # Freeze the rakennustiedot sets in the end.
    # This way, rakennustiedot may be used in sets etc.
    for id, (rakennus, vanhimmat, omistajat, osoitteet) in rakennustiedot_by_id.items():
        rakennustiedot_by_id[id] = (
            rakennus,
            frozenset(vanhimmat),
            frozenset(omistajat),
            frozenset(osoitteet),
        )
    return rakennustiedot_by_id


def _is_sauna(rakennus: "Rakennus"):
    """
    Saunas are a bit of a special case. They are significant buildings *only* if they
    are not added as auxiliary buildings. Therefore, we have to check if a building
    is a sauna *in addition* to checking significance.

    This is because saunas are often missing owner data (and they should belong to the
    main building), but we also want saunas to be created as separate kohde if no
    main building was found.
    """
    return (
        rakennus.rakennuksenkayttotarkoitus
        == codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.SAUNA]
    )


def _is_significant_building(rakennustiedot: "Rakennustiedot") -> bool:
    """
    Määrittää, mitkä rakennukset tulisi aina sisällyttää kohteeseen, joko erillisenä
    tai yhdistettynä muihin rakennuksiin. Tämä funktio vaatii rakennustiedot, koska
    mikä tahansa rakennus, jossa on pysyvä asukas (riippumatta rakennustyypistä), on
    aina merkittävä. Myös rakennukset ilman omistajia voivat olla merkittäviä.

    Saunat tulisi aina sisällyttää kohteeseen, mutta niillä ei koskaan pitäisi olla
    erillistä kohdetta, jos ne voidaan liittää muihin rakennuksiin samalla kiinteistöllä.
    Niiden merkittävyys on siksi tarkistettava erikseen kontekstista riippuen.
    """
    rakennus = rakennustiedot[0]
    asukkaat = rakennustiedot[1]
    
    return bool(asukkaat) or rakennus.rakennuksenkayttotarkoitus in (
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.YKSITTAISTALO],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.PARITALO],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.MUU_PIENTALO],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.RIVITALO],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.LUHTITALO],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.KETJUTALO],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.KERROSTALO],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.VAPAA_AJANASUNTO],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.MUU_ASUNTOLA],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.VANHAINKOTI],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.LASTENKOTI],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.KEHITYSVAMMAHOITOLAITOS],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.MUU_HUOLTOLAITOS],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.PAIVAKOTI],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.MUU_SOSIAALITOIMEN_RAKENNUS],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.YLEISSIVISTAVA_OPPILAITOS],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.AMMATILLINEN_OPPILAITOS],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.KORKEAKOULU],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.TUTKIMUSLAITOS],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.OPETUSRAKENNUS],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.MUU_OPETUSRAKENNUS],
    )


# def _cluster_rakennustiedot(
#     rakennustiedot_to_cluster: "Set[Rakennustiedot]",
#     distance_limit: int,
#     existing_cluster: "Optional[Set[Rakennustiedot]]" = None
# ) -> "List[Set[Rakennustiedot]]":
#     """
#     Klusteroi rakennukset kun KAIKKI kriteerit täyttyvät:
#     1. Sama omistaja TAI asukas
#     2. Sama osoite
#     3. Etäisyys alle raja-arvon
#     """
#     clusters = []
#     while rakennustiedot_to_cluster:
#         current_building = rakennustiedot_to_cluster.pop()
#         cluster = {current_building}
        
#         # Kerää samaan klusteriin kuuluvat rakennukset
#         matches = {
#             building for building in rakennustiedot_to_cluster
#             if (
#                 # 1. Sama omistaja TAI asukas  
#                 (_match_ownership_or_residents(current_building, building) or
#                 # 2. Sama osoite
#                 _match_addresses(current_building[3], building[3])) and
#                 # 3. Etäisyys alle rajan
#                 minimum_distance_of_buildings(
#                     [current_building[0], building[0]]
#                 ) < distance_limit
#             )
#         }
        
#         cluster.update(matches)
#         rakennustiedot_to_cluster -= matches
#         clusters.append(cluster)

#     return clusters

def _cluster_rakennustiedot_fulllog(
    rakennustiedot_to_cluster: "Set[Rakennustiedot]",
    distance_limit: int,
    existing_cluster: "Optional[Set[Rakennustiedot]]" = None
) -> "List[Set[Rakennustiedot]]":
    """
    Klusteroi rakennukset kun KAIKKI kriteerit täyttyvät:
    1. Sama omistaja TAI asukas
    2. Sama osoite
    3. Etäisyys alle raja-arvon
    """
    with open('cluster_debug.log', 'a', encoding='utf-8') as f:
        f.write(f"\nAloitetaan klusterointi {len(rakennustiedot_to_cluster)} rakennukselle\n")
        clusters = []
        
        while rakennustiedot_to_cluster:
            current_building = rakennustiedot_to_cluster.pop()
            cluster = {current_building}
            f.write(f"\nUusi klusteri, aloitetaan rakennuksesta {current_building[0].prt}\n")
            
            # Kerää samaan klusteriin kuuluvat rakennukset
            matches = set()
            for building in rakennustiedot_to_cluster:
                f.write(f"\nTarkistetaan rakennus {building[0].prt}:\n")
                
                # Tarkista omistajat/asukkaat
                owners1 = {owner.osapuoli_id for owner in current_building[2]}
                owners2 = {owner.osapuoli_id for owner in building[2]}
                residents1 = {res.osapuoli_id for res in current_building[1]}
                residents2 = {res.osapuoli_id for res in building[1]}
                
                f.write(f"Omistajat 1 ({current_building[0].prt}): {owners1}\n")
                f.write(f"Omistajat 2 ({building[0].prt}): {owners2}\n")
                f.write(f"Asukkaat 1 ({current_building[0].prt}): {residents1}\n")
                f.write(f"Asukkaat 2 ({building[0].prt}): {residents2}\n")
                
                owners_match = bool(owners1 and owners2 and (owners1 & owners2))
                residents_match = bool(residents1 and residents2 and (residents1 & residents2))
                f.write(f"- Omistajat täsmäävät: {owners_match}\n")
                f.write(f"- Asukkaat täsmäävät: {residents_match}\n")
                
                # Tarkista osoitteet
                addresses_match = _match_addresses(current_building[3], building[3])
                f.write(f"- Osoitteet täsmäävät: {addresses_match}\n")
                
                # Tarkista etäisyys
                distance = minimum_distance_of_buildings([current_building[0], building[0]])
                f.write(f"- Etäisyys: {distance}m\n")
                
                # Yhdistämisen ehdot
                match_criteria = (owners_match or residents_match or addresses_match)
                distance_ok = distance < distance_limit
                
                f.write(f"- Yhdistämiskriteerit täyttyvät: {match_criteria}\n")
                f.write(f"- Etäisyys OK: {distance_ok}\n")
                
                if match_criteria and distance_ok:
                    matches.add(building)
                    f.write(f"=> Lisätään klusteriin!\n")
                else:
                    f.write(f"=> Ei lisätä klusteriin.\n")
            
            f.write(f"\nLöytyi {len(matches)} rakennusta klusteriin\n")
            
            cluster.update(matches)
            rakennustiedot_to_cluster -= matches
            clusters.append(cluster)
            
            f.write(f"Klusteri valmis, sisältää {len(cluster)} rakennusta:\n")
            for r in cluster:
                f.write(f"- {r[0].prt}\n")

        f.write(f"\nKlusterointi valmis. Muodostui {len(clusters)} klusteria.\n")
        for i, cluster in enumerate(clusters, 1):
            f.write(f"\nKlusteri {i}:\n")
            for r in cluster:
                f.write(f"- {r[0].prt}\n")
                
        return clusters

def _cluster_rakennustiedot(
    rakennustiedot_to_cluster: "Set[Rakennustiedot]",
    distance_limit: int,
    existing_cluster: "Optional[Set[Rakennustiedot]]" = None
) -> "List[Set[Rakennustiedot]]":
    # PRTt joiden klusterointia seurataan
    log_prt_in = ('103074869S', '103074870T', '103074871U', '103074872V', 
                  '103074873W', '103074874X', '103074875Y', '1030748760', 
                  '1030748771', '1030748782')
    
    clusters = []
    
    with open('cluster_debug.log', 'a', encoding='utf-8') as f:
        tracked_buildings = any(r[0].prt in log_prt_in for r in rakennustiedot_to_cluster)
        log_all = not log_prt_in
        
        if tracked_buildings or log_all:
            f.write("\n" + "="*80 + "\n")
            f.write(f"{datetime.datetime.now()}: Aloitetaan klusterointi {len(rakennustiedot_to_cluster)} rakennukselle\n")
            f.write("Rakennukset alussa:\n")
            for r in rakennustiedot_to_cluster:
                f.write(f"- {r[0].prt}\n")

        while rakennustiedot_to_cluster:
            current_building = rakennustiedot_to_cluster.pop()
            cluster = {current_building}
            
            should_log = (log_all or 
                         current_building[0].prt in log_prt_in or
                         any(r[0].prt in log_prt_in for r in rakennustiedot_to_cluster))
            
            if should_log:
                f.write(f"\nUusi klusteri, aloitetaan rakennuksesta {current_building[0].prt}\n")
                f.write("Jäljellä olevat rakennukset:\n")
                for r in rakennustiedot_to_cluster:
                    f.write(f"- {r[0].prt}\n")
            
            matches = set()
            for building in rakennustiedot_to_cluster:
                # Kerää omistaja- ja asukastiedot ENNEN ehtolausetta
                owners1 = {owner.osapuoli_id for owner in current_building[2]}
                owners2 = {owner.osapuoli_id for owner in building[2]}
                residents1 = {res.osapuoli_id for res in current_building[1]}
                residents2 = {res.osapuoli_id for res in building[1]}
                
                should_log_match = (log_all or 
                                  current_building[0].prt in log_prt_in or 
                                  building[0].prt in log_prt_in)
                
                if should_log_match:
                    f.write(f"\nTarkistetaan rakennus {building[0].prt}:\n")
                    f.write(f"Omistajat 1 ({current_building[0].prt}): {owners1}\n")
                    f.write(f"Omistajat 2 ({building[0].prt}): {owners2}\n")
                    f.write(f"Asukkaat 1 ({current_building[0].prt}): {residents1}\n")
                    f.write(f"Asukkaat 2 ({building[0].prt}): {residents2}\n")
                
                owners_match = bool(owners1 and owners2 and (owners1 & owners2))
                residents_match = bool(residents1 and residents2 and (residents1 & residents2))
                addresses_match = _match_addresses(current_building[3], building[3])
                distance = minimum_distance_of_buildings([current_building[0], building[0]])
                
                if should_log_match:
                    f.write(f"- Omistajat täsmäävät: {owners_match}\n")
                    f.write(f"- Asukkaat täsmäävät: {residents_match}\n")
                    f.write(f"- Osoitteet täsmäävät: {addresses_match}\n")
                    f.write(f"- Etäisyys: {distance}m\n")
                
                match_criteria = (owners_match or residents_match or addresses_match)
                distance_ok = distance < distance_limit
                
                if should_log_match:
                    f.write(f"- Yhdistämiskriteerit täyttyvät: {match_criteria}\n")
                    f.write(f"- Etäisyys OK: {distance_ok}\n")
                
                if match_criteria and distance_ok:
                    matches.add(building)
                    if should_log_match:
                        f.write(f"=> Lisätään klusteriin!\n")
                elif should_log_match:
                    f.write(f"=> Ei lisätä klusteriin.\n")
            
            if should_log:
                f.write(f"\nLöytyi {len(matches)} rakennusta klusteriin\n")
            
            cluster.update(matches)
            rakennustiedot_to_cluster -= matches
            clusters.append(cluster)
            
            if should_log:
                f.write(f"Klusteri valmis, sisältää {len(cluster)} rakennusta:\n")
                for r in cluster:
                    f.write(f"- {r[0].prt}\n")

        if tracked_buildings or log_all:
            f.write("\nKaikki klusterit muodostettu:\n")
            for i, cluster in enumerate(clusters, 1):
                has_tracked = any(r[0].prt in log_prt_in for r in cluster)
                if has_tracked or log_all:
                    f.write(f"\nKlusteri {i}:\n")
                    prts = sorted([r[0].prt for r in cluster])
                    f.write(f"PRTt: {prts}\n")
                
    return clusters

def _match_ownership_or_residents(
    building1: "Rakennustiedot",
    building2: "Rakennustiedot" 
) -> bool:
    """
    Tarkistaa, onko rakennuksilla sama omistaja TAI asukas.
    Aiempi versio vaati molemmat.
    """
    owners1 = {owner.osapuoli_id for owner in building1[2]}
    owners2 = {owner.osapuoli_id for owner in building2[2]} 
    residents1 = {res.osapuoli_id for res in building1[1]}
    residents2 = {res.osapuoli_id for res in building2[1]}
    
    # Palauta True jos joko omistajissa TAI asukkaissa on yhteinen
    return bool(
        (owners1 and owners2 and (owners1 & owners2)) or
        (residents1 and residents2 and (residents1 & residents2))
    )


def update_old_kohde_data(session, old_kohde_id, new_kohde_id, new_kohde_alkupvm):
    """
    Päivittää vanhan kohteen tiedot kerralla yhtenä transaktiona:
    - Asettaa vanhan kohteen loppupvm 
    - Siirtää sopimukset ja kuljetukset
    - Päivittää viranomaispäätökset
    - Päivittää kompostorit
    """
    # Aseta loppupvm = uuden kohteen alkupvm - 1 päivä
    loppupvm = new_kohde_alkupvm - timedelta(days=1)
    
    # 1. Päivitä kohteen loppupvm
    stmt = (
        update(Kohde)
        .where(Kohde.id == old_kohde_id)
        .values(loppupvm=loppupvm)
        .execution_options(synchronize_session=False)
    )
    session.execute(stmt)

    # 2. Siirrä sopimukset ja kuljetukset uudelle kohteelle
    # Sopimukset joiden loppupvm >= uuden kohteen alkupvm
    stmt = (
        update(Sopimus)
        .where(Sopimus.kohde_id == old_kohde_id)
        .where(Sopimus.loppupvm >= new_kohde_alkupvm)
        .values(kohde_id=new_kohde_id)
        .execution_options(synchronize_session=False)
    )
    session.execute(stmt)
    
    # Kuljetukset joiden loppupvm >= uuden kohteen alkupvm 
    stmt = (
        update(Kuljetus)
        .where(Kuljetus.kohde_id == old_kohde_id)
        .where(Kuljetus.loppupvm >= new_kohde_alkupvm)
        .values(kohde_id=new_kohde_id)
        .execution_options(synchronize_session=False)
    )
    session.execute(stmt)

    # 3. Päivitä viranomaispäätösten loppupvm
    # Hae vanhan kohteen rakennusten id:t
    rakennus_ids = select(KohteenRakennukset.rakennus_id).where(
        KohteenRakennukset.kohde_id == old_kohde_id
    )

    # Aseta loppupvm päätöksille jotka alkaneet <= vanhan kohteen loppupvm
    stmt = (
        update(Viranomaispaatokset)
        .where(
            Viranomaispaatokset.rakennus_id.in_(rakennus_ids.scalar_subquery()),
            Viranomaispaatokset.alkupvm <= loppupvm
        )
        .values(loppupvm=loppupvm)
        .execution_options(synchronize_session=False)
    )
    session.execute(stmt)

    # 4. Päivitä kompostorien tiedot
    # Hae vanhan kohteen kompostorien id:t
    kompostori_ids = select(KompostorinKohteet.kompostori_id).where(
        KompostorinKohteet.kohde_id == old_kohde_id
    )

    # Aseta loppupvm kompostoreille jotka alkaneet <= vanhan kohteen loppupvm
    stmt = (
        update(Kompostori)
        .where(
            Kompostori.id.in_(kompostori_ids.scalar_subquery()),
            Kompostori.alkupvm <= loppupvm
        )
        .values(loppupvm=loppupvm)
        .execution_options(synchronize_session=False)
    )
    session.execute(stmt)

    # 5. Siirrä jatkuvat kompostorit uudelle kohteelle
    # Hae kompostorit jotka jatkuvat loppupvm:n jälkeen
    jatkuvat_kompostorit = select(Kompostori.id).where(
        and_(
            Kompostori.id.in_(kompostori_ids.scalar_subquery()),
            Kompostori.alkupvm > loppupvm
        )
    )

    stmt = (
        update(KompostorinKohteet)
        .where(
            KompostorinKohteet.kompostori_id.in_(jatkuvat_kompostorit.scalar_subquery()),
            KompostorinKohteet.kohde_id == old_kohde_id
        )
        .values(kohde_id=new_kohde_id)
        .execution_options(synchronize_session=False)
    )
    session.execute(stmt)

    # Kaikki muutokset tehdään yhdessä transaktiossa
    session.commit()


@lru_cache(maxsize=128)
def is_auxiliary_building(rakennus: Rakennus) -> bool:
    """
    Tarkistaa onko rakennus apurakennus (talousrakennus tai sauna).
    
    Tarkistaa ensisijaisesti Rakennusluokitus 2018 mukaiset luokat:
    - 1910: Saunarakennukset
    - 1911: Talousrakennukset
    
    Käyttää vanhempaa rakennuksen käyttötarkoitusta VAIN jos 2018 luokka puuttuu kokonaan.
    
    Args:
        rakennus: Rakennus-objekti
        
    Returns:
        bool: True jos kyseessä on apurakennus, muuten False
    """
    if rakennus.rakennusluokka_2018 is not None:
        return rakennus.rakennusluokka_2018 in ('1910', '1911')
    
    # Tarkista vanha käyttötarkoitus vain jos 2018 luokka puuttuu kokonaan
    return rakennus.rakennuksenkayttotarkoitus in (
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.TALOUSRAKENNUS],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.SAUNA]
    )


def add_auxiliary_buildings_materialized(
    dvv_rakennustiedot: Dict[int, "Rakennustiedot"],
    building_sets: List[Set["Rakennustiedot"]],
    session: Session 
) -> List[Set["Rakennustiedot"]]:
    """
    Lisää apurakennukset (saunat, piharakennukset) päärakennusten ryhmiin hyödyntäen
    materialisoitua nearby_buildings näkymää.

    Apurakennus lisätään ryhmään jos KAIKKI seuraavat ehdot täyttyvät:
    1. On tyypiltään apurakennus (sauna tai piharakennus)
    2. Sama omistaja tai asukas kuin jollain ryhmän rakennuksista
    3. Sama osoite kuin jollain ryhmän rakennuksista
    4. Löytyy nearby_buildings näkymästä (eli on max 300m päässä)

    Args:
        dvv_rakennustiedot: Sanakirja rakennustiedoista rakennuksen id:n mukaan
        building_sets: Lista rakennusryhmistä, joihin apurakennuksia etsitään
        session: Tietokantaistunto

    Returns:
        Lista päivitetyistä rakennusryhmistä joihin on lisätty kriteerit täyttävät
        apurakennukset
    """
    logger = logging.getLogger(__name__)
    print(f"Etsitään apurakennuksia {len(building_sets)} rakennusryhmälle...")
    logger.info(f"\nEtsitään apurakennuksia {len(building_sets)} rakennusryhmälle...")
    
    start_time = dt.now()

    # Kerää kaikki päärakennusten ID:t
    main_building_ids = {
        rakennustiedot[0].id 
        for building_set in building_sets
        for rakennustiedot in building_set
    }

    # Hae potentiaaliset apurakennukset käyttäen materialisoitua näkymää
    nearby_query = text("""
        SELECT DISTINCT r.id, r.prt, 
               ro.osapuoli_id as owner_id,
               o.katu_id, o.osoitenumero
        FROM jkr.nearby_buildings nb
        JOIN jkr.rakennus r ON 
            (r.id = nb.rakennus1_id OR r.id = nb.rakennus2_id)
        LEFT JOIN jkr.rakennuksen_omistajat ro ON r.id = ro.rakennus_id
        LEFT JOIN jkr.osoite o ON r.id = o.rakennus_id
        WHERE 
            -- Toinen rakennuksista on päärakennus
            ((nb.rakennus1_id = ANY(:main_ids) AND nb.rakennus2_id != ANY(:main_ids))
             OR 
             (nb.rakennus2_id = ANY(:main_ids) AND nb.rakennus1_id != ANY(:main_ids)))
            -- On apurakennus (2018 luokitus tai vanha)
            AND (
                r.rakennusluokka_2018 IN ('1910', '1911')
                OR (
                    r.rakennusluokka_2018 IS NULL 
                    AND r.rakennuksenkayttotarkoitus_koodi IN ('941', '931')
                )
            )
    """)

    # Suorita kysely
    results = session.execute(
        nearby_query,
        {"main_ids": list(main_building_ids)}
    ).all()

    # Kokoa apurakennusten tiedot
    potential_auxiliary_buildings = {}
    for row in results:
        if row.id not in dvv_rakennustiedot:
            continue
            
        aux_tiedot = dvv_rakennustiedot[row.id]
        if row.id not in potential_auxiliary_buildings:
            potential_auxiliary_buildings[row.id] = aux_tiedot

    # Lisää sopivat apurakennukset ryhmiin
    updated_sets = []
    aux_added = 0
    
    for building_set in building_sets:
        updated_set = building_set.copy()
        
        # Kerää ryhmän omistajat ja osoitteet
        main_owner_ids = {
            osapuoli.id
            for rakennustiedot in building_set
            for omistaja in rakennustiedot[2]  # [2] on omistajat
            for osapuoli in [omistaja.osapuoli]
        }
        
        main_address_ids = {
            (osoite.katu_id, osoite.osoitenumero)
            for rakennustiedot in building_set
            for osoite in rakennustiedot[3]  # [3] on osoitteet
        }

        # Käy läpi potentiaaliset apurakennukset
        for aux_id, aux_tiedot in potential_auxiliary_buildings.items():
            # Kerää apurakennuksen omistajat ja osoitteet
            aux_owner_ids = {
                osapuoli.id
                for omistaja in aux_tiedot[2]
                for osapuoli in [omistaja.osapuoli]
            }
            
            aux_address_ids = {
                (osoite.katu_id, osoite.osoitenumero)
                for osoite in aux_tiedot[3]
            }

            # Tarkista kriteerit:
            # 1. Omistajuus
            has_matching_owner = (
                not aux_owner_ids or  # Jos ei omistajia, hyväksytään
                bool(aux_owner_ids & main_owner_ids)  # Tai jos yhteinen omistaja
            )
            
            # 2. Osoite - vaaditaan aina yhteinen osoite
            has_matching_address = bool(aux_address_ids & main_address_ids)

            # Jos kriteerit täyttyvät, lisää apurakennus ryhmään
            if has_matching_owner and has_matching_address:
                updated_set.add(aux_tiedot)
                aux_added += 1

        updated_sets.append(updated_set)

    elapsed = dt.now() - start_time
    print(
        f"Lisätty {aux_added} apurakennusta {len(building_sets)} rakennusryhmään, "
        f"aikaa kului {elapsed.total_seconds():.2f}s"
    )
    logger.info(
        f"Lisätty {aux_added} apurakennusta {len(building_sets)} rakennusryhmään, "
        f"aikaa kului {elapsed.total_seconds():.2f}s"
    )
    return updated_sets

def _add_auxiliary_buildings(
    dvv_rakennustiedot: Dict[int, Rakennustiedot],
    building_sets: List[Set[Rakennustiedot]]
) -> List[Set[Rakennustiedot]]:
    """
    Lisää piha- ja apurakennukset päärakennusten muodostamiin rakennusryhmiin.
    """
    logger = logging.getLogger(__name__)
    logger.info("\nLisätään apurakennukset rakennusryhmiin...")

    # Luo lookup vain lähekkäisille rakennuksille
    nearby_buildings = create_nearby_buildings_lookup(dvv_rakennustiedot)
    
    sets_to_return = []
    progress = BatchProgressTracker(len(building_sets), "Apurakennusten lisäys")

    for building_set in building_sets:
        set_to_return = building_set.copy()
        main_building_ids = {tiedot[0].id for tiedot in building_set}
        
        # Kerää päärakennusten omistajat ja osoitteet suoraan building_setistä
        main_building_owners = {
            owner.osapuoli_id 
            for building in building_set
            for owner in building[2]
        }
        
        main_addresses = {
            (address.katu_id, address.osoitenumero)
            for building in building_set
            for address in building[3]
        }

        # Tarkista vain lähellä olevat rakennukset
        aux_candidates = set()
        for main_id in main_building_ids:
            if main_id in nearby_buildings:
                aux_candidates.update(nearby_buildings[main_id])

        for aux_id in aux_candidates:
            if aux_id in main_building_ids:
                continue

            aux_data = dvv_rakennustiedot[aux_id]
            aux_building = aux_data[0]
            
            # Nopeampi tarkistus ensin
            if not is_auxiliary_building(aux_building):
                continue

            # Tarkista osoite ja omistajuus vain jos on apurakennus
            aux_owners = {owner.osapuoli_id for owner in aux_data[2]}
            aux_addresses = {
                (address.katu_id, address.osoitenumero)
                for address in aux_data[3]
            }

            # Lisää rakennus jos kriteerit täyttyvät
            if ((not aux_owners or (aux_owners & main_building_owners)) and
                (aux_addresses & main_addresses)):
                set_to_return.add(aux_data)

        sets_to_return.append(set_to_return)
        progress.update()

    progress.done()
    return sets_to_return


def add_ulkoinen_asiakastieto_for_kohde(
    session: "Session", kohde: Kohde, asiakas: "Asiakas"
):
    asiakastieto = UlkoinenAsiakastieto(
        tiedontuottaja_tunnus=asiakas.asiakasnumero.jarjestelma,
        ulkoinen_id=asiakas.asiakasnumero.tunnus,
        ulkoinen_asiakastieto=asiakas.ulkoinen_asiakastieto,
        kohde=kohde,
    )

    session.add(asiakastieto)

    return asiakastieto


def create_new_kohde_yritelm(session: "Session", asiakas: "Asiakas"):
    """
    Luo uusi kohde asiakkaan tietojen perusteella.
    Kohdetyyppi määräytyy:
    - ALUEKERAYS jos kyseessä on aluekeräyspiste
    - ASUINKIINTEISTO tai MUU rakennustietojen perusteella
    """
    if is_aluekerays(asiakas):
        kohdetyyppi = KohdeTyyppi.ALUEKERAYS
    else:
        # Tarkista rakennusten perusteella
        kohdetyyppi = KohdeTyyppi.MUU
        for prt in asiakas.rakennukset:
            rakennus = session.query(Rakennus).filter(Rakennus.prt == prt).first()
            if rakennus:
                building_type = determine_kohdetyyppi(rakennus)
                if building_type == KohdeTyyppi.ASUINKIINTEISTO:
                    kohdetyyppi = KohdeTyyppi.ASUINKIINTEISTO
                    break

    kohde_display_name = form_display_name(asiakas.haltija)
    kohde = Kohde(
        nimi=kohde_display_name,
        kohdetyyppi=codes.kohdetyypit[kohdetyyppi],
        alkupvm=asiakas.voimassa.lower,
        loppupvm=asiakas.voimassa.upper,
    )

    return kohde


def create_new_kohde(session: "Session", asiakas: "Asiakas"):
    kohdetyyppi = codes.kohdetyypit[
        KohdeTyyppi.ALUEKERAYS if is_aluekerays(asiakas) else KohdeTyyppi.KIINTEISTO
    ]
    kohde_display_name = form_display_name(asiakas.haltija)
    kohde = Kohde(
        nimi=kohde_display_name,
        kohdetyyppi=kohdetyyppi,
        alkupvm=asiakas.voimassa.lower,
        loppupvm=asiakas.voimassa.upper,
    )

    return kohde


def parse_alkupvm_for_kohde(session, rakennus_ids, old_kohde_alkupvm, poimintapvm):
    """
    Määrittää uuden kohteen alkupvm:n seuraavasti:
    1. Jos rakennuksilla ei ole omistaja/asukas muutoksia -> poimintapvm
    2. Jos muutoksia, käytetään uusinta muutosta:
       - omistajan muutos
       - vanhimman asukkaan muutos
       - vanha kohteen alkupvm
    """
    # Hae viimeisin omistajamuutos
    latest_omistaja_change = (
        session.query(func.max(RakennuksenOmistajat.omistuksen_alkupvm))
        .filter(RakennuksenOmistajat.rakennus_id.in_(rakennus_ids))
        .scalar()
    )
    
    # Hae viimeisin asukas muutos  
    latest_vanhin_change = session.query(
        func.max(RakennuksenVanhimmat.alkupvm)
    ).filter(RakennuksenVanhimmat.rakennus_id.in_(rakennus_ids)).scalar()

    # Jos ei muutoksia, käytä poimintapvm
    if latest_omistaja_change is None and latest_vanhin_change is None:
        return poimintapvm

    # Määritä viimeisin muutospäivä
    latest_change = old_kohde_alkupvm
    if latest_omistaja_change is None and latest_vanhin_change is not None:
        latest_change = latest_vanhin_change
    elif latest_vanhin_change is None and latest_omistaja_change is not None:
        latest_change = latest_omistaja_change
    else:
        latest_change = max(latest_omistaja_change, latest_vanhin_change)

    # Jos muutoksia vanhan kohteen alkupvm:n jälkeen, käytä muutospvm
    # Muuten käytä poimintapvm
    if latest_change > old_kohde_alkupvm:
        return latest_change
    else:
        return poimintapvm


def create_new_kohde_from_buildings(
    session: "Session",
    rakennus_ids: "List[int]",
    asukkaat: "Set[Osapuoli]",
    omistajat: "Set[Osapuoli]",
    poimintapvm: "Optional[datetime.date]",
    loppupvm: "Optional[datetime.date]",
    old_kohde: "Optional[Kohde]",
):
    """
    Luo uuden kohteen annettujen rakennusten perusteella ja yhdistää niihin liittyvät tiedot.
    
    Kohteen nimeäminen priorisoidaan seuraavassa järjestyksessä:
    1. Asunto-osakeyhtiön nimi
    2. Yrityksen nimi 
    3. Yhteisön nimi
    4. Vanhimman asukkaan nimi
    5. Omistajan nimi
    Jos mitään edellä mainituista ei löydy, kohde nimetään "Tuntematon".

    Alkupäivämäärä määräytyy seuraavasti:
    - Jos kyseessä on vanhan kohteen päivitys, käytetään parse_alkupvm_for_kohde -funktion määrittämää päivää
    - Muussa tapauksessa käytetään annettua poimintapäivämäärää
    
    Loppupäivämääräksi asetetaan:
    - Annettu loppupvm, jos se on määritelty
    - Muussa tapauksessa järjestelmän oletusarvo (31.12.2100)

    Args:
        session: Tietokantaistunto
        rakennus_ids: Lista rakennusten ID-tunnisteista
        asukkaat: Joukko asukkaiden Osapuoli-objekteja
        omistajat: Joukko omistajien Osapuoli-objekteja 
        poimintapvm: Kohteen alkupäivämäärä (oletus)
        loppupvm: Kohteen loppupäivämäärä (vapaaehtoinen)
        old_kohde: Vanha kohde, jos kyseessä on päivitys (vapaaehtoinen)

    Returns:
        Kohde: Luotu kohdeobjekti kaikkine riippuvuuksineen

    Huomautukset:
        - Funktio lisää kaikki asukkaat VANHIN_ASUKAS -roolilla
        - Omistajat lisätään OMISTAJA-roolilla, vaikka olisivat myös asukkaita
        - Omistajatiedot tallennetaan aina, jotta kohde voidaan tunnistaa myöhemmissä tuonneissa
        - Muutokset tallennetaan session.flush()-komennolla, mutta ei commitoida
    """
    if omistajat:
        # prefer companies over private owners when naming combined objects
        asoy_asiakkaat = {osapuoli for osapuoli in omistajat if is_asoy(osapuoli.nimi)}
        company_asiakkaat = {
            osapuoli for osapuoli in omistajat if is_company(osapuoli.nimi)
        }
        yhteiso_asiakkaat = {
            osapuoli for osapuoli in omistajat if is_yhteiso(osapuoli.nimi)
        }
        if asoy_asiakkaat:
            asiakas = min(asoy_asiakkaat, key=lambda x: x.nimi)
        elif company_asiakkaat:
            asiakas = min(company_asiakkaat, key=lambda x: x.nimi)
        elif yhteiso_asiakkaat:
            asiakas = min(yhteiso_asiakkaat, key=lambda x: x.nimi)
        elif asukkaat:
            asiakas = min(asukkaat, key=lambda x: x.nimi)
        else:
            asiakas = min(omistajat, key=lambda x: x.nimi)
    else:
        if asukkaat:
            asiakas = min(asukkaat, key=lambda x: x.nimi)
        else:
            asiakas = None
            
    if asiakas:
        kohde_display_name = form_display_name(
            Yhteystieto(
                asiakas.nimi,
                asiakas.katuosoite,
                asiakas.ytunnus,
                asiakas.henkilotunnus,
            )
        )
    else:
        kohde_display_name = "Tuntematon"
        
    alkupvm = poimintapvm
    if old_kohde:
        alkupvm = parse_alkupvm_for_kohde(
            session, rakennus_ids, old_kohde.alkupvm, poimintapvm
        )
        
    # Jos loppupvm ei ole määritelty, käytetään oletusarvoa
    if loppupvm is None:
        loppupvm = date(2100, 12, 31)
        
    kohde = Kohde(
        nimi=kohde_display_name,
        kohdetyyppi=codes.kohdetyypit[KohdeTyyppi.KIINTEISTO],
        alkupvm=alkupvm,
        loppupvm=loppupvm,
    )
    session.add(kohde)
    # we need to get the id for the kohde from db
    session.flush()

    # create dependent objects
    for rakennus_id in rakennus_ids:
        kohteen_rakennus = KohteenRakennukset(
            rakennus_id=rakennus_id, kohde_id=kohde.id
        )
        session.add(kohteen_rakennus)
    # save all asukkaat as asiakas
    for osapuoli in asukkaat:
        asiakas = KohteenOsapuolet(
            osapuoli_id=osapuoli.id,
            kohde_id=kohde.id,
            osapuolenrooli=codes.osapuolenroolit[OsapuolenrooliTyyppi.VANHIN_ASUKAS]
        )
        session.add(asiakas)
    # save all omistajat as yhteystiedot, even if they also live in the building.
    # This is needed so the kohde can be identified by owner at later import.
    for osapuoli in omistajat:
        yhteystieto = KohteenOsapuolet(
            osapuoli_id=osapuoli.id,
            kohde_id=kohde.id,
            osapuolenrooli=codes.osapuolenroolit[
                OsapuolenrooliTyyppi.OMISTAJA
            ],
        )
        session.add(yhteystieto)
    return kohde


def old_kohde_for_buildings(
    session: "Session", rakennus_ids: "List[int]", poimintapvm: "datetime.date"
):
    kohde_query = (
        select(Kohde)
        .join(KohteenRakennukset)
        .filter(
            KohteenRakennukset.rakennus_id.in_(rakennus_ids),
            Kohde.loppupvm == poimintapvm - timedelta(days=1),
        )
    )
    old_kohde_id = session.execute(kohde_query).scalar()
    return old_kohde_id


def set_old_kohde_loppupvm(session: "Session", kohde_id: int, loppupvm: "datetime.date"):
    session.execute(
        update(Kohde)
        .where(Kohde.id == kohde_id)
        .values(loppupvm=loppupvm)
    )
    session.commit()


def set_paatos_loppupvm_for_old_kohde(
    session: "Session", kohde_id: int, loppupvm: "datetime.date"
):
    """
    Asettaa päätösten loppupäivämäärän vanhan kohteen päätöksille.
    """
    # Muunnetaan subquery explisiittiseksi select-lauseeksi
    rakennus_ids = select(KohteenRakennukset.rakennus_id).where(
        KohteenRakennukset.kohde_id == kohde_id
    )

    session.query(Viranomaispaatokset).filter(
        and_(
            Viranomaispaatokset.rakennus_id.in_(rakennus_ids.scalar_subquery()),
            Viranomaispaatokset.alkupvm <= loppupvm
        )
    ).update({Viranomaispaatokset.loppupvm: loppupvm}, synchronize_session=False)
    session.commit()


def update_kompostori(
    session: "Session", old_kohde_id: int, loppupvm: "datetime.date", new_kohde_id: int
):
    """
    Päivittää kompostorien tiedot kohteen vaihtuessa.
    """
    # Haetaan vanhan kohteen kompostorit
    kompostori_ids = select(KompostorinKohteet.kompostori_id).where(
        KompostorinKohteet.kohde_id == old_kohde_id
    )

    # Asetetaan loppupvm
    session.query(Kompostori).filter(
        and_(
            Kompostori.id.in_(kompostori_ids.scalar_subquery()),
            Kompostori.alkupvm <= loppupvm
        )
    ).update({Kompostori.loppupvm: loppupvm}, synchronize_session=False)

    # Haetaan kompostorit jotka jatkuvat loppupvm:n jälkeen
    kompostori_id_by_date = select(Kompostori.id).where(
        and_(
            Kompostori.id.in_(kompostori_ids.scalar_subquery()),
            Kompostori.alkupvm > loppupvm
        )
    )

    # Haetaan kompostorien osapuolet
    kompostori_osapuoli_ids = select(Kompostori.osapuoli_id).where(
        Kompostori.id.in_(kompostori_id_by_date.scalar_subquery())
    )

    # Päivitetään osapuolten kohde
    session.query(KohteenOsapuolet).filter(
        and_(
            KohteenOsapuolet.osapuoli_id.in_(kompostori_osapuoli_ids.scalar_subquery()),
            KohteenOsapuolet.kohde_id == old_kohde_id,
            KohteenOsapuolet.osapuolenrooli_id == 311
        )
    ).update({KohteenOsapuolet.kohde_id: new_kohde_id}, synchronize_session=False)

    # Päivitetään KompostorinKohteet
    session.query(KompostorinKohteet).filter(
        and_(
            KompostorinKohteet.kompostori_id.in_(kompostori_id_by_date.scalar_subquery()),
            KompostorinKohteet.kohde_id == old_kohde_id,
        )
    ).update({KompostorinKohteet.kohde_id: new_kohde_id}, synchronize_session=False)
    
    session.commit()


def move_sopimukset_and_kuljetukset_to_new_kohde(
    session: "Session", alkupvm: "datetime.date", old_kohde_id: int, new_kohde_id: int
):
    session.execute(
        update(Sopimus)
        .where(Sopimus.kohde_id == old_kohde_id)
        .where(Sopimus.loppupvm >= alkupvm)
        .values(kohde_id=new_kohde_id)
    )
    session.execute(
        update(Kuljetus)
        .where(Kuljetus.kohde_id == old_kohde_id)
        .where(Kuljetus.loppupvm >= alkupvm)
        .values(kohde_id=new_kohde_id)
    )
    session.commit()


def update_or_create_kohde_from_buildings(
    session: Session,
    dvv_rakennustiedot: Dict[int, Rakennustiedot],
    rakennukset: Set[Rakennustiedot],
    asukkaat: Set[Osapuoli],
    omistajat: Set[Osapuoli],
    poimintapvm: Optional[datetime.date],
    loppupvm: Optional[datetime.date]
) -> Kohde:
    """
    Optimoitu versio kohteen päivitys/luontifunktiosta.
    Luo uuden kohteen tai päivittää olemassa olevaa annettujen rakennusten perusteella.

    Toiminta:
    1. Hakee rakennusten perusteella mahdollisen olemassa olevan kohteen
    2. Jos kohdetta ei löydy, luo uuden
    3. Jos kohde löytyy, päivittää sen tiedot
    4. Käsittelee vanhaan kohteeseen liittyvät tietojen siirrot ja päivitykset

    Optimoinnit:
    - Käyttää eksplisiittisiä join-määrittelyjä kyselyissä
    - Vähentää tietokantakyselyiden määrää kokoamalla tietoja muistiin
    - Käyttää tehokkaita bulk-operaatioita päivityksiin
    - Minimoi sarakkeiden päivitykset
    
    Args:
        session: Tietokantaistunto
        dvv_rakennustiedot: Rakennustietojen lookup-taulukko
        rakennukset: Käsiteltävät rakennukset
        asukkaat: Rakennusten asukkaat 
        omistajat: Rakennusten omistajat
        poimintapvm: Uuden kohteen alkupvm
        loppupvm: Uuden kohteen loppupvm

    Returns:
        Kohde: Luotu tai päivitetty kohde
    """
    rakennus_ids = {rakennustiedot[0].id for rakennustiedot in rakennukset}
    asukas_ids = {osapuoli.id for osapuoli in asukkaat}
    omistaja_ids = {osapuoli.id for osapuoli in omistajat}
    
    logger = logging.getLogger(__name__)
    print(
        f"Etsitään kohdetta: rakennukset={rakennus_ids}, "
        f"asukkaat={asukas_ids}, omistajat={omistaja_ids}"
    )
    logger.debug(
        f"Etsitään kohdetta: rakennukset={rakennus_ids}, "
        f"asukkaat={asukas_ids}, omistajat={omistaja_ids}"
    )

    # Hae olemassa oleva kohde eksplisiittisillä join-määrittelyillä
    kohde_query = (
        select(Kohde.id, Osapuoli.nimi)
        .select_from(Kohde)
        .join(KohteenRakennukset, KohteenRakennukset.kohde_id == Kohde.id)
        .join(KohteenOsapuolet, KohteenOsapuolet.kohde_id == Kohde.id, isouter=True)
        .join(Osapuoli, Osapuoli.id == KohteenOsapuolet.osapuoli_id, isouter=True)
        .where(KohteenRakennukset.rakennus_id.in_(rakennus_ids))
    )
    
    # Jos on aikarajaus, lisää se kyselyyn
    if poimintapvm and loppupvm:
        kohde_query = kohde_query.where(
            Kohde.voimassaolo.overlaps(DateRange(poimintapvm, loppupvm))
        )

    try:
        kohteet = session.execute(kohde_query).all()
    except NoResultFound:
        kohteet = []

    # Jos kohdetta ei löydy, luo uusi
    if not kohteet:
        print("Kohdetta ei löytynyt, luodaan uusi")
        logger.debug("Kohdetta ei löytynyt, luodaan uusi")
        
        # Tarkista mahdollinen vanha kohde
        old_kohde = None
        if poimintapvm:
            old_kohde = old_kohde_for_buildings(session, list(rakennus_ids), poimintapvm)
            
        # Määritä alkupvm
        alkupvm = poimintapvm
        if old_kohde:
            alkupvm = parse_alkupvm_for_kohde(
                session, rakennus_ids, old_kohde.alkupvm, poimintapvm
            )
            
        # Luo uusi kohde
        new_kohde = create_new_kohde_from_buildings(
            session,
            rakennus_ids,
            asukkaat,
            omistajat,
            alkupvm,
            loppupvm,
            old_kohde if 'old_kohde' in locals() else None
        )
        
        # Käsittele vanhan kohteen tiedot
        if new_kohde and poimintapvm and old_kohde:
            logger.debug(f"Päivitetään vanhan kohteen {old_kohde.id} tiedot")
            update_old_kohde_data(
                session,
                old_kohde.id,
                new_kohde.id,
                new_kohde.alkupvm
            )
            
        return new_kohde

    # Jos kohde löytyi, päivitä sen tiedot
    found_kohde = session.get(Kohde, kohteet[0][0])
    logger.debug(f"Löydettiin olemassa oleva kohde {found_kohde.id}")

    # Päivitä kohteen voimassaoloaika
    needs_update = False
    if not poimintapvm or (found_kohde.alkupvm and poimintapvm < found_kohde.alkupvm):
        found_kohde.alkupvm = poimintapvm
        needs_update = True
        
    if poimintapvm and found_kohde.loppupvm == poimintapvm - timedelta(days=1):
        found_kohde.loppupvm = None
        needs_update = True

    if needs_update:
        session.flush()
        
    return found_kohde


def get_or_create_kohteet_from_rakennustiedot(
    session: Session,
    dvv_rakennustiedot: Dict[int, "Rakennustiedot"],
    building_sets: List[Set["Rakennustiedot"]],
    owners_by_rakennus_id: Dict[int, Set["Osapuoli"]],
    inhabitants_by_rakennus_id: Dict[int, Set["Osapuoli"]],
    poimintapvm: Optional[datetime.date],
    loppupvm: Optional[datetime.date]
) -> List[Kohde]:
    """
    Luo kohteet rakennusryhmien perusteella ja lisää niihin apurakennukset.
    
    Args:
        session: Tietokantaistunto
        dvv_rakennustiedot: Sanakirja rakennustiedoista
        building_sets: Lista rakennusryhmistä
        owners_by_rakennus_id: Sanakirja rakennusten omistajista
        inhabitants_by_rakennus_id: Sanakirja rakennusten asukkaista
        poimintapvm: Uusien kohteiden alkupäivämäärä
        loppupvm: Uusien kohteiden loppupäivämäärä

    Returns:
        Lista luoduista kohteista
    """
    logger = logging.getLogger(__name__)
    print("Luodaan kohteet rakennusryhmille...")
    logger.info("\nLuodaan kohteet rakennusryhmille...")

    # Lisää apurakennukset kuhunkin rakennusryhmään
    building_sets = add_auxiliary_buildings_materialized(
        dvv_rakennustiedot,
        building_sets,
        session  # Välitetään session-parametri
    )
    
    kohteet = []
    for building_set in building_sets:
        owners = set().union(
            *[
                owners_by_rakennus_id[rakennustiedot[0].id]
                for rakennustiedot in building_set
            ]
        )
        inhabitants = set().union(
            *[
                inhabitants_by_rakennus_id[rakennustiedot[0].id]
                for rakennustiedot in building_set
            ]
        )

        kohde = update_or_create_kohde_from_buildings(
            session,
            dvv_rakennustiedot,
            building_set,
            inhabitants,
            owners,
            poimintapvm,
            loppupvm,
        )
        kohteet.append(kohde)
        
    logger.info(f"Luotu {len(kohteet)} kohdetta")
    return kohteet


def _match_address(first: "Osoite", second: "Osoite"):
    """
    Determines whether two buildings are at the same address. Osoite is
    the many to many table between Rakennus and Katu.
    """
    return first.katu_id == second.katu_id and first.osoitenumero == second.osoitenumero


def _match_addresses(first: "Set[Osoite]", second: "Set[Osoite]"):
    """
    Determines whether address sets contain any common addresses.
    """
    for osoite in first:
        for address in second:
            if _match_address(osoite, address):
                print("Yhteinen osoite löytyi.")
                return True
    print("Ei yhteistä osoitetta.")
    return False


def get_or_create_kohteet_from_kiinteistot(
    session: "Session",
    kiinteistotunnukset: "Select", 
    poimintapvm: "Optional[datetime.date]",
    loppupvm: "Optional[datetime.date]",
) -> "List[Kohde]":
    """
    Luo vähintään yksi kohde jokaisesta kiinteistötunnuksesta, jonka select-kysely palauttaa,
    jos kiinteistotunnuksella on rakennuksia ilman olemassa olevaa kohdetta annetulle aikajaksolle.

    Prosessi:
    1. Erotellaan kiinteistöjen rakennukset klustereihin etäisyyden perusteella
       - Jotkin kiinteistöt voivat sisältää kaukana toisistaan olevia rakennuksia
       - Osoitteet voivat olla virheellisiä, joten erottelu tehdään etäisyyden perusteella
    
    2. Käsitellään samassa klusterissa olevat rakennukset:
       - Jos kaikki rakennukset ovat saman asunto-osakeyhtiön omistamia, luodaan yksi kohde
       - Muuten käsitellään omistajittain:
         * Ensimmäinen kohde sisältää eniten rakennuksia omistavan omistajan rakennukset
         * Toinen kohde sisältää toiseksi eniten rakennuksia omistavan rakennukset
         * Prosessi jatkuu kunnes kaikilla rakennuksilla on kohde
         * Ilman omistajaa olevat rakennukset saavat oman kohteensa

    3. Lopuksi erotellaan saman omistajan rakennukset osoitteen perusteella,
       paitsi jos kyseessä on asunto-osakeyhtiö.

    Args:
        session: Tietokantaistunto
        kiinteistotunnukset: Select-kysely joka palauttaa kiinteistötunnukset
        poimintapvm: Uusien kohteiden alkupäivämäärä
        loppupvm: Uusien kohteiden loppupäivämäärä (None = ei loppupäivää)

    Returns:
        Lista luoduista kohteista

    Raises:
        SQLAlchemyError: Jos tietokantaoperaatioissa tapahtuu virhe
    """
    logger = logging.getLogger(__name__)

    # Seurattavat PRT-tunnukset lokitusta varten
    log_prt_in = (
        '103074869S', '103074870T', '103074871U', '103074872V',
        '103074873W', '103074874X', '103074875Y', '1030748760',
        '1030748771', '1030748782'
    )

    with open('kiinteisto_debug.log', 'a', encoding='utf-8') as f:
        # Lataa kiinteistötunnukset ja logita määrä
        kiinteistotunnukset = [
            result[0] for result in session.execute(kiinteistotunnukset).all()
        ]
        logger.info(f"{len(kiinteistotunnukset)} tuotavaa kiinteistötunnusta löydetty")
        
        # Hae DVV:n rakennustiedot ilman kohdetta ja logita määrä
        dvv_rakennustiedot = get_dvv_rakennustiedot_without_kohde(
            session, poimintapvm, loppupvm
        )
        logger.info(
            f"Löydetty {len(dvv_rakennustiedot)} DVV-rakennusta ilman voimassaolevaa kohdetta"
        )

        # Ryhmittele rakennustiedot kiinteistötunnuksittain
        rakennustiedot_by_kiinteistotunnus = defaultdict(set)
        for rakennus, vanhimmat, omistajat, osoitteet in dvv_rakennustiedot.values():
            rakennustiedot_by_kiinteistotunnus[rakennus.kiinteistotunnus].add(
                (rakennus, vanhimmat, omistajat, osoitteet)
            )

        # Hae omistajatiedot ja muodosta lookup-taulut
        rakennus_owners = session.execute(
            select(RakennuksenOmistajat.rakennus_id, Osapuoli)
            .join(Osapuoli, RakennuksenOmistajat.osapuoli_id == Osapuoli.id)
        ).all()
        
        owners_by_rakennus_id = defaultdict(set)  # rakennus_id -> {omistajat}
        rakennus_ids_by_owner_id = defaultdict(set)  # omistaja.id -> {rakennus_id:t}
        for (rakennus_id, owner) in rakennus_owners:
            owners_by_rakennus_id[rakennus_id].add(owner)
            rakennus_ids_by_owner_id[owner.id].add(rakennus_id)

        # Hae asukastiedot ja muodosta lookup-taulu
        rakennus_inhabitants = session.execute(
            select(RakennuksenVanhimmat.rakennus_id, Osapuoli)
            .join(Osapuoli, RakennuksenVanhimmat.osapuoli_id == Osapuoli.id)
        ).all()
        
        inhabitants_by_rakennus_id = defaultdict(set)  # rakennus_id -> {asukkaat}
        for (rakennus_id, inhabitant) in rakennus_inhabitants:
            inhabitants_by_rakennus_id[rakennus_id].add(inhabitant)

        # Hae osoitetiedot ja muodosta lookup-taulu
        rakennus_addresses = session.execute(
            select(Rakennus.id, Osoite)
            .join(Osoite, Rakennus.id == Osoite.rakennus_id)
        ).all()
        
        addresses_by_rakennus_id = defaultdict(set)  # rakennus_id -> {osoitteet}
        for (rakennus_id, address) in rakennus_addresses:
            addresses_by_rakennus_id[rakennus_id].add(address)

        # Lista muodostettavista rakennusryhmistä
        building_sets: List[Set[Rakennustiedot]] = []

        # Käsittele kaikki kiinteistöt
        for kiinteistotunnus in kiinteistotunnukset:
            # Tarkista onko seurattavia rakennuksia tällä kiinteistöllä
            tracked_buildings = any(
                r[0].prt in log_prt_in 
                for r in rakennustiedot_by_kiinteistotunnus[kiinteistotunnus]
            )
            
            if tracked_buildings:
                f.write("\n" + "="*80 + "\n")
                f.write(f"{datetime.datetime.now()}: Käsitellään kiinteistö {kiinteistotunnus}\n")
                f.write("Rakennukset:\n")
                for r in rakennustiedot_by_kiinteistotunnus[kiinteistotunnus]:
                    f.write(f"- {r[0].prt}\n")

            # Kerää kiinteistön rakennukset
            rakennustiedot_to_add = rakennustiedot_by_kiinteistotunnus[kiinteistotunnus]

            # 1. Jaa rakennukset klustereihin etäisyyden perusteella
            clustered_rakennustiedot = _cluster_rakennustiedot(
                rakennustiedot_to_add, DISTANCE_LIMIT
            )

            if tracked_buildings:
                f.write("\nMuodostuneet klusterit:\n")
                for i, cluster in enumerate(clustered_rakennustiedot, 1):
                    f.write(f"Klusteri {i}:\n")
                    for r in cluster:
                        f.write(f"- {r[0].prt}\n")

            # Käsittele klusterit yksitellen
            for rakennustiedot_cluster in clustered_rakennustiedot:
                cluster_ids = {rt[0].id for rt in rakennustiedot_cluster}
                
                if tracked_buildings:
                    f.write("\nKäsitellään klusteri:\n")
                    f.write(f"Rakennukset: {cluster_ids}\n")

				# Kerää klusterin rakennusten omistajat ja tarkista asoy
                cluster_owners = defaultdict(set)  # owner_id -> {rakennus_id:t}
                owner_names = set()  # Uniikit omistajanimet
                asoy_owners = set()  # Asoy-tyyppiset omistajat
                
                for rakennus_id in cluster_ids:
                    if rakennus_id in owners_by_rakennus_id:
                        for owner in owners_by_rakennus_id[rakennus_id]:
                            cluster_owners[owner.id].add(rakennus_id)
                            owner_names.add(owner.nimi.upper())
                            if is_asoy(owner.nimi):
                                asoy_owners.add(owner)

                # 2. Tarkista onko koko klusteri saman asoy:n omistuksessa
                if len(owner_names) == 1 and asoy_owners:
                    if tracked_buildings:
                        f.write(
                            f"\nYksi asoy ({next(iter(asoy_owners)).nimi}) omistaa "
                            f"kaikki klusterin rakennukset, luodaan yksi kohde\n"
                        )
                    
                    # Koko klusteri yhdeksi kohteeksi, asoy:lla kaikki osoitteet sallittu
                    rakennustiedot_group = {
                        dvv_rakennustiedot[id]
                        for id in cluster_ids
                        if id in dvv_rakennustiedot
                    }
                    if rakennustiedot_group:
                        building_sets.append(rakennustiedot_group)
                    continue  # Siirry seuraavaan klusteriin

                # 3. Jaa muut kuin yhden asoy:n klusterit omistajien ja osoitteiden mukaan
                if tracked_buildings:
                    f.write("\nEi yhden asoy:n klusteri, jaetaan omistajien ja osoitteiden mukaan\n")

                remaining_ids = set(cluster_ids)
                
                while remaining_ids:
                    # 3.1 Jaa ensin omistajien mukaan
                    if cluster_owners:
                        # Aloita suurimmasta omistajaryhmästä
                        owner_id, owner_buildings = max(
                            cluster_owners.items(),
                            key=lambda x: len(x[1])
                        )
                        buildings_to_process = remaining_ids & owner_buildings
                        
                        # Tarkista onko omistaja asoy
                        owner = next(
                            owner for owner in owners_by_rakennus_id[next(iter(owner_buildings))]
                            if owner.id == owner_id
                        )
                        is_owner_asoy = is_asoy(owner.nimi)
                    else:
                        # Jos ei omistajia, käsittele kaikki jäljellä olevat
                        buildings_to_process = remaining_ids
                        is_owner_asoy = False

                    if tracked_buildings:
                        f.write(f"\nKäsitellään rakennukset: {buildings_to_process}\n")
                        if is_owner_asoy:
                            f.write(f"Omistaja on asoy ({owner.nimi}), ei jaeta osoitteen mukaan\n")

                    # 3.2 Jos ei ole asoy, jaa vielä osoitteen mukaan
                    if not is_owner_asoy:
                        buildings_by_address = defaultdict(set)
                        for building_id in buildings_to_process:
                            for address in addresses_by_rakennus_id.get(building_id, set()):
                                key = (address.katu_id, address.osoitenumero)
                                buildings_by_address[key].add(building_id)

                        # Käsittele osoiteryhmät suuruusjärjestyksessä
                        while buildings_to_process:
                            if buildings_by_address:
                                # Aloita suurimmasta osoiteryhmästä
                                _, address_group = max(
                                    buildings_by_address.items(),
                                    key=lambda x: len(x[1])
                                )
                                current_group = buildings_to_process & address_group
                            else:
                                # Jos ei osoitteita, käsittele kaikki kerralla
                                current_group = buildings_to_process

                            # Luo rakennusryhmä
                            rakennustiedot_group = {
                                dvv_rakennustiedot[id] 
                                for id in current_group 
                                if id in dvv_rakennustiedot
                            }
                            
                            if rakennustiedot_group:
                                building_sets.append(rakennustiedot_group)

                            # Päivitä jäljellä olevat rakennukset
                            buildings_to_process -= current_group
                            remaining_ids -= current_group

                            # Päivitä osoiteryhmät
                            if buildings_by_address:
                                buildings_by_address = {
                                    addr: buildings - current_group
                                    for addr, buildings in buildings_by_address.items()
                                    if buildings - current_group
                                }
                    else:
                        # Asoy - kaikki omistajan rakennukset samaan ryhmään
                        rakennustiedot_group = {
                            dvv_rakennustiedot[id] 
                            for id in buildings_to_process 
                            if id in dvv_rakennustiedot
                        }
                        if rakennustiedot_group:
                            building_sets.append(rakennustiedot_group)
                        remaining_ids -= buildings_to_process

                    # Päivitä omistajaryhmät
                    if cluster_owners:
                        cluster_owners.pop(owner_id, None)

        # Lokita lopputulos jos käsiteltiin seurattavia rakennuksia
        if any(any(r[0].prt in log_prt_in for r in bs) for bs in building_sets):
            f.write("\nLopulliset rakennusryhmät:\n")
            for i, building_set in enumerate(building_sets, 1):
                if any(r[0].prt in log_prt_in for r in building_set):
                    f.write(f"\nRyhmä {i}:\n")
                    for r in building_set:
                        f.write(f"- {r[0].prt}\n")

        # Luo kohteet rakennusryhmien perusteella
        kohteet = get_or_create_kohteet_from_rakennustiedot(
            session,
            dvv_rakennustiedot,
            building_sets,
            owners_by_rakennus_id,
            inhabitants_by_rakennus_id,
            poimintapvm,
            loppupvm,
        )

        # Lokita luodut kohteet jos käsiteltiin seurattavia rakennuksia
        if any(any(r[0].prt in log_prt_in for r in bs) for bs in building_sets):
            f.write("\nLuodut kohteet:\n")
            for kohde in kohteet:
                if any(r.prt in log_prt_in for r in kohde.rakennus_collection):
                    f.write(f"\nKohde {kohde.id}:\n")
                    f.write(f"Nimi: {kohde.nimi}\n")
                    f.write("Rakennukset:\n")
                    for r in kohde.rakennus_collection:
                        f.write(f"- {r.prt}\n")

        return kohteet

def get_or_create_single_asunto_kohteet(
    session: "Session",
    poimintapvm: "Optional[datetime.date]",
    loppupvm: "Optional[datetime.date]",
) -> "List[Kohde]":
    """
    Hae tai luo kohteet kaikille yhden asunnon taloille ja paritaloille, joilla ei ole
    kohdetta määritellyllä aikavälillä. Huomioi myös talot, joissa ei ole asukkaita.

    Jos kiinteistöllä on useita asuttuja rakennuksia, sitä ei tuoda tässä.
    """
    print(" ")
    print("----- LUODAAN YHDEN ASUNNON KOHTEET -----")

    # Älä tuo rakennuksia, joilla on jo olemassa olevia kohteita
    if loppupvm is None:
        rakennus_id_with_current_kohde = (
            select(Rakennus.id)
            .join(KohteenRakennukset)
            .join(Kohde)
            .filter(poimintapvm == Kohde.alkupvm)
        )
    else:
        rakennus_id_with_current_kohde = (
            select(Rakennus.id)
            .join(KohteenRakennukset)
            .join(Kohde)
            .filter(Kohde.voimassaolo.overlaps(DateRange(poimintapvm, loppupvm)))
        )

    rakennus_id_without_kohde = (
        select(Rakennus.id)
        .filter(
            or_(
                Rakennus.rakennuksenkayttotarkoitus == codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.YKSITTAISTALO],
                Rakennus.rakennuksenkayttotarkoitus == codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.PARITALO]
            )
        )
        .filter(~Rakennus.id.in_(rakennus_id_with_current_kohde))
        # Älä tuo rakennuksia, jotka on poistettu DVV:n tiedoista
        .filter(
            or_(
                Rakennus.kaytostapoisto_pvm.is_(None),
                Rakennus.kaytostapoisto_pvm > poimintapvm,
            )
        )
    )

    single_asunto_kiinteistotunnus = (
        select(
            Rakennus.kiinteistotunnus,
            func.count(Rakennus.id),
        )
        .filter(Rakennus.id.in_(rakennus_id_without_kohde))
        .group_by(Rakennus.kiinteistotunnus)
        .having(func.count(Rakennus.id) == 1)
    )

    return get_or_create_kohteet_from_kiinteistot(
        session, single_asunto_kiinteistotunnus, poimintapvm, loppupvm
    )

def determine_kohdetyyppi(rakennus: Rakennus) -> KohdeTyyppi:
    """
    Määrittää kohteen tyypin rakennuksen tietojen perusteella.
    """
    # Tarkista rakennusluokka 2018
    if rakennus.rakennusluokka_2018:
        if '0110' <= rakennus.rakennusluokka_2018 <= '0211':
            return KohdeTyyppi.ASUINKIINTEISTO
    # Jos ei rakennusluokkaa, tarkista käyttötarkoitus
    elif '011' <= rakennus.rakennuksenkayttotarkoitus <= '041':
        return KohdeTyyppi.ASUINKIINTEISTO
        
    # Tarkista muut asuinkiinteistön kriteerit
    if (rakennus.huoneistomaara > 0 or
        bool(rakennus.asukkaat) or
        rakennus.rakennuksenkayttotarkoitus == '1910'):  # Sauna
        return KohdeTyyppi.ASUINKIINTEISTO
        
    return KohdeTyyppi.MUU


def get_or_create_multiple_and_uninhabited_kohteet(
    session: "Session",
    poimintapvm: "Optional[datetime.date]",
    loppupvm: "Optional[datetime.date]",
) -> "List[Kohde]":
    """
    Luo kohteet kaikille kiinteistötunnuksille, joilla on rakennuksia ilman kohdetta
    määritellylle aikavälille. Tämä funktio käsittelee jäljellä olevat rakennukset,
    mukaan lukien useita rakennuksia sisältävät kiinteistöt ja asumattomat rakennukset.
    """
    print(" ")
    print("----- LUODAAN JÄLJELLÄ OLEVAT KOHTEET -----")

    rakennus_id_with_current_kohde = (
        select(Rakennus.id)
        .join(KohteenRakennukset)
        .join(Kohde)
        .filter(Kohde.voimassaolo.overlaps(DateRange(poimintapvm, loppupvm)))
    )
    
    kiinteistotunnus_without_kohde = (
        select(Rakennus.kiinteistotunnus)
        .filter(~Rakennus.id.in_(rakennus_id_with_current_kohde))
        # Älä tuo rakennuksia, jotka on poistettu DVV:n tiedoista
        .filter(
            or_(
                Rakennus.kaytostapoisto_pvm.is_(None),
                Rakennus.kaytostapoisto_pvm > poimintapvm,
            )
        )
        .group_by(Rakennus.kiinteistotunnus)
    )

    return get_or_create_kohteet_from_kiinteistot(
        session, kiinteistotunnus_without_kohde, poimintapvm, loppupvm
    )


def _should_have_perusmaksu_kohde(rakennus: "Rakennus"):
    """
    Determines which buildings should be combined using perusmaksu data.
    """
    return rakennus.rakennuksenkayttotarkoitus in (
        codes.rakennuksenkayttotarkoitukset[
            RakennuksenKayttotarkoitusTyyppi.KERROSTALO
        ],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.RIVITALO],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.LUHTITALO],
        codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.KETJUTALO],
    )


def batch_update_old_kohde_data(session, updates):
    """
    Optimoitu versio batch-päivityksistä joka säilyttää alkuperäisen logiikan.
    Käyttää synchronize_session=False nopeuttamiseen missä turvallista.
    """
    if not updates:
        return

    # Kerää old_kohde_ids vain niistä updatesista missä old_kohde_id != new_kohde_id
    updates_by_old_id = {}
    for old_id, new_id, new_alkupvm in updates:
        if old_id != new_id:  # Käsitellään vain jos oikeasti siirretään uudelle kohteelle
            updates_by_old_id[old_id] = (new_id, new_alkupvm)
    
    if not updates_by_old_id:
        return
        
    old_kohde_ids = list(updates_by_old_id.keys())
    
    # 1. Aseta vanhojen kohteiden loppupvm (päivä ennen uuden alkupvm)
    loppupvm_values = {
        old_id: (new_alkupvm - timedelta(days=1))
        for old_id, (new_id, new_alkupvm) in updates_by_old_id.items()
    }
    
    stmt = (
        update(Kohde)
        .where(Kohde.id.in_(old_kohde_ids))
        .values({
            Kohde.loppupvm: case(
                whens=loppupvm_values,
                value=Kohde.id
            )
        })
        .execution_options(synchronize_session=False)
    )
    session.execute(stmt)

    # 2. Siirrä sopimukset ja kuljetukset
    for model in [Sopimus, Kuljetus]:
        for old_id, (new_id, new_alkupvm) in updates_by_old_id.items():
            stmt = (
                update(model)
                .where(
                    model.kohde_id == old_id,
                    model.loppupvm >= new_alkupvm
                )
                .values(kohde_id=new_id)
                .execution_options(synchronize_session=False)
            )
            session.execute(stmt)

    # 3. Päivitä viranomaispäätökset
    # Hae ensin kaikki rakennukset vanhoilta kohteilta
    rakennus_ids = session.execute(
        select(KohteenRakennukset.rakennus_id)
        .where(KohteenRakennukset.kohde_id.in_(old_kohde_ids))
    ).scalars().all()

    if rakennus_ids:
        # Päivitä päätökset rakennuksittain
        for old_id, (new_id, new_alkupvm) in updates_by_old_id.items():
            kohteen_rakennus_ids = session.execute(
                select(KohteenRakennukset.rakennus_id)
                .where(KohteenRakennukset.kohde_id == old_id)
            ).scalars().all()
            
            if kohteen_rakennus_ids:
                loppupvm = new_alkupvm - timedelta(days=1)
                stmt = (
                    update(Viranomaispaatokset)
                    .where(
                        Viranomaispaatokset.rakennus_id.in_(kohteen_rakennus_ids),
                        Viranomaispaatokset.alkupvm <= loppupvm
                    )
                    .values(loppupvm=loppupvm)
                    .execution_options(synchronize_session=False)
                )
                session.execute(stmt)

    # 4. Päivitä kompostorit
    for old_id, (new_id, new_alkupvm) in updates_by_old_id.items():
        # Hae kohteen kompostorit
        kompostori_ids = session.execute(
            select(KompostorinKohteet.kompostori_id)
            .where(KompostorinKohteet.kohde_id == old_id)
        ).scalars().all()
        
        if kompostori_ids:
            loppupvm = new_alkupvm - timedelta(days=1)
            
            # Aseta loppupvm kompostoreille
            stmt = (
                update(Kompostori)
                .where(
                    Kompostori.id.in_(kompostori_ids),
                    Kompostori.alkupvm <= loppupvm
                )
                .values(loppupvm=loppupvm)
                .execution_options(synchronize_session=False)
            )
            session.execute(stmt)

            # Siirrä jatkuvat kompostorit uudelle kohteelle
            stmt = (
                update(KompostorinKohteet)
                .where(
                    KompostorinKohteet.kompostori_id.in_(kompostori_ids),
                    KompostorinKohteet.kohde_id == old_id,
                    Kompostori.alkupvm > loppupvm
                )
                .values(kohde_id=new_id)
                .execution_options(synchronize_session=False)
            )
            session.execute(stmt)
    
    session.commit()


def create_perusmaksurekisteri_kohteet(
    session: Session,
    perusmaksutiedosto: Path,
    poimintapvm: Optional[datetime.date],
    loppupvm: Optional[datetime.date]
) -> List[Kohde]:
    """
    Luo kohteet perusmaksurekisterin perusteella. Yhdistää samaan kohteeseen rakennukset,
    joilla on sama asiakasnumero perusmaksurekisterissä ja jotka ovat määriteltyjä talotyyppejä.
    
    Tarkistaa ensisijaisesti Rakennusluokitus 2018 mukaiset luokat:
    - 0110: Paritalot
    - 0210: Rivitalot
    - 0220: Ketjutalot
    - 0320: Luhtitalot
    - 0390: Muut asuinkerrostalot
    
    Jos 2018 luokka puuttuu, käytetään vanhempaa luokitusta:
    - 012: Kahden asunnon talot
    - 021: Rivitalot
    - 022: Ketjutalot
    - 032: Luhtitalot
    - 039: Muut asuinkerrostalot

    Lisäksi kohteeseen yhdistetään saunat ja piharakennukset, jos:
    - Sama omistaja/asukas kuin jollain ryhmän rakennuksista
    - Sama osoite kuin jollain ryhmän rakennuksista  
    - Sijainti max 300m päässä ryhmän rakennuksista

    Args:
        session: Tietokantaistunto
        perusmaksutiedosto: Polku perusmaksurekisterin Excel-tiedostoon
        poimintapvm: Uusien kohteiden alkupäivämäärä
        loppupvm: Uusien kohteiden loppupäivämäärä (None = ei loppupvm)

    Returns:
        List[Kohde]: Lista luoduista kohteista

    Raises:
        FileNotFoundError: Jos perusmaksutiedostoa ei löydy
        openpyxl.utils.exceptions.InvalidFileException: Jos tiedosto ei ole validi Excel
    """
    logger = logging.getLogger(__name__)
    logger.info("\nLuodaan perusmaksurekisterin kohteet...")

    # Hae DVV:n rakennustiedot rakennuksista joilla ei vielä ole kohdetta
    dvv_rakennustiedot = get_dvv_rakennustiedot_without_kohde(
        session, poimintapvm, loppupvm
    )
    logger.info(f"Löydettiin {len(dvv_rakennustiedot)} rakennusta ilman kohdetta")

    # Luo lookup PRT -> Rakennustiedot jatkojalostusta varten
    dvv_rakennustiedot_by_prt = {
        tiedot[0].prt: tiedot 
        for tiedot in dvv_rakennustiedot.values()
        if tiedot[0].prt  # Ohita jos PRT puuttuu
    }

    # Määrittele sallitut rakennustyypit
    # Rakennusluokka 2018 mukaiset luokat
    ALLOWED_TYPES_2018 = {
        '0110',  # Paritalot
        '0210',  # Rivitalot
        '0220',  # Ketjutalot
        '0320',  # Luhtitalot
        '0390'   # Muut asuinkerrostalot
    }
    
    # Vanhat luokat (käytetään jos 2018 luokka puuttuu)
    ALLOWED_TYPES_OLD = {
        '012',  # Paritalot
        '021',  # Rivitalot
        '022',  # Ketjutalot
        '032',  # Luhtitalot
        '039'   # Muut asuinkerrostalot
    }

    # Ryhmittele rakennukset asiakasnumeron mukaan
    buildings_to_combine = defaultdict(lambda: {"prt": set()})
    
    # Avaa perusmaksurekisteri
    logger.info("Avataan perusmaksurekisteri...")
    perusmaksut = load_workbook(filename=perusmaksutiedosto)
    sheet = perusmaksut["Tietopyyntö asiakasrekisteristä"]

    # Käsittele rivit ja kerää sallitut rakennukset
    logger.info("Käsitellään perusmaksurekisterin rivit...")
    rows_processed = 0
    buildings_found = 0

    for index, row in enumerate(sheet.values):
        if index == 0:  # Ohita otsikkorivi
            continue
        
        rows_processed += 1
        asiakasnumero = str(row[2])
        prt = str(row[3])

        # Hae rakennus ja tarkista tyyppi
        rakennus = session.query(Rakennus).filter(
            Rakennus.prt == prt
        ).first()

        if not rakennus:
            continue

        # Tarkista ensisijaisesti rakennusluokka 2018
        if rakennus.rakennusluokka_2018 in ALLOWED_TYPES_2018:
            buildings_to_combine[asiakasnumero]["prt"].add(prt)
            buildings_found += 1
        # Jos 2018 luokka puuttuu, tarkista vanha luokitus
        elif (rakennus.rakennusluokka_2018 is None and 
              rakennus.rakennuksenkayttotarkoitus_koodi in ALLOWED_TYPES_OLD):
            buildings_to_combine[asiakasnumero]["prt"].add(prt)
            buildings_found += 1

    logger.info(f"Käsitelty {rows_processed:,} riviä")
    logger.info(f"Löydetty {buildings_found:,} yhdistettävää rakennusta")

    # Muodosta rakennusryhmät samalla asiakasnumerolla olevista
    building_sets = []
    valid_sets = 0

    logger.info("\nMuodostetaan rakennusryhmät...")
    for asiakasnumero, data in buildings_to_combine.items():
        building_set = set()
        
        # Kerää rakennukset ryhmään
        for prt in data["prt"]:
            if prt in dvv_rakennustiedot_by_prt:
                rakennustiedot = dvv_rakennustiedot_by_prt[prt]
                building_set.add(rakennustiedot)

        # Lisää vain jos ryhmässä on rakennuksia
        if building_set:
            building_sets.append(building_set)
            valid_sets += 1

    logger.info(f"Muodostettu {valid_sets:,} rakennusryhmää")

    # Luo omistaja- ja asukastiedot lookupeja varten
    owners_by_rakennus_id = defaultdict(set)
    rakennus_owners = session.execute(
        select(RakennuksenOmistajat.rakennus_id, Osapuoli).join(
            Osapuoli, RakennuksenOmistajat.osapuoli_id == Osapuoli.id
        )
    ).all()
    for (rakennus_id, owner) in rakennus_owners:
        owners_by_rakennus_id[rakennus_id].add(owner)

    inhabitants_by_rakennus_id = defaultdict(set)
    rakennus_inhabitants = session.execute(
        select(RakennuksenVanhimmat.rakennus_id, Osapuoli).join(
            Osapuoli, RakennuksenVanhimmat.osapuoli_id == Osapuoli.id
        )
    ).all()
    for (rakennus_id, inhabitant) in rakennus_inhabitants:
        inhabitants_by_rakennus_id[rakennus_id].add(inhabitant)

    # Luo kohteet ja lisää apurakennukset
    logger.info("\nLuodaan kohteet ja lisätään apurakennukset...")
    kohteet = get_or_create_kohteet_from_rakennustiedot(
        session,
        dvv_rakennustiedot,
        building_sets,
        owners_by_rakennus_id,
        inhabitants_by_rakennus_id,
        poimintapvm,
        loppupvm
    )

    logger.info(f"\nLuotu {len(kohteet):,} kohdetta perusmaksurekisterin perusteella")
    return kohteet