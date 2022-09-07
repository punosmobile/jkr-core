import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Dict, List, Optional

from geoalchemy2.shape import to_shape
from shapely.geometry import MultiPoint
from sqlalchemy import func as sqlalchemyFunc
from sqlalchemy import select

from jkrimporter.model import Rakennustunnus
from jkrimporter.providers.db.utils import clean_asoy_name, is_asoy

from .. import codes
from ..codes import RakennuksenKayttotarkoitusTyyppi
from ..models import Katu, Kunta, Osapuoli, Osoite, Posti, Rakennus

logger = logging.getLogger(__name__)

AREA_LIMIT = 30000

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from jkrimporter.model import Asiakas, Yhteystieto


def convex_hull_area_of_buildings(buildings):
    points = [to_shape(building.geom) for building in buildings if building.geom]
    multipoint = MultiPoint(points)

    convex_hull = multipoint.convex_hull.buffer(6)
    area = convex_hull.area

    return area


def match_omistaja(rakennus, haltija, preprocessor=lambda x: x):
    omistajat = rakennus.osapuoli_collection
    return any(
        preprocessor(haltija.nimi).lower() == preprocessor(omistaja.nimi).lower()
        for omistaja in omistajat
    )


counts: Dict[str, int] = defaultdict(int)


def find_buildings_for_kohde(
    session: "Session",
    asiakas: "Asiakas",
    prt_counts: Optional[Dict[str, int]] = None,
    kitu_counts: Optional[Dict[str, int]] = None,
    address_counts: Optional[Dict[str, int]] = None,
):
    counts["asiakkaita"] += 1
    rakennukset = []
    if asiakas.rakennukset:
        counts["on prt"] += 1
        if all(prt_counts[prt] in (1, 2) for prt in asiakas.rakennukset):
            counts["prt vain yhdella tai kahdella asiakkaalla"] += 1

            rakennukset = _find_by_prt(session, asiakas.rakennukset)
            if rakennukset:
                if all(
                    prt_counts[rakennus.prt] == 1
                    or prt_counts[rakennus.prt] == 2
                    and rakennus.rakennuksenkayttotarkoitus
                    == codes.rakennuksenkayttotarkoitukset[
                        RakennuksenKayttotarkoitusTyyppi.PARITALO
                    ]
                    for rakennus in rakennukset
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

    elif asiakas.kiinteistot:
        counts["on kitu"] += 1
        if all(kitu_counts[kitu] == 1 for kitu in asiakas.kiinteistot):
            counts["uniikki kitu"] += 1

            rakennukset = _find_by_kiinteisto(session, asiakas.kiinteistot)
            if rakennukset:
                omistajat = set()
                for rakennus in rakennukset:
                    omistajat.add(
                        frozenset(
                            osapuoli.id for osapuoli in rakennus.osapuoli_collection
                        )
                    )
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

    elif asiakas.haltija.ytunnus and is_asoy(asiakas.haltija.nimi):
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

    elif address_counts[asiakas.haltija.osoite.osoite_rakennus()] == 1:
        rakennukset = _find_by_address(session, asiakas.haltija)
        if rakennukset:
            counts["osoitteella löytyi"] += 1
            if rakennukset:
                omistajat = set()
                for rakennus in rakennukset:
                    omistajat.add(
                        frozenset(
                            osapuoli.id for osapuoli in rakennus.osapuoli_collection
                        )
                    )
                if len(omistajat) == 1:
                    counts["osoitteella löytyi - kaikilla sama omistaja"] += 1
                    if len(rakennukset) > 1:
                        area = convex_hull_area_of_buildings(rakennukset)
                    if len(rakennukset) == 1 or area < AREA_LIMIT:
                        counts[
                            "osoitteella löytyi - kaikilla sama omistaja - koko ok"
                        ] += 1
                        return rakennukset

    return []


def _find_by_ytunnus(session: "Session", haltija: "Yhteystieto"):
    if haltija.ytunnus:
        statement = (
            select(Rakennus)
            .join(Rakennus.osapuoli_collection)
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

    statement = (
        select(Rakennus)
        .join(Osoite)
        .join(Katu)
        .join(Kunta)
        .join(Posti)
        .where(
            Posti.numero == haltija.osoite.postinumero,
            sqlalchemyFunc.lower(Katu.katunimi_fi) == katunimi_lower,
            Osoite.osoitenumero == haltija.osoite.osoitenumero,
        )
        .distinct()
    )

    rakennukset = session.execute(statement).scalars().all()

    return rakennukset


def _find_by_prt(session: "Session", prt_list: List[Rakennustunnus]) -> List[Rakennus]:
    statement = select(Rakennus).where(Rakennus.prt.in_(prt_list))
    rakennukset = session.execute(statement).scalars().all()

    return rakennukset


def _verify_rakennukset(
    session: "Session", rakennukset: List[Rakennus], asiakas: "Yhteystieto"
):

    return rakennukset
