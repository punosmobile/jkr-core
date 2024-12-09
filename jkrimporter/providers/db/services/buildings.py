
import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Dict, List, Set, Union


from geoalchemy2.shape import to_shape
from shapely.geometry import MultiPoint
from sqlalchemy import and_
from sqlalchemy import func as sqlalchemyFunc
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from ..database import engine

from jkrimporter.model import Rakennustunnus
from jkrimporter.providers.db.utils import clean_asoy_name, is_asoy

from .. import codes
from ..codes import RakennuksenKayttotarkoitusTyyppi
from ..models import (
    Katu,
    Osapuoli,
    Osoite,
    RakennuksenOmistajat,
    RakennuksenVanhimmat,
    Rakennus,
)

logger = logging.getLogger(__name__)

DISTANCE_LIMIT = 300
AREA_LIMIT = 30000

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from jkrimporter.model import Asiakas, Yhteystieto, JkrIlmoitukset, LopetusIlmoitus


def minimum_distance_of_buildings(buildings: List[Rakennus]) -> float:
    """
    Palauttaa lyhimmän etäisyyden rakennusten välillä.
    """
    if len(buildings) < 2:
        return float('inf')
        
    min_distance = float('inf')
    points = [to_shape(building.geom) for building in buildings if building.geom]
    
    for i, first_point in enumerate(points[:-1]):
        for second_point in points[i+1:]:
            distance = first_point.distance(second_point)
            min_distance = min(min_distance, distance)
            
    return min_distance


def convex_hull_area_of_buildings(buildings):
    points = [to_shape(building.geom) for building in buildings if building.geom]
    multipoint = MultiPoint(points)

    convex_hull = multipoint.convex_hull.buffer(6)
    area = convex_hull.area

    return area

def create_nearby_buildings_lookup(
    dvv_rakennustiedot: Dict[int, "Rakennustiedot"]
) -> Dict[int, Set[int]]:
    """
    Luo hakutaulukko lähekkäisistä rakennuksista hyödyntäen materialisoitua näkymää.
    
    Args:
        dvv_rakennustiedot: Sanakirja rakennustiedoista joille etsitään lähellä olevia rakennuksia
        
    Returns:
        Dict[int, Set[int]]: Sanakirja muotoa {rakennus_id: {lähellä_oleva_id1, ...}}
    """
    logger = logging.getLogger(__name__)
    nearby_lookup = defaultdict(set)
    
    # Käytetään vain kokonaislukuja SQL kyselyssä (suorituskyky)
    building_ids = list(dvv_rakennustiedot.keys())
    
    with Session(engine) as session:
        # Hae kaikki rakennusparit jotka ovat alle 300m päässä toisistaan
        query = """
        SELECT rakennus1_id, rakennus2_id 
        FROM jkr.nearby_buildings 
        WHERE rakennus1_id = ANY(:ids) 
          AND rakennus2_id = ANY(:ids)
          AND distance <= 300
        """
        
        result = session.execute(
            query,
            {"ids": building_ids}
        )
        
        # Lisää molemmat suunnat hakutaulukkoon
        pairs_added = 0
        for r1_id, r2_id in result:
            nearby_lookup[r1_id].add(r2_id)
            nearby_lookup[r2_id].add(r1_id)
            pairs_added += 1
            
        logger.debug(
            f"Haettu {pairs_added} lähellä olevaa rakennusparia "
            f"({len(building_ids)} rakennukselle)"
        )
            
    return nearby_lookup

def refresh_nearby_buildings_materialized_view() -> None:
    """
    Päivitä materialisoitu näkymä nearby_buildings.
    Tätä tulee kutsua kun rakennusten sijaintitiedot muuttuvat.
    """
    with Session(engine) as session:
        session.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY jkr.nearby_buildings")
        session.commit()


def match_omistaja(rakennus, haltija, preprocessor=lambda x: x):
    omistajat = rakennus.omistajat
    return any(
        preprocessor(haltija.nimi).lower() == preprocessor(omistaja.osapuoli.nimi).lower()
        for omistaja in omistajat
    )


counts: Dict[str, int] = defaultdict(int)


def prt_on_single_customer(rakennukset, prt_counts):
    """
    Tarkistaa onko rakennus yhden asiakkaan/paritalon omistuksessa.
    
    Args:
        rakennukset: Lista rakennuksia
        prt_counts: Sanakirja rakennusten PRT-tunnusten esiintymismääristä
        
    Returns:
        bool: True jos kaikki rakennukset täyttävät kriteerit
    """
    for rakennus in rakennukset:
        # Käytä oikeaa attribuuttinimeä rakennuksen_omistajat_collection
        omistajat = list(rakennus.rakennuksen_omistajat_collection)
        if not (prt_counts[rakennus.prt] == 1 or 
               (prt_counts[rakennus.prt] == 2 and len(omistajat) <= 2)):
            return False
    return True


def find_buildings_for_kohde(
    session: "Session",
    asiakas: "Asiakas",
    prt_counts: Dict[str, "IntervalCounter"],
    kitu_counts: Dict[str, "IntervalCounter"],
    address_counts: Dict[str, "IntervalCounter"],
):
    """
    Etsii rakennukset asiakkaan kohteelle seuraavien kriteerien mukaisesti:
    1. PRT-tunnuksen perusteella jos asiakas on ainoa/paritalo
    2. Y-tunnuksen perusteella jos kyseessä on asunto-osakeyhtiö
    3. Osoitteen perusteella
    """
    print("looking for buildings")
    counts["asiakkaita"] += 1
    rakennukset = []

    # 1. Tarkista PRT-tunnuksen perusteella
    if asiakas.rakennukset:
        print("has buildings already")
        counts["on prt"] += 1
        on_how_many_customers = {
            prt: prt_counts[prt].count_overlapping(asiakas.voimassa)
            for prt in asiakas.rakennukset
        }
        
        if all(
            customer_count in (1, 2)
            for customer_count in on_how_many_customers.values()
        ):
            counts["prt vain yhdella tai kahdella asiakkaalla"] += 1
            rakennukset = _find_by_prt(session, asiakas.rakennukset)
            if rakennukset:
                if prt_on_single_customer(
                    rakennukset, on_how_many_customers
                ):
                    counts["prt yhdellä tai jos kahdella, niin kaikki paritaloja"] += 1

                    if len(rakennukset) > 1:
                        area = convex_hull_area_of_buildings(rakennukset)
                    if len(rakennukset) == 1 or area < AREA_LIMIT:
                        counts["uniikki prt - koko ok"] += 1
                        return rakennukset
                    else:
                        counts["uniikki prt - koko liian iso"] += 1
            else:
                counts["uniikki prt - rakennuksia ei löydy"] += 1

    # 2. Tarkista asunto-osakeyhtiön Y-tunnuksen perusteella
    if asiakas.haltija.ytunnus and is_asoy(asiakas.haltija.nimi):
        rakennukset = _find_by_ytunnus(session, asiakas.haltija)
        if rakennukset:
            counts["asoy"] += 1
            if all(
                match_omistaja(rakennus, asiakas.haltija, preprocessor=clean_asoy_name)
                for rakennus in rakennukset
            ):
                counts["asoy - omistaja ok"] += 1
                if len(rakennukset) > 1:
                    area = convex_hull_area_of_buildings(rakennukset)
                if len(rakennukset) == 1 or area < AREA_LIMIT:
                    counts["asoy - omistaja ok - koko ok"] += 1
                    return rakennukset
            else:
                counts["asoy - väärä omistaja"] += 1

    # 3. Tarkista osoitteen perusteella 
    rakennukset = _find_by_address(session, asiakas.haltija)
    if rakennukset:
        omistajat = set()
        for rakennus in rakennukset:
            omistajat.add(
                frozenset(
                    omistaja.osapuoli_id 
                    for omistaja in rakennus.rakennuksen_omistajat_collection
                )
            )
        
        # Tarkista rakennusten etäisyys ja pinta-ala
        if len(rakennukset) > 1:
            min_distance = minimum_distance_of_buildings(rakennukset)
            area = convex_hull_area_of_buildings(rakennukset)
            if min_distance <= DISTANCE_LIMIT and area < AREA_LIMIT:
                return rakennukset
        else:
            return rakennukset

    return []


def find_building_candidates_for_kohde(session: "Session", asiakas: "Asiakas") -> List[Rakennus]:
   """
   Etsii rakennusehdokkaat kohteelle käyttäen rakennustietoja asiakkaasta.
   
   Rakennusehdokkaita etsitään seuraavassa järjestyksessä:
   1. PRT-tunnuksen perusteella
   2. Y-tunnuksen perusteella jos kyseessä asunto-osakeyhtiö 
   3. Osoitteen perusteella

   Ehdokasrakennuksia käytetään kun rakennuksia ei voida suoraan yhdistää kohteeseen,
   mutta ne ovat potentiaalisia kohteen rakennuksia myöhempää tarkistusta varten.

   Args:
       session: SQLAlchemy-tietokantaistunto
       asiakas: Asiakas-objekti joka sisältää tarvittavat tiedot haulle:
               - rakennukset (PRT-tunnukset)
               - haltija.ytunnus (jos asunto-osakeyhtiö)
               - haltija.osoite (osoitetiedot)

   Returns:
       List[Rakennus]: Lista löydetyistä rakennusehdokkaista. Lista voi olla tyhjä jos
                       ehdokkaita ei löydy millään kriteerillä.

   Raises:
       Ei nosta poikkeuksia. Jos hakuja ei voida suorittaa (esim. puutteelliset tiedot),
       palautetaan tyhjä lista.
   """
   logger = logging.getLogger(__name__)
   logger.debug(f"Etsitään rakennusehdokkaita asiakkaalle: {asiakas.asiakasnumero.tunnus}")

   # 1. Yritä löytää rakennukset PRT-tunnuksella
   if asiakas.rakennukset:
       logger.debug(f"Etsitään PRT-tunnuksilla: {asiakas.rakennukset}")
       rakennukset = _find_by_prt(session, asiakas.rakennukset)
       if rakennukset:
           logger.debug(f"Löydettiin {len(rakennukset)} rakennusta PRT:llä")
           return rakennukset

   # 2. Jos asunto-osakeyhtiö, yritä löytää Y-tunnuksella
   if asiakas.haltija.ytunnus and is_asoy(asiakas.haltija.nimi):
       logger.debug(f"Etsitään Y-tunnuksella: {asiakas.haltija.ytunnus}")
       rakennukset = _find_by_ytunnus(session, asiakas.haltija)
       if rakennukset:
           logger.debug(f"Löydettiin {len(rakennukset)} rakennusta Y-tunnuksella")
           return rakennukset

   # 3. Viimeisenä yritä löytää osoitteella
   if asiakas.haltija.osoite:
       logger.debug(
           f"Etsitään osoitteella: {asiakas.haltija.osoite.katunimi} "
           f"{asiakas.haltija.osoite.osoitenumero}"
       )
       rakennukset = _find_by_address(session, asiakas.haltija)
       if rakennukset:
           logger.debug(f"Löydettiin {len(rakennukset)} rakennusta osoitteella")
           return rakennukset

   logger.debug("Ei löytynyt rakennusehdokkaita millään kriteerillä")
   return []


def find_single_building_id_by_prt(session: "Session", prt: Rakennustunnus):
    rakennus_ehdokkaat = _find_by_prt(session, [prt])
    if len(rakennus_ehdokkaat) == 1:
        return rakennus_ehdokkaat[0].id
    return None


def _find_by_ytunnus(session: "Session", haltija: "Yhteystieto") -> List[Rakennus]:
   """
   Etsii rakennukset Y-tunnuksen perusteella.
   
   Args:
       session: Tietokantaistunto
       haltija: Yhteystieto-objekti joka sisältää Y-tunnuksen

   Returns:
       Lista löydetyistä rakennuksista
   """
   if not haltija.ytunnus:
       return []
       
   statement = (
       select(Rakennus)
       .join(RakennuksenOmistajat)
       .join(Osapuoli)
       .where(Osapuoli.ytunnus == haltija.ytunnus)
   )
   return session.execute(statement).scalars().all()


def _find_by_address(session: "Session", haltija: "Yhteystieto") -> List[Rakennus]:
   """
   Etsii rakennukset osoitteen perusteella.
   
   Osoitehaussa huomioidaan:
   - Katuosoite (katunimi_fi ja katunimi_sv)
   - Osoitenumero (huomioiden myös mahdolliset kirjaimet)
   - Postinumero
   
   Args:
       session: Tietokantaistunto
       haltija: Yhteystieto-objekti joka sisältää osoitetiedot

   Returns:
       Lista löydetyistä rakennuksista
   """
   try:
       katunimi_lower = haltija.osoite.katunimi.lower().strip()
   except AttributeError:
       return []

   # Osoitenumeron käsittely
   if haltija.osoite.osoitenumero and "-" in haltija.osoite.osoitenumero:
       osoitenumerot = haltija.osoite.osoitenumero.split("-", maxsplit=1)
   else:
       osoitenumerot = [haltija.osoite.osoitenumero]

   # Huoneistotunnuksen käsittely mahdollisena osoitenumeron osana
   potential_osoitenumero_suffix = (
       haltija.osoite.huoneistotunnus.lower() 
       if haltija.osoite.huoneistotunnus 
       else ""
   )

   if potential_osoitenumero_suffix:
       osoitenumero_condition = and_(
           Osoite.osoitenumero.ilike(haltija.osoite.osoitenumero + "%"),
           Osoite.osoitenumero.ilike("%" + potential_osoitenumero_suffix),
       )
   else:
       osoitenumero_condition = Osoite.osoitenumero.in_(osoitenumerot)

   statement = (
       select(Rakennus)
       .join(Osoite)
       .join(Katu)
       .where(
           Osoite.posti_numero == haltija.osoite.postinumero,
           or_(
               sqlalchemyFunc.lower(Katu.katunimi_fi) == katunimi_lower,
               sqlalchemyFunc.lower(Katu.katunimi_sv) == katunimi_lower,
           ),
           osoitenumero_condition,
       )
       .distinct()
   )

   return session.execute(statement).scalars().all()


def _find_by_prt(session: "Session", prt_list: List[Rakennustunnus]) -> List[Rakennus]:
   """
   Etsii rakennukset PRT-tunnusten perusteella.

   Args:
       session: Tietokantaistunto
       prt_list: Lista PRT-tunnuksia

   Returns:
       Lista löydetyistä rakennuksista
   """
   statement = select(Rakennus).where(Rakennus.prt.in_(prt_list))
   return session.execute(statement).scalars().all()


def _verify_rakennukset(
    session: "Session", rakennukset: List[Rakennus], asiakas: "Yhteystieto"
):

    return rakennukset


def find_osoite_by_prt(
    session: "Session", asiakas: Union["JkrIlmoitukset", "LopetusIlmoitus"]
):
    if hasattr(asiakas, 'sijainti_prt'):
        prts = asiakas.sijainti_prt
    else:
        prts = asiakas.prt

    for prt in prts:
        rakennus = session.query(Rakennus).filter_by(prt=prt).first()
        if rakennus:
            osoite = (
                session.query(Osoite)
                .filter_by(rakennus_id=rakennus.id)
                .first()
            )
            if osoite:
                return osoite.id
    return None
