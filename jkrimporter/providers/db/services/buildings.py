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
    Luo hakutaulukko lähekkäisistä rakennuksista hyödyntäen materializoitua näkymää.
    
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
    Päivitä materializoitu näkymä nearby_buildings.
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
    # paritalo = codes.rakennuksenkayttotarkoitukset[
    #     RakennuksenKayttotarkoitusTyyppi.PARITALO
    # ]
    return all(
        prt_counts[rakennus.prt] == 1
        or prt_counts[rakennus.prt] == 2
        for rakennus in rakennukset
    )


def find_buildings_for_kohde(
    session: "Session",
    asiakas: "Asiakas",
    prt_counts: Dict[str, "IntervalCounter"],
    kitu_counts: Dict[str, "IntervalCounter"],
    address_counts: Dict[str, "IntervalCounter"],
):
    print("looking for buildings")
    counts["asiakkaita"] += 1
    rakennukset = []
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
        # TODO: liitetään asiakkaaseen vaikka asiakkaita olisi useampi! Halutaan luoda
        # uusi kohde, vaikka vanha kohde vielä voimassa (asiakas muuttunut). Tosin
        # kuljetustiedoissa ei yleensä prt:tä? => ei ajankohtaista?

    if asiakas.kiinteistot:
        print("has kiinteistöt")
        counts["on kitu"] += 1
        if all(
            kitu_counts[kitu].count_overlapping(asiakas.voimassa) == 1
            for kitu in asiakas.kiinteistot
        ):
            counts["uniikki kitu"] += 1

            rakennukset = _find_by_kiinteisto(session, asiakas.kiinteistot)
            if rakennukset:
                omistajat = set()
                omistajat = {
                    frozenset(omistaja.osapuoli_id for omistaja in rakennus.omistajat)
                    for rakennus in rakennukset
                }
                if len(omistajat) == 1:
                    if len(rakennukset) > 1:
                        area = convex_hull_area_of_buildings(rakennukset)
                    if len(rakennukset) == 1 or area < AREA_LIMIT:
                        counts["uniikki kitu - koko ok"] += 1
                        return rakennukset
                    else:
                        counts["uniikki kitu - koko liian iso"] += 1
                else:
                    counts["uniikki kitu - rakennuksilla monta omistajaa"] += 1
            else:
                counts["uniikki kitu - rakennuksia ei löydy"] += 1

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

    # If we are *not* creating kohteet here at all, each asiakas and address will be
    # present over and over again.
    # 1) The *same* asiakas may have multiple jätetyypit for the same address
    # 2) The *same* address may have deals with multiple asiakas.
    # Just save them all on the same kohde, even if the intervals overlap.
    # TODO: Why aren't overlapping intervals allowed here, will have to ask Lauri?
    # if (
    #     address_counts[asiakas.haltija.osoite.osoite_rakennus()].count_overlapping(
    #         asiakas.voimassa
    #     )
    #     == 1
    # ):
    print("trying to find by address")
    rakennukset = _find_by_address(session, asiakas.haltija)
    if rakennukset:
        print("found some")
        print([rakennus.id for rakennus in rakennukset])
        counts["osoitteella löytyi"] += 1
        omistajat = set()
        for rakennus in rakennukset:
            omistajat.add(
                frozenset(omistaja.osapuoli_id for omistaja in rakennus.omistajat)
            )
        print("has omistajat")
        print(omistajat)
        omistajat = set(filter(lambda osapuolet: osapuolet, omistajat))
        print(omistajat)
        # At the moment, return all buildings, even if they have different owners.
        # TODO: group buildings by owner sets. We are creating new kohteet here,
        # better use the same rules as with old dvv kohteet. Let's ask first if
        # there should be any differences compared to original dvv import, tho.
        return rakennukset
        # TODO: whenever the address has buildings with different owners,
        # the below will not return any buildings. This is as intended in Tampere,
        # but no idea why, let's ask Lauri.
        # if len(omistajat) == 1:
        #     counts["osoitteella löytyi - kaikilla sama omistaja"] += 1
        #     if len(rakennukset) > 1:
        #         area = convex_hull_area_of_buildings(rakennukset)
        #     if len(rakennukset) == 1 or area < AREA_LIMIT:
        #         counts["osoitteella löytyi - kaikilla sama omistaja - koko ok"] += 1
        #         return rakennukset
    print("couldnt find")
    return []


def find_building_candidates_for_kohde(session: "Session", asiakas: "Asiakas"):
    if asiakas.rakennukset:
        return _find_by_prt(session, asiakas.rakennukset)
    elif asiakas.kiinteistot:
        return _find_by_kiinteisto(session, asiakas.kiinteistot)
    elif asiakas.haltija.ytunnus and is_asoy(asiakas.haltija.nimi):
        return _find_by_ytunnus(session, asiakas.haltija)

    return _find_by_address(session, asiakas.haltija)


def find_single_building_id_by_prt(session: "Session", prt: Rakennustunnus):
    rakennus_ehdokkaat = _find_by_prt(session, [prt])
    if len(rakennus_ehdokkaat) == 1:
        return rakennus_ehdokkaat[0].id
    return None


def _find_by_ytunnus(session: "Session", haltija: "Yhteystieto"):
    if haltija.ytunnus:
        statement = (
            select(Rakennus)
            .join(RakennuksenOmistajat)
            .join(Osapuoli)
            .where(Osapuoli.ytunnus == haltija.ytunnus)
        )
        rakennukset = session.execute(statement).scalars().all()

        return rakennukset


def _find_by_kiinteisto(session: "Session", kitu_list: List[str]):
    statement = select(Rakennus).where(Rakennus.kiinteistotunnus.in_(kitu_list))
    rakennukset = session.execute(statement).scalars().all()

    return rakennukset


def _find_by_address(session: "Session", haltija: "Yhteystieto"):
    try:
        katunimi_lower = haltija.osoite.katunimi.lower().strip()
    except AttributeError:
        return ""

    # The osoitenumero may contain dash. In that case, the buildings may be
    # listed as separate in DVV data.
    # Also. osoitenumero may be None and we must match to None too.
    if haltija.osoite.osoitenumero and "-" in haltija.osoite.osoitenumero:
        osoitenumerot = haltija.osoite.osoitenumero.split("-", maxsplit=1)
    else:
        osoitenumerot = [haltija.osoite.osoitenumero]

    # The address parser parses Metsätie 33 A so that 33 is osoitenumero and A is
    # huoneistotunnus. While the parsing is correct, it may very well also mean (and
    # in many cases it means) osoitenumero 33a and empty huoneistonumero.
    potential_osoitenumero_suffix = (
        haltija.osoite.huoneistotunnus.lower() if haltija.osoite.huoneistotunnus else ""
    )
    if potential_osoitenumero_suffix:
        # Find Metsätie 33a by Metsätie 33 A. For simplicity, let's not assume
        # 31-33a exists.
        osoitenumero_condition = and_(
            Osoite.osoitenumero.ilike(haltija.osoite.osoitenumero + "%"),
            Osoite.osoitenumero.ilike("%" + potential_osoitenumero_suffix),
        )
    else:
        # Do *NOT* find Mukkulankatu 51 *AND* Mukkulankatu 51b by Mukkulankatu 51.
        osoitenumero_condition = Osoite.osoitenumero.in_(osoitenumerot)

    # # Find Mukkulankatu 51 by Mukkulankatu 51 B.
    # # Only find Mukkulankatu 51 by Mukkulankatu 51.
    # # Only find Mukkulankatu 51b by Mukkulankatu 51b.
    # osoitenumero_condition = Osoite.osoitenumero.in_(osoitenumerot)

    # Do *NOT* find Sokeritopankatu 18 *AND* Sokeritopankatu 18a by
    # Sokeritopankatu 18 A. Looks like Sokeritopankatu 18, 18 A and 18 B are *all*
    # separate.
    # For some unfathomable reason, huoneistotunnus contains merged kirjain and asunto.
    # Why didn't we parse letter and apartment number separately?
    huoneistokirjain, huoneistonumero = (
        haltija.osoite.huoneistotunnus.split(" ", maxsplit=1)
        if haltija.osoite.huoneistotunnus and " " in haltija.osoite.huoneistotunnus
        else (haltija.osoite.huoneistotunnus, None)
    )
    huoneisto_condition = and_(
        # Vanhin must live in the huoneisto with the same kirjain (and apartment number
        # *if* present).
        Osoite.osoitenumero.in_(osoitenumerot),
        RakennuksenVanhimmat.huoneistokirjain == huoneistokirjain,
        RakennuksenVanhimmat.huoneistonumero == huoneistonumero,
    )

    print(osoitenumero_condition)
    print(osoitenumerot)
    print(haltija.osoite.osoitenumero)
    print(haltija.osoite.postinumero)
    print(katunimi_lower)
    print(huoneisto_condition)
    print(haltija.osoite.huoneistotunnus)
    statement = (
        select(Rakennus)
        .join(Osoite)
        .join(Katu)
        .outerjoin(RakennuksenVanhimmat)  # allow vapaa-ajanrakennukset
        .where(
            Osoite.posti_numero == haltija.osoite.postinumero,
            sqlalchemyFunc.lower(Katu.katunimi_fi) == katunimi_lower,
            or_(
                # Find vapaa-ajanrakennukset even if osoitenumero and kirjain and
                # everything is empty.
                osoitenumero_condition,
                # Find Metsätähtikatu 3 by Metsätähtikatu 3 B. This is a case of
                # paritalo, where the owner of one half has address 3 B, although the
                # building only has address 3. We are creating a new kohde here.
                huoneisto_condition
            ),
        )
        .distinct()
    )

    rakennukset = session.execute(statement).scalars().all()
    print("query returned buildings")
    print(rakennukset)
    return rakennukset


def _find_by_prt(session: "Session", prt_list: List[Rakennustunnus]) -> List[Rakennus]:
    statement = select(Rakennus).where(Rakennus.prt.in_(prt_list))
    rakennukset = session.execute(statement).scalars().all()

    return rakennukset


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
