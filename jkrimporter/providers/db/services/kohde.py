from dataclasses import dataclass
import datetime
import re
import logging
from collections import defaultdict
from datetime import date, datetime as dt
from datetime import timedelta
from functools import lru_cache
from typing import TypeVar, DefaultDict, Set, List, Dict,TYPE_CHECKING,NamedTuple, FrozenSet, Optional, Generic, Iterable, Callable
from ..models import Kohde  # Lisätään puuttuvat importit

from openpyxl import load_workbook
from psycopg2.extras import DateRange
from sqlalchemy import and_, exists, or_, select, update, case, delete, text, func
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm.decl_api import DeclarativeMeta
from sqlalchemy.orm import Session
from pathlib import Path

from jkrimporter.model import Asiakas, JkrIlmoitukset, LopetusIlmoitus, Yhteystieto

from .. import codes
from ..codes import KohdeTyyppi, OsapuolenrooliTyyppi, RakennuksenKayttotarkoitusTyyppi, RakennuksenOlotilaTyyppi
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
    HapaAineisto,
)
from ..utils import clean_asoy_name, form_display_name, is_asoy, is_company, is_yhteiso
from .buildings import DISTANCE_LIMIT, create_nearby_buildings_lookup, maximum_distance_of_buildings

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


def add_ulkoinen_asiakastieto_for_kohde(
    session: Session, kohde: Kohde, asiakas: Asiakas
):
    """
    Lisää ulkoisen asiakastiedon kohteelle.

    Args:
        session: Tietokantaistunto
        kohde: Kohde jolle asiakastieto lisätään
        asiakas: Asiakas jonka tiedot lisätään

    Returns:
        UlkoinenAsiakastieto: Luotu asiakastieto-objekti
    """
    asiakastieto = UlkoinenAsiakastieto(
        tiedontuottaja_tunnus=asiakas.asiakasnumero.jarjestelma,
        ulkoinen_id=asiakas.asiakasnumero.tunnus,
        ulkoinen_asiakastieto=asiakas.ulkoinen_asiakastieto,
        kohde=kohde,
    )

    session.add(asiakastieto)
    return asiakastieto


def find_kohde_by_prt(
    session: "Session", asiakas: "Union[Asiakas, JkrIlmoitukset]"
) -> "Union[Kohde, None]":
    if isinstance(asiakas, JkrIlmoitukset):
        return _find_kohde_by_asiakastiedot(
            session, Rakennus.prt.in_(asiakas.sijainti_prt), asiakas
        )
    elif isinstance(asiakas, Asiakas):
        return _find_kohde_by_asiakastiedot(
            session, Rakennus.prt.in_(asiakas.rakennukset), asiakas
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

def _find_kohde_by_ilmoitustiedot(
    session: "Session",
    filter,
    ilmoitus: "LopetusIlmoitus" 
) -> "Optional[Kohde]":
    """
    Optimoitu versio lopetusilmoitusten käsittelyyn.
    """
    # 1. Hae kohteiden ID:t ensin
    kohde_ids_query = (
        select(Kohde.id)
        .join(KohteenRakennukset)
        .join(Rakennus)
        .where(
            filter,
            Kohde.voimassaolo.overlaps(DateRange(ilmoitus.Vastausaika))
        )
        .distinct()
    )

    try:
        kohde_ids = session.execute(kohde_ids_query).scalars().all()
    except Exception as e:
        print(f"Virhe kohde-ID:iden haussa: {e}")
        return None

    if not kohde_ids:
        return None

    # 2. Standardoi vastuuhenkilön nimi kerran
    vastuuhenkilo = ilmoitus.nimi.upper()

    # 3. Käy läpi kohteet kunnes löytyy täsmäys
    for kohde_id in kohde_ids:
        osapuolet_query = (
            select(Osapuoli.nimi)
            .join(KohteenOsapuolet)
            .where(
                KohteenOsapuolet.kohde_id == kohde_id,
                KohteenOsapuolet.osapuolenrooli_id.in_([1, 2, 311])
            )
        )
        
        osapuoli_nimet = session.execute(osapuolet_query).scalars().all()
        
        for db_nimi in osapuoli_nimet:
            if not db_nimi:
                continue
                
            if db_nimi.upper() == vastuuhenkilo:
                return session.get(Kohde, kohde_id)

    return None



def _find_kohde_by_asiakastiedot(
    session: "Session", 
    filter,  
    asiakas: "Union[Asiakas, JkrIlmoitukset]"
) -> "Optional[Kohde]":
    """
    Optimoitu versio kohteen haulle. Minimoi tietokantakyselyt ja muistin käytön.
    Säilyttää luotettavan kohdennuksen.
    """
    # 1. Hae ensin pelkät kohteiden ID:t rakennusten perusteella
    kohde_ids_query = (
        select(Kohde.id)
        .join(KohteenRakennukset)
        .join(Rakennus)
        .where(
            filter,
            Kohde.voimassaolo.overlaps(
                DateRange(
                    asiakas.voimassa.lower or datetime.date.min,
                    asiakas.voimassa.upper or datetime.date.max,
                )
            )
        )
        .distinct()
    )

    try:
        kohde_ids = session.execute(kohde_ids_query).scalars().all()
    except Exception as e:
        print(f"Virhe kohde-ID:iden haussa: {e}")
        return None

    if not kohde_ids:
        return None

    # 2. Standardoi asiakkaan nimi kerran
    if isinstance(asiakas, JkrIlmoitukset):
        asiakas_nimi = asiakas.vastuuhenkilo.nimi.upper()
    else:
        asiakas_nimi = asiakas.haltija.nimi.upper()

    # 3. Hae ja validoi kohteet yksi kerrallaan kunnes löytyy täsmäys
    for kohde_id in kohde_ids:
        # Hae vain oleelliset osapuolet kohteelle
        osapuolet_query = (
            select(Osapuoli.nimi)
            .join(KohteenOsapuolet)
            .where(
                KohteenOsapuolet.kohde_id == kohde_id,
                KohteenOsapuolet.osapuolenrooli_id.in_([1, 2, 311])  # Vain oleelliset roolit
            )
        )
        
        osapuoli_nimet = session.execute(osapuolet_query).scalars().all()
        
        # Tarkista täsmääkö jokin osapuoli
        for db_nimi in osapuoli_nimet:
            if not db_nimi:
                continue
                
            db_nimi = db_nimi.upper()
            
            # Jos kyseessä asoy, vaadi tarkka täsmäys
            if 'ASOY' in db_nimi or 'AS OY' in db_nimi:
                if db_nimi == asiakas_nimi:
                    return session.get(Kohde, kohde_id)
            # Muuten salli osittainen täsmäys
            elif (asiakas_nimi in db_nimi or db_nimi in asiakas_nimi):
                return session.get(Kohde, kohde_id)

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


@lru_cache(maxsize=100)
def get_or_create_pseudokohde(session: Session, nimi: str, kohdetyyppi) -> Kohde:
    kohdetyyppi = codes.kohdetyypit[kohdetyyppi]
    query = select(Kohde).where(Kohde.nimi == nimi, Kohde.kohdetyyppi == kohdetyyppi)
    try:
        kohde = session.execute(query).scalar_one()
    except NoResultFound:
        kohde = Kohde(nimi=nimi, kohdetyyppi=kohdetyyppi)
        session.add(kohde)

    return kohde


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
            .filter(
                and_(
                    poimintapvm < Kohde.loppupvm,
                    # Älä liitä rakennuksia perusmaksurekisterin kohteisiin
                    Kohde.loppupvm != datetime.date(2100, 1, 1)
                )
            )
        )
    else:
        rakennus_id_with_current_kohde = (
            select(Rakennus.id)
            .join(KohteenRakennukset)
            .join(Kohde)
            .filter(
                and_(
                    Kohde.voimassaolo.overlaps(DateRange(poimintapvm, loppupvm)),
                    # Älä liitä rakennuksia perusmaksurekisterin kohteisiin
                    Kohde.loppupvm != datetime.date(2100, 1, 1)
                )
            )
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


def _cluster_rakennustiedot(
    rakennustiedot_to_cluster: "Set[Rakennustiedot]",
    distance_limit: int,
    existing_cluster: "Optional[Set[Rakennustiedot]]" = None
) -> "List[Set[Rakennustiedot]]":
    """
    Klusteroi rakennukset seuraavien ehtojen perusteella:
    - Etäisyys toisistaan max 300m JA
    - Samat omistajat/asukkaat JA
    - Sama osoite
    """
    clusters = []
    # Aloita klusteri ensimmäisestä rakennuksesta (tai olemassaolevasta klusterista)
    cluster = existing_cluster.copy() if existing_cluster else None
    
    while rakennustiedot_to_cluster:
        if not cluster:
            cluster = set([rakennustiedot_to_cluster.pop()])

        other_rakennustiedot_to_cluster = rakennustiedot_to_cluster.copy()
        while other_rakennustiedot_to_cluster:
            found_match = False
            for other_rakennustiedot in other_rakennustiedot_to_cluster:
                # Tarkista etäisyys kaikkiin klusterin rakennuksiin
                all_buildings = [rakennustiedot[0] for rakennustiedot in cluster] + [other_rakennustiedot[0]]
                if maximum_distance_of_buildings(all_buildings) >= distance_limit:
                    continue

                # Tarkista omistajat/asukkaat
                match_found = False
                for cluster_building in cluster:
                    if _match_ownership_or_residents(cluster_building, other_rakennustiedot):
                        match_found = True
                        break
                if not match_found:
                    continue

                # Tarkista osoite
                match_found = False
                for cluster_building in cluster:
                    if _match_addresses(cluster_building[3], other_rakennustiedot[3]):
                        match_found = True
                        break
                if not match_found:
                    continue

                # Kaikki ehdot täyttyvät, lisää rakennus klusteriin
                cluster.add(other_rakennustiedot)
                found_match = True
                break

            if not found_match:
                # Klusteri on valmis! Muita sopivia rakennuksia ei löytynyt.
                break

            # Poista löydetty rakennus käsiteltävistä ja jatka silmukkaa
            other_rakennustiedot_to_cluster.remove(other_rakennustiedot)

        # Klusteri on valmis! Poista klusteroidut rakennukset ja aloita silmukka alusta
        clusters.append(cluster)
        rakennustiedot_to_cluster -= cluster
        cluster = None

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


def _normalize_address(address: "Osoite") -> str:
    """
    Normalisoi osoitteen vertailua varten.
    Palauttaa osoitteen muodossa 'kadunnimi numero' ilman kirjaimia tai muita lisäosia.
    Esim. 'Leninpolku 1 a 5' -> 'leninpolku 1'

    Args:
        address: Osoite-objekti

    Returns:
        str: Normalisoitu osoite
    """
    # Tarkista että osoitteella on katu ja numero
    if not address.katu or not address.osoitenumero:
        return ""

    # Poista välilyönnit alusta ja lopusta, muuta pieniksi kirjaimiksi
    katunimi = address.katu.katunimi_fi.strip().lower() if address.katu.katunimi_fi else ""
    
    # Ota numerosta vain ensimmäinen numero (ennen kirjainta tai välilyöntiä)
    import re
    numero_match = re.match(r'^\d+', address.osoitenumero.strip())
    numero = numero_match.group(0) if numero_match else ""

    return f"{katunimi} {numero}"

def _match_addresses(addresses1: "FrozenSet[Osoite]", addresses2: "FrozenSet[Osoite]") -> bool:
    """
    Tarkistaa onko osoitteilla yhtäläisyyksiä.
    Vertailee osoitteita vain kadunnimen ja numeron perusteella, jättäen huomiotta
    kirjaimet ja muut lisäosat.

    Esimerkiksi seuraavat osoitteet tulkitaan samoiksi:
    - Leninpolku 1
    - Leninpolku 1 a
    - Leninpolku 1a
    - Leninpolku 1b
    - Leninpolku 1 c 5

    Args:
        addresses1: Ensimmäisen rakennuksen osoitteet
        addresses2: Toisen rakennuksen osoitteet

    Returns:
        bool: True jos osoitteilla on yhtäläisyyksiä, muuten False
    """
    # Jos jommalla kummalla ei ole osoitteita, ei voida verrata
    if not addresses1 or not addresses2:
        return False

    # Normalisoi osoitteet vertailua varten
    normalized1 = {_normalize_address(addr) for addr in addresses1}
    normalized2 = {_normalize_address(addr) for addr in addresses2}

    # Poista tyhjät osoitteet
    normalized1 = {addr for addr in normalized1 if addr}
    normalized2 = {addr for addr in normalized2 if addr}

    # Jos jommalla kummalla ei ole valideja osoitteita, ei voida verrata
    if not normalized1 or not normalized2:
        return False

    # Tarkista onko yhteisiä normalisoituja osoitteita
    return bool(normalized1.intersection(normalized2))


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

    # Siirrä jatkuvat kompostorit uudelle kohteelle
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


def determine_kohdetyyppi(session: "Session", rakennus: "Rakennus", asukkaat: "Optional[Set[Osapuoli]]" = None) -> KohdeTyyppi:
    """
    Määrittää kohteen tyypin rakennuksen tietojen perusteella.
    Logiikka:
    1. Tarkista HAPA/BIOHAPA status
    2. Tarkista onko asuinkiinteistö seuraavassa järjestyksessä:
       1. Rakennusluokka 2018 (0110-0211)
       2. Vanha rakennusluokka (011-041)
       3. Huoneistomaara > 0
       4. Asukkaat olemassa
    3. Jos mikään ehto ei täyty -> MUU

    Args:
        session: Tietokantaistunto
        rakennus: Rakennus-objekti
        asukkaat: Lista asukkaista (optional)

    Huom: HAPA/BIOHAPA tyypit määritellään myös tietokannassa triggerillä
    (katso V2.48.0__Add_hapa_trigger_and_functions.sql)
    """
    # 1. Tarkista HAPA/BIOHAPA status
    # hapa_aineisto = get_hapa_aineisto(session)
    # if rakennus.prt in hapa_aineisto:
    #     kohdetyyppi = hapa_aineisto[rakennus.prt].lower()
    #     if kohdetyyppi == 'hapa':
    #         return KohdeTyyppi.HAPA
    #     elif kohdetyyppi == 'biohapa':
    #         return KohdeTyyppi.BIOHAPA

    # 2. Tarkista rakennusluokka 2018
    if rakennus.rakennusluokka_2018 is not None:
        try:
            luokka = int(rakennus.rakennusluokka_2018)
            if 110 <= luokka <= 211:
                return KohdeTyyppi.ASUINKIINTEISTO
        except (ValueError, TypeError):
            pass

    # 3. Jos ei rakennusluokkaa 2018, tarkista käyttötarkoitus
    try:
        kayttotarkoitus = int(rakennus.rakennuksenkayttotarkoitus)
        if 11 <= kayttotarkoitus <= 41:
            return KohdeTyyppi.ASUINKIINTEISTO
    except (ValueError, TypeError):
        pass

    # 4. Tarkista huoneistomäärä
    if rakennus.huoneistomaara is not None and rakennus.huoneistomaara > 0:
        return KohdeTyyppi.ASUINKIINTEISTO

    # 5. Tarkista rakennuksenolotila
    if rakennus.rakennuksenolotila is not None and rakennus.rakennuksenolotila in [
        RakennuksenOlotilaTyyppi.VAKINAINEN_ASUMINEN.value
    ]:
        return KohdeTyyppi.ASUINKIINTEISTO

    # 6. Tarkista asukkaat
    if asukkaat and len(asukkaat) > 0:
        return KohdeTyyppi.ASUINKIINTEISTO

    # 7. Jos mikään ehto ei täyttynyt, kyseessä on muu kohde
    return KohdeTyyppi.MUU

@lru_cache(maxsize=1)  # Vain yksi cache entry koko aineistolle
def get_hapa_aineisto(session: "Session") -> Dict[str, str]:
    """
    Hakee HAPA-aineiston tiedot muistiin.
    
    Args:
        session: Tietokantaistunto
    
    Returns:
        Dict[str, str]: Sanakirja, jossa avaimena rakennus_id_tunnus ja arvona kohdetyyppi
    """
    # Haetaan koko aineisto muistiin
    query = select(HapaAineisto.rakennus_id_tunnus, HapaAineisto.kohdetyyppi)
    
    try:
        results = session.execute(query).all()
        return {row[0]: row[1] for row in results if row[0] is not None}
    except Exception as e:
        print(f"Virhe HAPA-aineiston haussa: {str(e)}")
        return {}

def create_new_kohde(session: Session, asiakas: Asiakas, keraysalueet=None) -> Kohde:
    """
    Luo uusi kohde asiakkaan tietojen perusteella.
    
    Args:
        session: Tietokantaistunto
        asiakas: Asiakas jonka tiedoista kohde luodaan
        keraysalueet: Valinnainen dictionary keräysaluetiedoilla
            {
                'biojate': bool,
                'hyotyjate': bool 
            }
        asukkaat: Valinnainen set asukkaista kohdetyypin määritystä varten
    Returns:
        Kohde: Luotu kohdeobjekti
    """

    # Tarkista rakennusten perusteella
    kohdetyyppi = KohdeTyyppi.MUU
    try:
        for prt in asiakas.rakennukset:
            rakennus = session.query(Rakennus).filter(Rakennus.prt == prt).first()
            if rakennus:           
                # Hae rakennuksen asukkaat suoraan RakennuksenVanhimmat-taulusta
                asukkaat = set(session.query(RakennuksenVanhimmat)
                    .filter(RakennuksenVanhimmat.rakennus_id == rakennus.id)
                    .all())
                
                building_type = determine_kohdetyyppi(session, rakennus, asukkaat)
                if building_type in (KohdeTyyppi.ASUINKIINTEISTO):
                    kohdetyyppi = building_type
                    break
    
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Virhe rakennusten tyypin määrityksessä: {str(e)}")
        # Jatketaan oletustyypillä MUU

    kohde = Kohde(
        nimi=form_display_name(asiakas.haltija),
        kohdetyyppi=codes.kohdetyypit[kohdetyyppi],
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
        session.query(func.max(RakennuksenOmistajat.omistuksen_alkupvm))
        .filter(RakennuksenOmistajat.rakennus_id.in_(rakennus_ids))
        .scalar()
    )
    latest_vanhin_change = session.query(
        func.max(RakennuksenVanhimmat.alkupvm)
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
    session: Session,
    rakennus_ids: List[int],
    asukkaat: Set[Osapuoli],
    omistajat: Set[Osapuoli],
    poimintapvm: Optional[datetime.date],
    loppupvm: Optional[datetime.date],
    old_kohde: Optional[Kohde],
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
        asukkaat: Rakennusten asukkaat 
        omistajat: Rakennusten omistajat
        poimintapvm: Uuden kohteen alkupäivämäärä
        loppupvm: Uuden kohteen loppupäivämäärä
        old_kohde: Vanha kohde, jos kyseessä on päivitys (vapaaehtoinen)

    Returns:
        Kohde: Luotu kohdeobjekti kaikkine riippuvuuksineen

    Huomautukset:
        - Funktio lisää kaikki asukkaat VANHIN_ASUKAS -roolilla
        - Omistajat lisätään OMISTAJA-roolilla, vaikka olisivat myös asukkaita
        - Omistajatiedot tallennetaan aina, jotta kohde voidaan tunnistaa myöhemmissä tuonneissa
        - Muutokset tallennetaan session.flush()-komennolla, mutta ei commitoida
    """
    # Alustetaan asiakas None:ksi
    asiakas = None
    
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
        else:
            # Jos ei löydy yritystä/yhteisöä, käytetään ensimmäistä omistajaa
            asiakas = min(omistajat, key=lambda x: x.nimi)
            
    # Jos ei omistajaa, käytetään asukasta
    if not asiakas and asukkaat:
        asiakas = min(asukkaat, key=lambda x: x.nimi)

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
        
    # Määritä kohdetyyppi rakennusten perusteella
    kohdetyyppi = KohdeTyyppi.MUU  # Oletuksena MUU
    for rakennus_id in rakennus_ids:
        rakennus = session.query(Rakennus).filter(Rakennus.id == rakennus_id).first()
        if rakennus:
            building_type = determine_kohdetyyppi(session, rakennus, asukkaat)
            if building_type == KohdeTyyppi.ASUINKIINTEISTO:
                kohdetyyppi = building_type
                break

    kohde = Kohde(
        nimi=kohde_display_name,
        kohdetyyppi=codes.kohdetyypit[kohdetyyppi],
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
    session: Session, rakennus_ids: List[int], poimintapvm: datetime.date
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


def set_old_kohde_loppupvm(session: Session, kohde_id: int, loppupvm: datetime.date):
    session.execute(
        update(Kohde)
        .where(Kohde.id == kohde_id)
        .values(loppupvm=loppupvm)
    )
    session.commit()


def set_paatos_loppupvm_for_old_kohde(
    session: Session, kohde_id: int, loppupvm: datetime.date
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
    session: Session, old_kohde_id: int, loppupvm: datetime.date, new_kohde_id: int
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
    session: Session, alkupvm: datetime.date, old_kohde_id: int, new_kohde_id: int
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
    2. Jos kohdetta ei löydy, luo uusi
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
        poimintapvm: Uuden kohteen alkupäivämäärä
        loppupvm: Uuden kohteen loppupäivämäärä

    Returns:
        Kohde: Luotu tai päivitetty kohde
    """
    rakennus_ids = set()
    for rakennustiedot in rakennukset:
        if isinstance(rakennustiedot, tuple):
            rakennus_ids.add(rakennustiedot[0].id)
        else:
            rakennus_ids.add(rakennustiedot.id)

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
    
    original_kohdetyyppi = found_kohde.kohdetyyppi

    for rakennus_tiedot in rakennukset:       
        if isinstance(rakennus_tiedot, tuple):
            rakennus = rakennus_tiedot[0].rakennus
        else:
            rakennus = rakennus_tiedot
        
        building_type = determine_kohdetyyppi(session, rakennus, asukkaat)
        if building_type == KohdeTyyppi.ASUINKIINTEISTO:
            new_kohdetyyppi = codes.kohdetyypit[building_type]
            if new_kohdetyyppi != original_kohdetyyppi:
                found_kohde.kohdetyyppi = new_kohdetyyppi
                needs_update = True
            break
    

    if needs_update:
        session.flush()
        
    return found_kohde


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


@lru_cache(maxsize=100)
def get_or_create_pseudokohde(session: Session, nimi: str, kohdetyyppi) -> Kohde:
    kohdetyyppi = codes.kohdetyypit[kohdetyyppi]
    query = select(Kohde).where(Kohde.nimi == nimi, Kohde.kohdetyyppi == kohdetyyppi)
    try:
        kohde = session.execute(query).scalar_one()
    except NoResultFound:
        kohde = Kohde(nimi=nimi, kohdetyyppi=kohdetyyppi)
        session.add(kohde)

    return kohde


def get_or_create_kohteet_from_kiinteistot(
    session: Session,
    kiinteistotunnukset: "Select", 
    poimintapvm: "Optional[datetime.date]",
    loppupvm: "Optional[datetime.date]",
) -> "List[Kohde]":
    """
    Luo vähintään yksi kohde jokaisesta kiinteistötunnuksesta, jonka select-kysely palauttaa,
    jos kiinteistotunnuksella on rakennuksia ilman olemassa olevaa kohdetta annetulle aikavälille.

    Prosessi:
    1. Erotellaan kiinteistöjen rakennukset klustereihin etäisyyden perusteella
       - Jotkin kiinteistöt voivat sisältää kaukana toisistaan olevia rakennuksia
       - Osoitteet voivat olla virheellisiä, joten erottelu tehdään etäisyyden perusteella
    
    2. Käsittele samassa klusterissa olevat rakennukset:
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
        loppupvm: Uusien kohteiden loppupäivämäärä

    Returns:
        Lista luoduista kohteista

    Raises:
        SQLAlchemyError: Jos tietokantaoperaatioissa tapahtuu virhe
    """
    logger = logging.getLogger(__name__)

    # Seurattavat PRT-tunnukset lokitusta varten
    log_prt_in = (
'103084763X',
'103084764Y',
'1030847650',
'1030847661',
'1030847672',
'1030847683',
'1030847694',
'1030847395',
'1030847406',
'103074894K',
'103074895L',
'103084760U',
'103084762W',
'103084761V'
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
            select(RakennuksenOmistajat.rakennus_id, Osapuoli).join(
                Osapuoli, RakennuksenOmistajat.osapuoli_id == Osapuoli.id
            )
        ).all()
        
        owners_by_rakennus_id = defaultdict(set)  # rakennus_id -> {omistajat}
        rakennus_ids_by_owner_id = defaultdict(set)  # omistaja.id -> {rakennus_id:t}
        for (rakennus_id, owner) in rakennus_owners:
            owners_by_rakennus_id[rakennus_id].add(owner)
            rakennus_ids_by_owner_id[owner.id].add(rakennus_id)

        # Hae asukastiedot ja muodosta lookup-taulu
        rakennus_inhabitants = session.execute(
            select(RakennuksenVanhimmat.rakennus_id, Osapuoli).join(
                Osapuoli, RakennuksenVanhimmat.osapuoli_id == Osapuoli.id
            )
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
                        
                        # Tarkista omistaja asoy
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
    session: Session,
    poimintapvm: "Optional[datetime.date]",
    loppupvm: "Optional[datetime.date]",
) -> "List[Kohde]":
    """
    Hae tai luo kohteet kaikille yhden asunnon taloille ja paritaloille, joilla ei ole
    kohdetta määritellyllä aikavälillä. Huomioi myös talot, joissa ei ole asukkaita.

    Jos kiinteistöllä on useita asuttuja rakennuksia, sitä ei tuoda tässä.
    """
    logger = logging.getLogger(__name__)
    logger.info("\n----- LUODAAN YHDEN ASUNNON KOHTEET -----")

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

    # Määrittele sallitut rakennustyypit
    ALLOWED_TYPES_2018 = {
        '0111',  # Yhden asunnon talot
        '0110'   # Paritalot
    }
    
    ALLOWED_TYPES_OLD = {
        '011',  # Yhden asunnon talot
        '012'   # Kahden asunnon talot
    }

    # Hae rakennukset joilla ei ole kohdetta
    rakennus_id_without_kohde = (
        select(Rakennus.id)
        .filter(
            or_(
                # Tarkista ensisijaisesti 2018 luokitus
                Rakennus.rakennusluokka_2018.in_(ALLOWED_TYPES_2018),
                # Jos 2018 luokka puuttuu, käytä vanhaa luokitusta
                and_(
                    Rakennus.rakennusluokka_2018.is_(None),
                    Rakennus.rakennuksenkayttotarkoitus_koodi.in_(ALLOWED_TYPES_OLD)
                )
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

    # Hae kiinteistöt joilla on vain yksi rakennus
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


def get_or_create_multiple_and_uninhabited_kohteet(
    session: Session,
    poimintapvm: "Optional[datetime.date]",
    loppupvm: "Optional[datetime.date]",
) -> "List[Kohde]":
    """
    Luo kohteet kaikille kiinteistötunnuksille, joilla on rakennuksia ilman kohdetta
    määritellylle aikavälille. Tämä funktio käsittelee jäljellä olevat rakennukset,
    mukaan lukien useita rakennuksia sisältävät kiinteistöt ja asumattomat rakennukset.
    """
    logger = logging.getLogger(__name__)
    logger.info("\n----- LUODAAN JÄLJELLÄ OLEVAT KOHTEET -----")

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
    # Hae kaikki rakennukset vanhoilta kohteilta
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
        kompostori_ids = select(KompostorinKohteet.kompostori_id).where(
            KompostorinKohteet.kohde_id == old_id
        )

        # Aseta loppupvm kompostoreille
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

        # Siirrä jatkuvat kompostorit uudelle kohteelle
        stmt = (
            update(KompostorinKohteet)
            .where(
                KompostorinKohteet.kompostori_id.in_(kompostori_ids.scalar_subquery()),
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
    loppupvm: Optional[datetime.date] = None,
) -> List[Kohde]:
    """
    Luo kohteet perusmaksurekisterin tietojen perusteella.
    
    Args:
        session: Tietokantaistunto
        perusmaksutiedosto: Polku perusmaksurekisterin Excel-tiedostoon
        poimintapvm: Uusien kohteiden alkupäivämäärä
        loppupvm: Uusien kohteiden loppupäivämäärä (ei käytetä, käytetään aina 2100-01-01)
        
    Returns:
        Lista luoduista kohteista

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

    # Ryhmittele rakennukset asiakasnumeron mukaan
    buildings_to_combine = defaultdict(lambda: {"prt": set()})
    
    # Avaa perusmaksurekisteri
    logger.info("Avataan perusmaksurekisteri...")
    perusmaksut = load_workbook(filename=perusmaksutiedosto)
    
    # Käytä ensimmäistä sheetiä jos "Tietopyyntö asiakasrekisteristä" ei löydy
    sheet_name = "Tietopyyntö asiakasrekisteristä"
    if sheet_name not in perusmaksut.sheetnames:
        sheet_name = perusmaksut.sheetnames[0]
        logger.info(f"Käytetään sheet-nimeä: {sheet_name}")
    
    sheet = perusmaksut[sheet_name]

    # Käsittele rivit ja kerää rakennukset asiakasnumeron mukaan
    logger.info("Käsitellään perusmaksurekisterin rivit...")
    rows_processed = 0
    buildings_found = 0

    for index, row in enumerate(sheet.values):
        if index == 0:  # Ohita otsikkorivi
            continue
        
        rows_processed += 1
        asiakasnumero = str(row[2])
        prt = str(row[0])

        # Hae rakennus
        rakennus = session.query(Rakennus).filter(
            Rakennus.prt == prt
        ).first()

        if not rakennus:
            continue

        # Lisää rakennus asiakasnumeron mukaiseen ryhmään
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

    # Luo kohteet
    logger.info("\nLuodaan kohteet...")
    kohteet = get_or_create_kohteet_from_rakennustiedot(
        session,
        dvv_rakennustiedot,
        building_sets,
        owners_by_rakennus_id,
        inhabitants_by_rakennus_id,
        poimintapvm,
        datetime.date(2100, 1, 1),  # Käytetään kiinteää loppupäivämäärää
    )

    logger.info(f"\nLuotu {len(kohteet):,} kohdetta perusmaksurekisterin perusteella")
    return kohteet


def get_or_create_kohteet_from_rakennustiedot(
    session: Session,
    dvv_rakennustiedot: Dict[int, Rakennustiedot],
    building_sets: List[Set[Rakennustiedot]],
    owners_by_rakennus_id: Dict[int, Set[Osapuoli]],
    inhabitants_by_rakennus_id: Dict[int, Set[Osapuoli]],
    poimintapvm: Optional[datetime.date],
    loppupvm: Optional[datetime.date]
) -> List[Kohde]:
    """
    Luo kohteet rakennusryhmien perusteella.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"\nLuodaan kohteet {len(building_sets)} rakennusryhmälle...")
    
    kohteet = []

    for i, building_set in enumerate(building_sets, 1):
        # Kerää rakennusten ID:t ja rakennustiedot
        rakennus_ids = []
        rakennustiedot_set = set()
        
        for tiedot in building_set:
            if isinstance(tiedot, tuple):
                rakennus_id = tiedot[0].id
                rakennustiedot_set.add(tiedot[0])
            else:
                rakennus_id = tiedot.id
                rakennustiedot_set.add(tiedot)
            rakennus_ids.append(rakennus_id)
        
        # Kerää omistajat ja asukkaat
        asukkaat = set()
        omistajat = set()
        
        for rakennus_id in rakennus_ids:
            if rakennus_id in owners_by_rakennus_id:
                omistajat.update(owners_by_rakennus_id[rakennus_id])
            if rakennus_id in inhabitants_by_rakennus_id:
                asukkaat.update(inhabitants_by_rakennus_id[rakennus_id])
        
        # Yhdistä osapuolet ja asukkaat
       # osapuolet = omistajat.union(asukkaat)
        
        # Luo tai päivitä kohde
        kohde = update_or_create_kohde_from_buildings(
            session,
            dvv_rakennustiedot,
            rakennustiedot_set,  # Käytetään rakennustiedot_set:iä building_set:in sijaan
            asukkaat,
            omistajat,
            poimintapvm,
            loppupvm
        )
        
        if kohde:
            kohteet.append(kohde)
        
        # Näytä edistyminen joka 100. kohteen jälkeen
        if i % 100 == 0:
            logger.info(f"Käsitelty {i}/{len(building_sets)} rakennusryhmää...")

    logger.info(f"Käsitelty kaikki {len(building_sets)} rakennusryhmää.")
    return kohteet