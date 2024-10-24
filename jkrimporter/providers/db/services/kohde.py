import datetime
import re
import logging
from collections import defaultdict
from datetime import datetime as dt
from datetime import timedelta
from functools import lru_cache
from typing import TypeVar, DefaultDict, Set, List, Dict,TYPE_CHECKING,NamedTuple, FrozenSet, Optional, Generic, Iterable, Callable

from openpyxl import load_workbook
from psycopg2.extras import DateRange
from sqlalchemy import and_, exists, or_, select, update
from sqlalchemy import func as sqlalchemyFunc
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
        sqlalchemyFunc.lower(Osoite.posti_numero) == asiakas.haltija.osoite.postinumero,
        or_(
            sqlalchemyFunc.lower(Katu.katunimi_fi)
            == asiakas.haltija.osoite.katunimi.lower(),
            sqlalchemyFunc.lower(Katu.katunimi_sv)
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


def _cluster_rakennustiedot(
    rakennustiedot_to_cluster: "Set[Rakennustiedot]",
    distance_limit: int,
    existing_cluster: "Optional[Set[Rakennustiedot]]" = None,
) -> "List[Set[Rakennustiedot]]":
    """
    Return rakennustiedot clustered so that all buildings within distance_limit
    to any other building are joined to the same cluster.

    Optionally, we may specify an existing cluster that may not be split. This is
    meant for cases in which we know the buildings should belong together (e.g.
    because of perusmaksu, or grouping additional buildings to cluster).
    """
    clusters = []
    # start cluster from first remaining building (or existing cluster, if
    # provided).
    cluster = existing_cluster.copy() if existing_cluster else None
    while rakennustiedot_to_cluster:
        if not cluster:
            cluster = set([rakennustiedot_to_cluster.pop()])

        other_rakennustiedot_to_cluster = rakennustiedot_to_cluster.copy()
        while other_rakennustiedot_to_cluster:
            for other_rakennustiedot in other_rakennustiedot_to_cluster:
                if (
                    minimum_distance_of_buildings(
                        [rakennustiedot[0] for rakennustiedot in cluster]
                        + [other_rakennustiedot[0]]
                    )
                    < distance_limit
                ):
                    # found another building. add found building to cluster
                    # and start the loop anew.
                    cluster.add(other_rakennustiedot)
                    break
            else:
                # cluster finished! other_rakennustiedot_to_cluster did not
                # contain any buildings within set distance of cluster.
                break
            # found another building. remove found building from set to process
            # and start the loop anew.
            other_rakennustiedot_to_cluster.remove(other_rakennustiedot)
        # cluster finished! removing clustered buildings and starting the loop anew.
        clusters.append(cluster)
        rakennustiedot_to_cluster -= cluster
        cluster = None
    return clusters


def _add_auxiliary_buildings(
    dvv_rakennustiedot: Dict[int, Rakennustiedot],
    building_sets: List[Set[Rakennustiedot]]
) -> List[Set[Rakennustiedot]]:
    """
    Optimoitu versio apurakennusten lisäämisestä edistymisen seurannalla.
    """
    logger = logging.getLogger(__name__)
    logger.info("\nValmistellaan apurakennusten lisäämistä...")
    
    # Luo lookup-taulut
    nearby_buildings = create_nearby_buildings_lookup(dvv_rakennustiedot)
    logger.info(f"Löydettiin {sum(len(v) for v in nearby_buildings.values())} lähellä olevaa rakennusparia")
    
    # Rakenna muut lookup-taulut
    owner_lookup = defaultdict(set)
    address_lookup = defaultdict(set)
    
    for rakennus_id, (rakennus, _, omistajat, osoitteet) in dvv_rakennustiedot.items():
        for omistaja in omistajat:
            owner_lookup[omistaja.osapuoli_id].add(rakennus_id)
        for osoite in osoitteet:
            address_key = (osoite.katu_id, osoite.osoitenumero)
            address_lookup[address_key].add(rakennus_id)
    
    sets_to_return = []
    progress = BatchProgressTracker(len(building_sets), "Apurakennusten lisäys")
    
    for building_set in building_sets:
        set_to_return = building_set.copy()
        main_building_ids = {tiedot[0].id for tiedot in building_set}
        
        # Kerää päärakennusten tiedot
        main_building_owners = set()
        main_building_addresses = set()
        
        for building_data in building_set:
            main_building_owners.update(owner.osapuoli_id for owner in building_data[2])
            main_building_addresses.update(
                (address.katu_id, address.osoitenumero) 
                for address in building_data[3]
            )

        # Kerää potentiaaliset apurakennukset
        potential_auxiliary_buildings = set()
        for main_id in main_building_ids:
            potential_auxiliary_buildings.update(nearby_buildings[main_id])
        
        logger.debug(
            f"Käsitellään rakennusryhmä {main_building_ids}, "
            f"löydetty {len(potential_auxiliary_buildings)} potentiaalista apurakennusta"
        )
            
        # Käsittele potentiaaliset apurakennukset
        aux_added = 0
        for aux_id in potential_auxiliary_buildings:
            if aux_id in main_building_ids:
                continue
                
            aux_building_data = dvv_rakennustiedot[aux_id]
            
            if _is_significant_building(aux_building_data):
                continue
                
            aux_owner_ids = {owner.osapuoli_id for owner in aux_building_data[2]}
            aux_addresses = {
                (address.katu_id, address.osoitenumero) 
                for address in aux_building_data[3]
            }
            
            # Tarkista kriteerit ja lisää sopivat apurakennukset
            if _is_sauna(aux_building_data[0]):
                if not aux_owner_ids or (aux_owner_ids & main_building_owners):
                    set_to_return.add(aux_building_data)
                    aux_added += 1
                    continue
                    
            if (bool(aux_addresses & main_building_addresses) and
                (not aux_owner_ids or (aux_owner_ids & main_building_owners))):
                set_to_return.add(aux_building_data)
                aux_added += 1
                
        if aux_added > 0:
            logger.debug(f"Lisätty {aux_added} apurakennusta")
                
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


def parse_alkupvm_for_kohde(
    session: "Session",
    rakennus_ids: "List[int]",
    old_kohde_alkupvm: "datetime.date",
    poimintapvm: "Optional[datetime.date]",
):
    latest_omistaja_change = (
        session.query(sqlalchemyFunc.max(RakennuksenOmistajat.omistuksen_alkupvm))
        .filter(RakennuksenOmistajat.rakennus_id.in_(rakennus_ids))
        .scalar()
    )
    latest_vanhin_change = session.query(
        sqlalchemyFunc.max(RakennuksenVanhimmat.alkupvm)
    ).filter(RakennuksenVanhimmat.rakennus_id.in_(rakennus_ids)).scalar()

    if latest_omistaja_change is None and latest_vanhin_change is None:
        return poimintapvm

    latest_change = old_kohde_alkupvm
    if latest_omistaja_change is None and latest_vanhin_change is not None:
        latest_change = latest_vanhin_change
    elif latest_vanhin_change is None and latest_omistaja_change is not None:
        latest_change = latest_omistaja_change
    else:
        latest_change = max(latest_omistaja_change, latest_vanhin_change)

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
    Create combined kohde for the given list of building ids. Omistaja or asukas
    will be used for kohde name. Omistajat will be added as yhteystiedot.
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
    rakennus_ids = (
        session.query(KohteenRakennukset.rakennus_id)
        .filter(KohteenRakennukset.kohde_id == kohde_id)
        .subquery()
    )
    session.query(Viranomaispaatokset).filter(
        and_(
            Viranomaispaatokset.rakennus_id.in_(rakennus_ids),
            Viranomaispaatokset.alkupvm <= loppupvm
        )
    ).update({Viranomaispaatokset.loppupvm: loppupvm}, synchronize_session=False)
    session.commit()


def update_kompostori(
    session: "Session", old_kohde_id: int, loppupvm: "datetime.date", new_kohde_id: int
):
    # Set loppupvm
    kompostori_ids = (
        session.query(KompostorinKohteet.kompostori_id)
        .filter(KompostorinKohteet.kohde_id == old_kohde_id)
        .subquery()
    )
    session.query(Kompostori).filter(
        and_(
            Kompostori.id.in_(kompostori_ids),
            Kompostori.alkupvm <= loppupvm
        )
    ).update({Kompostori.loppupvm: loppupvm}, synchronize_session=False)

    # Move osapuoli to new kohde.
    kompostori_id_by_date = (
        session.query(Kompostori.id)
        .filter(
            and_(
                Kompostori.id.in_(kompostori_ids),
                Kompostori.alkupvm > loppupvm
            )
        )
        .subquery()
    )

    kompostori_osapuoli_ids = (
        session.query(Kompostori.osapuoli_id)
        .filter(Kompostori.id.in_(kompostori_id_by_date))
        .subquery()
    )
    session.query(KohteenOsapuolet).filter(
        and_(
            KohteenOsapuolet.osapuoli_id.in_(kompostori_osapuoli_ids),
            KohteenOsapuolet.kohde_id == old_kohde_id,
            KohteenOsapuolet.osapuolenrooli_id == 311
        )
    ).update({KohteenOsapuolet.kohde_id: new_kohde_id}, synchronize_session=False)

    # Update KompostorinKohteet
    session.query(KompostorinKohteet).filter(
        and_(
            KompostorinKohteet.kompostori_id.in_(kompostori_id_by_date),
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
    session: "Session",
    dvv_rakennustiedot: "Dict[int, Rakennustiedot]",
    rakennukset: "Set[Rakennustiedot]",
    asukkaat: "Set[Osapuoli]",
    omistajat: "Set[Osapuoli]",
    poimintapvm: "Optional[datetime.date]",
    loppupvm: "Optional[datetime.date]",
) -> Kohde:
    """
    Tarkista tietokannasta olemassa oleva kohde samoilla asukkailla, omistajilla ja
    rakennuksilla. Luo uusi kohde, jos ei löydy.

    Olemassa olevassa kohteessa voi olla enemmän tai vähemmän apurakennuksia kuin
    tulevassa kohteessa. Tässä tapauksessa käytetään olemassa olevaa kohdetta, mutta
    lisätään tai poistetaan rakennukset, jotka ovat muuttuneet.

    Paritalon tapauksessa emme tiedä, kumpi omistaja omisti kumman puolen rakennuksesta.
    Siksi meidän on luotava uudet kohteet molemmille puolille, kun joku myy puolikkaansa.
    """
    rakennus_ids = {rakennustiedot[0].id for rakennustiedot in rakennukset}
    asukas_ids = {osapuoli.id for osapuoli in asukkaat}
    omistaja_ids = {osapuoli.id for osapuoli in omistajat}
    osapuoli_ids = asukas_ids | omistaja_ids
    print(
        f"Etsitään kohdetta, jossa rakennukset {rakennus_ids}, asukkaat {asukas_ids} ja omistajat {omistaja_ids}"
    )
    
    # Hae kaikki kohteen rakennukset. Tarkistetaan myöhemmin, mitkä pitää lisätä tai poistaa.
    kohde_query = (
        select(Kohde, KohteenRakennukset, KohteenOsapuolet)
        .join(KohteenRakennukset)
        .join(KohteenOsapuolet)
        .filter(KohteenRakennukset.rakennus_id.in_(rakennus_ids))
        .filter(KohteenOsapuolet.osapuoli_id.in_(osapuoli_ids))
    )
    potential_kohdetiedot: "List[(Kohde, KohteenRakennukset, KohteenOsapuolet)]" = (
        session.execute(kohde_query).all()
    )

    # Listaa rakennukset, asukkaat ja omistajat jokaiselle kohteelle
    kohdetiedot_by_kohde: "dict[int, Kohdetiedot]" = {}
    for kohde, rakennus, osapuoli in potential_kohdetiedot:
        if kohde.id not in kohdetiedot_by_kohde:
            kohdetiedot_by_kohde[kohde.id] = (kohde, set(), set(), set())
        kohdetiedot_by_kohde[kohde.id][1].add(rakennus)
        # Erottele asukkaat ja omistajat
        if (
            osapuoli.osapuolenrooli_id
            == codes.osapuolenroolit[OsapuolenrooliTyyppi.VANHIN_ASUKAS].id
        ):
            kohdetiedot_by_kohde[kohde.id][2].add(osapuoli)
        if (
            osapuoli.osapuolenrooli_id
            == codes.osapuolenroolit[OsapuolenrooliTyyppi.OMISTAJA].id
        ):
            kohdetiedot_by_kohde[kohde.id][3].add(osapuoli)

    for kohdetiedot in kohdetiedot_by_kohde.values():
        kohde = kohdetiedot[0]
        kohteen_rakennus_ids = set(rakennus.rakennus_id for rakennus in kohdetiedot[1])
        kohteen_asukas_ids = set(osapuoli.osapuoli_id for osapuoli in kohdetiedot[2])
        kohteen_omistaja_ids = set(osapuoli.osapuoli_id for osapuoli in kohdetiedot[3])
        
        # Käytä kohdetta, jos rakennukset ja osapuolet ovat samat
        if (
            kohteen_rakennus_ids == rakennus_ids
            and kohteen_asukas_ids == asukas_ids
            and kohteen_omistaja_ids == omistaja_ids
        ):
            print("Rakennukset, asukkaat ja omistajat samat!")
            break
        # Hylkää kohde, jos rakennuksia puuttuu
        if rakennus_ids - kohteen_rakennus_ids:
            print("Rakennuksia puuttuu")
            continue
        # Käytä kohdetta, jos rakennuksia on lisätty
        if (
            kohteen_rakennus_ids < rakennus_ids
            and kohteen_asukas_ids == asukas_ids
            and kohteen_omistaja_ids == omistaja_ids
        ):
            print("Rakennukset lisätty, asukkaat ja omistajat samat!")
            break
        # Hylkää kohde, jos omistajat tai asukkaat ovat erilaiset
        if kohteen_asukas_ids != asukas_ids or kohteen_omistaja_ids != omistaja_ids:
            print("Asukkaat tai omistajat eri")
            continue
    else:
        print("Sopivaa kohdetta ei löydy, luodaan uusi kohde.")
        if poimintapvm:
            old_kohde = old_kohde_for_buildings(session, rakennus_ids, poimintapvm)
        new_kohde = create_new_kohde_from_buildings(
            session,
            rakennus_ids,
            asukkaat,
            omistajat,
            poimintapvm,
            loppupvm,
            old_kohde if 'old_kohde' in locals() else None,
        )
        if new_kohde and poimintapvm:
            if 'old_kohde' in locals() and old_kohde:
                print(
                    f"Löytyi päättyvä kohde {old_kohde.id}, asetetaan loppupäivämäärä."
                )
                set_old_kohde_loppupvm(
                    session, old_kohde.id, new_kohde.alkupvm - timedelta(days=1)
                )
                move_sopimukset_and_kuljetukset_to_new_kohde(
                    session, new_kohde.alkupvm, old_kohde.id, new_kohde.id
                )
                set_paatos_loppupvm_for_old_kohde(
                    session, old_kohde.id, new_kohde.alkupvm - timedelta(days=1)
                )
                update_kompostori(
                    session,
                    old_kohde.id,
                    new_kohde.alkupvm - timedelta(days=1),
                    new_kohde.id
                )
        return new_kohde

    # Palautetaan olemassa oleva kohde, kun löydetty
    print("Olemassaoleva kohde löytynyt.")
    kohteen_rakennukset = set(kohdetiedot[1])
    for kohteen_rakennus in kohteen_rakennukset:
        print("Tarkistetaan kohteen rakennus")
        print(kohteen_rakennus.rakennus_id)
        if kohteen_rakennus.rakennus_id not in rakennus_ids:
            print("Ei löydy enää, poistetaan kohteelta")
            session.delete(kohteen_rakennus)
    # Lisää uudet rakennukset
    for rakennus_id in rakennus_ids - kohteen_rakennus_ids:
        print("Tarkistetaan rakennus")
        print(rakennus_id)
        if rakennus_id not in kohteen_rakennus_ids:
            print("Ei löydy vielä, lisätään kohteelle")
            kohteen_rakennus = KohteenRakennukset(
                rakennus_id=rakennus_id, kohde_id=kohde.id
            )
            session.add(kohteen_rakennus)

    # Päivitä kohde voimassa olevaksi koko tuontijaksolle
    if not poimintapvm or (kohde.alkupvm and poimintapvm < kohde.alkupvm):
        kohde.alkupvm = poimintapvm

    # Nollaa loppupäivämäärä, jos käytetään poimintapvm:ää (kohde on edelleen aktiivinen)
    if poimintapvm and kohde.loppupvm == poimintapvm - timedelta(days=1):
        kohde.loppupvm = None

    return kohde


def get_or_create_kohteet_from_vanhimmat(
    session: "Session",
    ids: "Select",
    poimintapvm: "Optional[datetime.date]",
    loppupvm: "Optional[datetime.date]",
):
    """
    Create one kohde for each RakennuksenVanhimmat osapuoli id provided by
    the select query.
    """
    dvv_rakennustiedot = get_dvv_rakennustiedot_without_kohde(
        session, poimintapvm, loppupvm
    )
    # iterate vanhimmat to create kohde with the right name, client and building
    vanhimmat_osapuolet_query = (
        select(RakennuksenVanhimmat, Osapuoli)
        .join(RakennuksenVanhimmat.osapuoli)
        .filter(RakennuksenVanhimmat.osapuoli_id.in_(ids))
    )
    vanhimmat_osapuolet = session.execute(vanhimmat_osapuolet_query).all()
    print(
        f"Löydetty {len(vanhimmat_osapuolet)} vanhinta asukasta ilman voimassaolevaa kohdetta"
    )
    kohteet = []
    for (vanhin, osapuoli) in vanhimmat_osapuolet:
        # We have to check if we are interested in just this rakennus of vanhin
        if vanhin.rakennus_id in dvv_rakennustiedot:
            # The oldest inhabitant is the customer. Also save owners as backup
            # contacts.
            omistajat_query = (
                select(RakennuksenOmistajat, Osapuoli)
                .join(RakennuksenOmistajat.osapuoli)
                .where(RakennuksenOmistajat.rakennus_id == vanhin.rakennus_id)
            )
            omistajat = {row[1] for row in session.execute(omistajat_query).all()}
            # The correct kohde is found by checking the inhabitant in each half. In case
            # of paritalo, we don't know which owner owned which part of the building.
            # Therefore, we will have to create new kohteet for both halves when somebody
            # sells their half.
            kohde = update_or_create_kohde_from_buildings(
                session,
                dvv_rakennustiedot,
                {dvv_rakennustiedot[vanhin.rakennus_id]},
                {osapuoli},
                omistajat,
                poimintapvm,
                loppupvm,
            )
            kohteet.append(kohde)
    return kohteet


def get_or_create_kohteet_from_rakennustiedot(
    session: Session,
    dvv_rakennustiedot: Dict[int, Rakennustiedot],
    building_sets: List[Set[Rakennustiedot]],
    owners_by_rakennus_id: DefaultDict[int, Set[Osapuoli]],
    inhabitants_by_rakennus_id: DefaultDict[int, Set[Osapuoli]],
    poimintapvm: Optional[datetime.date],
    loppupvm: Optional[datetime.date],
):
    """
    Luo erilliset kohteet jokaiselle building_sets listassa olevalle rakennusryhmälle 
    ja lisää apurakennukset kuhunkin kohteeseen.
    """
    # Lisää apurakennukset kuhunkin rakennusryhmään
    building_sets = _add_auxiliary_buildings(dvv_rakennustiedot, building_sets)
    
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
):
    """
    Luo vähintään yksi kohde jokaisesta kiinteistotunnuksesta, jonka select-kysely palauttaa,
    jos kiinteistotunnuksella on rakennuksia ilman olemassa olevaa kohdetta annetulle aikajaksolle.

    1) Ensin erotellaan jokaisen kiinteistön rakennukset klustereihin etäisyyden perusteella.
    Jotkut kiinteistöt ovat valtavia ja voivat sisältää asuttuja rakennuksia/saunoja kaukana
    toisistaan. Niiden osoitteet voivat olla vääriä, joten meidän on erotettava ne etäisyyden perusteella.

    2) Jos samassa klusterissa on rakennuksia useilla omistajilla, ensimmäinen kohde sisältää
    kaikki rakennukset, jotka omistaa omistaja, jolla on eniten rakennuksia. Sitten luodaan
    toinen kohde jäljellä olevista rakennuksista, jotka omistaa omistaja, jolla on toiseksi
    eniten rakennuksia, jne., kunnes kaikilla rakennuksilla on kohde, joka on nimetty niiden
    omistajan mukaan. Jos on rakennuksia ilman omistajia, ne saavat oman kohteensa.

    3) Lopuksi, jos rakennuksilla on eri osoitteet, erotellaan rakennukset, joilla on sama osoite.
    """
    print("Ladataan kiinteistötunnukset...")
    kiinteistotunnukset = [
        result[0] for result in session.execute(kiinteistotunnukset).all()
    ]
    print(f"{len(kiinteistotunnukset)} tuotavaa kiinteistötunnusta löydetty.")
    print("Ladataan rakennukset...")

    dvv_rakennustiedot = get_dvv_rakennustiedot_without_kohde(
        session, poimintapvm, loppupvm
    )
    print(
        f"Löydetty {len(dvv_rakennustiedot)} DVV-rakennusta ilman voimassaolevaa kohdetta"
    )

    rakennustiedot_by_kiinteistotunnus: Dict[int, Set[Rakennustiedot]] = defaultdict(
        set
    )
    for rakennus, vanhimmat, omistajat, osoitteet in dvv_rakennustiedot.values():
        rakennustiedot_by_kiinteistotunnus[rakennus.kiinteistotunnus].add(
            (rakennus, vanhimmat, omistajat, osoitteet)
        )

    print("Ladataan omistajat...")
    rakennus_owners = session.execute(
        select(RakennuksenOmistajat.rakennus_id, Osapuoli).join(
            Osapuoli, RakennuksenOmistajat.osapuoli_id == Osapuoli.id
        )
    ).all()
    owners_by_rakennus_id = defaultdict(set)
    rakennus_ids_by_owner_id = defaultdict(set)
    for (rakennus_id, owner) in rakennus_owners:
        owners_by_rakennus_id[rakennus_id].add(owner)
        rakennus_ids_by_owner_id[owner.id].add(rakennus_id)

    print("Ladataan vanhimmat asukkaat...")
    rakennus_inhabitants = session.execute(
        select(RakennuksenVanhimmat.rakennus_id, Osapuoli).join(
            Osapuoli, RakennuksenVanhimmat.osapuoli_id == Osapuoli.id
        ).where(RakennuksenVanhimmat.loppupvm.is_(None))
    ).all()
    inhabitants_by_rakennus_id = defaultdict(set)
    for (rakennus_id, inhabitant) in rakennus_inhabitants:
        inhabitants_by_rakennus_id[rakennus_id].add(inhabitant)

    print("Ladataan osoitteet...")
    rakennus_addresses = session.execute(
        select(Rakennus.id, Osoite).join(Osoite, Rakennus.id == Osoite.rakennus_id)
    ).all()
    addresses_by_rakennus_id: "Dict[int, Set[Osoite]]" = defaultdict(set)
    for (rakennus_id, address) in rakennus_addresses:
        addresses_by_rakennus_id[rakennus_id].add(address)

    building_sets: List[Set[Rakennustiedot]] = []
    print("Käydään läpi kiinteistötunnukset...")
    for kiinteistotunnus in kiinteistotunnukset:
        print(f"--- Kiinteistö {kiinteistotunnus} ---")
        rakennustiedot_to_add = rakennustiedot_by_kiinteistotunnus[kiinteistotunnus]

        # 1) Jaa rakennukset klustereihin etäisyyden perusteella
        clustered_rakennustiedot = _cluster_rakennustiedot(
            rakennustiedot_to_add, DISTANCE_LIMIT
        )

        for rakennustiedot_by_cluster in clustered_rakennustiedot:
            ids_by_cluster = {rakennustiedot[0].id for rakennustiedot in rakennustiedot_by_cluster}
            print("Löydetty rakennusryhmä:")
            print(ids_by_cluster)

            # 2) Jaa rakennukset omistajan mukaan
            while ids_by_cluster:
                owners = set().union(
                    *[dvv_rakennustiedot[id][2] for id in ids_by_cluster]
                )
                building_ids_by_owner = {
                    owner: ids_by_cluster & rakennus_ids_by_owner_id[owner.osapuoli_id]
                    for owner in owners
                }
                # Aloita omistajasta, jolla on eniten rakennuksia
                owners_by_buildings = sorted(
                    building_ids_by_owner.items(),
                    key=lambda item: len(item[1]),
                    reverse=True,
                )
                if owners_by_buildings:
                    first_owner, building_ids_owned = owners_by_buildings[0]
                else:
                    # Meillä ei ole omistajia jäljellä! Jäljellä olevat ovat rakennuksia,
                    # joilla ei ole omistajia. Lisätään ne kaikki yhteen.
                    ids_without_owner = ids_by_cluster - set(
                        owners_by_rakennus_id.keys()
                    )
                    building_ids_owned = ids_without_owner

                print("Saman omistajan rakennukset:")
                print(building_ids_owned)

                # 3) Jaa rakennukset edelleen osoitteen mukaan
                while building_ids_owned:
                    building_ids_by_address = defaultdict(set)
                    for building in building_ids_owned:
                        for address in addresses_by_rakennus_id[building]:
                            street = address.katu_id
                            number = address.osoitenumero
                            building_ids_by_address[(street, number)].add(building)
                    # Aloita osoitteesta, jossa on eniten rakennuksia
                    addresses_by_buildings = sorted(
                        building_ids_by_address.items(),
                        key=lambda item: len(item[1]),
                        reverse=True,
                    )
                    (street, number), building_ids_at_address = addresses_by_buildings[0]
                    print(f"Kadun {street} osoitteessa {number}:")
                    print(f"Yhdistetään rakennukset {building_ids_at_address}")
                    rakennustiedot_at_address = {
                        dvv_rakennustiedot[id] for id in building_ids_at_address
                    }
                    building_sets.append(rakennustiedot_at_address)
                    # Älä tuo rakennusta uudestaan toisesta osoitteesta
                    building_ids_owned -= building_ids_at_address
                    ids_by_cluster -= building_ids_at_address

    print(" ")
    print(
        "--- Kiinteistötunnukset käyty läpi. Lisätään piharakennukset/saunat ja luodaan kohteet. ---"
    )
    kohteet = get_or_create_kohteet_from_rakennustiedot(
        session,
        dvv_rakennustiedot,
        building_sets,
        owners_by_rakennus_id,
        inhabitants_by_rakennus_id,
        poimintapvm,
        loppupvm,
    )
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
            sqlalchemyFunc.count(Rakennus.id),
        )
        .filter(Rakennus.id.in_(rakennus_id_without_kohde))
        .group_by(Rakennus.kiinteistotunnus)
        .having(sqlalchemyFunc.count(Rakennus.id) == 1)
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


def create_perusmaksurekisteri_kohteet(
    session: Session,
    perusmaksutiedosto: Path,
    poimintapvm: Optional[datetime.date],
    loppupvm: Optional[datetime.date] 
) -> List[Kohde]:
    """
    Luo kohteet perusmaksurekisterin perusteella.
    Vain määritellyt talotyypit huomioidaan.
    """
    logger = logging.getLogger(__name__)
    logger.info("\nLuodaan perusmaksurekisterin kohteet...")
    
    # Hae ensin kaikki DVV rakennustiedot
    dvv_rakennustiedot = get_dvv_rakennustiedot_without_kohde(
        session, poimintapvm, loppupvm
    )
    logger.info(f"Löydettiin {len(dvv_rakennustiedot)} rakennusta ilman kohdetta")
    
    # Luo lookup PRT -> Rakennustiedot
    dvv_rakennustiedot_by_prt = {
        tiedot[0].prt: tiedot 
        for tiedot in dvv_rakennustiedot.values() 
        if tiedot[0].prt  # Skip if PRT is None
    }
    
    ALLOWED_TYPES = {
        '021',  # Rivitalot
        '022',  # Ketjutalot
        '032',  # Luhtitalot
        '039'   # Muut asuinkerrostalot
    }
    
    buildings_to_combine = defaultdict(lambda: {"prt": set()})
    perusmaksut = load_workbook(filename=perusmaksutiedosto)
    sheet = perusmaksut["Tietopyyntö asiakasrekisteristä"]
    
    logger.info("Käsitellään perusmaksurekisterin rivit...")
    rows_processed = 0
    buildings_found = 0
    
    # Kerää vain sallitut rakennustyypit
    for index, row in enumerate(sheet.values):
        if index == 0:  # Skip header
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
            
        if rakennus.rakennuksenkayttotarkoitus in ALLOWED_TYPES:
            buildings_to_combine[asiakasnumero]["prt"].add(prt)
            buildings_found += 1
    
    logger.info(f"Käsitelty {rows_processed:,} riviä, löydetty {buildings_found:,} sopivaa rakennusta")
    
    # Luo kohteet sallituille rakennuksille
    building_sets = []
    valid_sets = 0
    
    logger.info("Muodostetaan rakennusryhmät...")
    for asiakasnumero, data in buildings_to_combine.items():
        building_set = set()
        for prt in data["prt"]:
            if prt in dvv_rakennustiedot_by_prt:
                rakennustiedot = dvv_rakennustiedot_by_prt[prt]
                building_set.add(rakennustiedot)
                
        if building_set:
            building_sets.append(building_set)
            valid_sets += 1
            
    logger.info(f"Muodostettu {valid_sets:,} rakennusryhmää")
    
    # Create owners_by_rakennus_id lookup for get_or_create_kohteet_from_rakennustiedot
    owners_by_rakennus_id = defaultdict(set)
    rakennus_owners = session.execute(
        select(RakennuksenOmistajat.rakennus_id, Osapuoli).join(
            Osapuoli, RakennuksenOmistajat.osapuoli_id == Osapuoli.id
        )
    ).all()
    for (rakennus_id, owner) in rakennus_owners:
        owners_by_rakennus_id[rakennus_id].add(owner)
    
    # Create inhabitants_by_rakennus_id lookup
    inhabitants_by_rakennus_id = defaultdict(set)
    rakennus_inhabitants = session.execute(
        select(RakennuksenVanhimmat.rakennus_id, Osapuoli).join(
            Osapuoli, RakennuksenVanhimmat.osapuoli_id == Osapuoli.id
        )
    ).all()
    for (rakennus_id, inhabitant) in rakennus_inhabitants:
        inhabitants_by_rakennus_id[rakennus_id].add(inhabitant)
            
    logger.info("Luodaan kohteet...")
    # Luo kohteet ja aseta loppupäivämäärä 2100
    kohteet = get_or_create_kohteet_from_rakennustiedot(
        session,
        dvv_rakennustiedot,
        building_sets,
        owners_by_rakennus_id,
        inhabitants_by_rakennus_id,
        poimintapvm,
        datetime.date(2100, 1, 1)
    )
    
    logger.info(f"Luotu {len(kohteet):,} kohdetta perusmaksurekisterin perusteella")
    return kohteet