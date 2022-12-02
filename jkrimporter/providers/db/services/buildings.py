import logging
from collections import Iterable, defaultdict
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    FrozenSet,
    List,
    NamedTuple,
    Set,
    Union,
    get_type_hints,
)

from geoalchemy2.shape import to_shape
from shapely.geometry import MultiPoint
from sqlalchemy import and_
from sqlalchemy import func as sqlalchemyFunc
from sqlalchemy import or_, select
from sqlalchemy.sql import false

from jkrimporter.model import Rakennustunnus
from jkrimporter.providers.db.utils import clean_asoy_name, is_asoy

from .. import codes
from ..codes import RakennuksenKayttotarkoitusTyyppi
from ..models import (
    Katu,
    Kohde,
    KohteenOsapuolet,
    Kunta,
    Osapuoli,
    Osoite,
    Posti,
    RakennuksenVanhimmat,
    Rakennus,
    UlkoinenAsiakastieto,
)

logger = logging.getLogger(__name__)

AREA_LIMIT = 30000

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from jkrimporter.model import Asiakas, Yhteystieto


def freeze(unfrozen: Iterable) -> Union[tuple, FrozenSet]:
    """
    Recursively freezes the given iterable. Any contained sets are converted to frozen
    sets and other iterables are converted to tuples for hashing.
    """
    print("freezing")
    print(unfrozen)
    frozen = []
    for item in unfrozen:
        if issubclass(type(item), (set, tuple)):
            item = freeze(item)
        frozen.append(item)
    print("returning")
    print(frozen)
    if type(unfrozen) is set:
        return frozenset(frozen)
    return tuple(frozen)


class Osoitetiedot(NamedTuple):
    osoite: Osoite
    katu: Katu


class Kohdetiedot(NamedTuple):
    kohde: Kohde
    ulkoiset_asiakastiedot: Union[
        Set[UlkoinenAsiakastieto], FrozenSet[UlkoinenAsiakastieto]
    ]
    # Osapuoli ids are only ever needed to match paritalot, the devilish fiends.
    kohteen_osapuolet: Union[Set[KohteenOsapuolet], FrozenSet[KohteenOsapuolet]]


class Rakennustiedot(NamedTuple):
    rakennus: Rakennus
    osapuolet: Union[Set[Osapuoli], FrozenSet[Osapuoli]]
    osoitteet: Union[Set[Osoitetiedot], FrozenSet[Osoitetiedot]]
    # Vanhimmat are only ever needed to match paritalot, the devilish fiends.
    vanhimmat: Union[Set[RakennuksenVanhimmat], FrozenSet[RakennuksenVanhimmat]]
    kohteet: Union[Set[Kohdetiedot], FrozenSet[Kohdetiedot]]


def convex_hull_area_of_buildings(buildings):
    points = [to_shape(building.geom) for building in buildings if building.geom]
    multipoint = MultiPoint(points)

    convex_hull = multipoint.convex_hull.buffer(6)
    area = convex_hull.area

    return area


# def match_omistaja(rakennus, haltija, preprocessor=lambda x: x):
#     omistajat = rakennus.osapuoli_collection
#     return any(
#         preprocessor(haltija.nimi).lower() == preprocessor(omistaja.nimi).lower()
#         for omistaja in omistajat
#     )


counts: Dict[str, int] = defaultdict(int)


def prt_on_single_customer_or_double_house(rakennukset, prt_counts):
    paritalo = codes.rakennuksenkayttotarkoitukset[
        RakennuksenKayttotarkoitusTyyppi.PARITALO
    ]
    return all(
        prt_counts[rakennus.prt] == 1
        or prt_counts[rakennus.prt] == 2
        and rakennus.rakennuksenkayttotarkoitus == paritalo
        for rakennus in rakennukset
    )


def find_buildings_for_kohde(
    rakennustiedot_by_prt: dict[str, Rakennustiedot],
    rakennustiedot_by_kiinteistotunnus: dict[str, Set[Rakennustiedot]],
    rakennustiedot_by_ytunnus: dict[str, Set[Rakennustiedot]],
    rakennustiedot_by_address: dict[tuple, Set[Rakennustiedot]],
    osapuolet_by_id: dict[str, Osapuoli],
    asiakas: "Asiakas",
    prt_counts: Dict[str, "IntervalCounter"],
    kitu_counts: Dict[str, "IntervalCounter"],
    address_counts: Dict[str, "IntervalCounter"],
) -> List[Rakennustiedot]:
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
            rakennustiedot = [rakennustiedot_by_prt[prt] for prt in asiakas.rakennukset]
            if rakennustiedot:
                rakennukset = [tiedot.rakennus for tiedot in rakennustiedot]
                if prt_on_single_customer_or_double_house(
                    rakennukset, on_how_many_customers
                ):
                    counts["prt yhdellä tai jos kahdella, niin kaikki paritaloja"] += 1

                    if len(rakennukset) > 1:
                        area = convex_hull_area_of_buildings(rakennukset)
                    if len(rakennukset) == 1 or area < AREA_LIMIT:
                        counts["uniikki prt - koko ok"] += 1
                        return rakennustiedot
                    else:
                        counts["uniikki prt - koko liian iso"] += 1
            else:
                counts["uniikki prt - rakennuksia ei löydy"] += 1
        # TODO: liitetään asiakkaaseen vaikka asiakkaita olisi useampi!

    if asiakas.kiinteistot:
        print("has kiinteistöt")
        counts["on kitu"] += 1
        if all(
            kitu_counts[kitu].count_overlapping(asiakas.voimassa) == 1
            for kitu in asiakas.kiinteistot
        ):
            counts["uniikki kitu"] += 1

            rakennus_sets = [
                rakennustiedot_by_kiinteistotunnus[kitu] for kitu in asiakas.kiinteistot
            ]
            rakennustiedot = [tiedot for tiedot in rakennus_sets for tiedot in tiedot]
            if rakennustiedot:
                omistajat = set()
                omistajat = {
                    frozenset(osapuoli.id for osapuoli in tiedot.osapuolet)
                    for tiedot in rakennustiedot
                }
                if len(omistajat) == 1:
                    rakennukset = [tiedot.rakennus for tiedot in rakennustiedot]
                    if len(rakennukset) > 1:
                        area = convex_hull_area_of_buildings(rakennukset)
                    if len(rakennukset) == 1 or area < AREA_LIMIT:
                        counts["uniikki kitu - koko ok"] += 1
                        return rakennustiedot
                    else:
                        counts["uniikki kitu - koko liian iso"] += 1
                else:
                    counts["uniikki kitu - rakennuksilla monta omistajaa"] += 1
            else:
                counts["uniikki kitu - rakennuksia ei löydy"] += 1

    if asiakas.haltija.ytunnus and is_asoy(asiakas.haltija.nimi):
        print("trying to find by ytunnus")
        # rakennukset = _find_by_ytunnus(session, asiakas.haltija)
        rakennustiedot = rakennustiedot_by_ytunnus[asiakas.haltija.ytunnus]
        if rakennustiedot:
            counts["asoy"] += 1
            asoy_name = clean_asoy_name(asiakas.haltija.nimi)
            if all(
                any(
                    asoy_name.lower() == osapuoli.nimi.lower()
                    for osapuoli in tiedot.osapuolet
                )
                for tiedot in rakennustiedot
            ):
                counts["asoy - omistaja ok"] += 1
                rakennukset = [tiedot.rakennus for tiedot in rakennustiedot]
                if len(rakennukset) > 1:
                    area = convex_hull_area_of_buildings(rakennukset)
                if len(rakennukset) == 1 or area < AREA_LIMIT:
                    counts["asoy - omistaja ok - koko ok"] += 1
                    return rakennustiedot
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
    rakennustiedot = find_by_address(rakennustiedot_by_address, asiakas.haltija)
    if rakennustiedot:
        print("found some")
        print([tiedot for tiedot in rakennustiedot])
        counts["osoitteella löytyi"] += 1
        omistajat = set()
        for tiedot in rakennustiedot:
            omistajat.add(frozenset(osapuoli.id for osapuoli in tiedot.osapuolet))
        print("has omistajat")
        print(omistajat)
        omistajat = set(filter(lambda osapuolet: osapuolet, omistajat))
        print(omistajat)
        # At the moment, return all buildings, even if they have different owners.
        return rakennustiedot
        # TODO: whenever the address has buildings with different owners,
        # this will not return any buildings. This is as intended in Tampere,
        # but no idea why.
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

    return find_by_address(session, asiakas.haltija)


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


def find_by_address(
    rakennustiedot_by_address: dict[tuple, Set[Rakennustiedot]], haltija: "Yhteystieto"
) -> List[Rakennustiedot]:
    try:
        katunimi_lower = haltija.osoite.katunimi.lower().strip()
    except AttributeError:
        return ""

    # The osoitenumero may contain dash. In that case, the buildings may be
    # listed as separate in DVV data.
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

    print(
        [
            rakennustiedot_by_address[
                (
                    haltija.osoite.postinumero,
                    katunimi_lower,
                    osoitenumero,
                )
            ]
            for osoitenumero in osoitenumerot
        ]
    )
    # - Do *NOT* find Sokeritopankatu 18 *AND* Sokeritopankatu 18a by
    # Sokeritopankatu 18 A. Looks like Sokeritopankatu 18, 18 A and 18 B are *all*
    # separate.
    # - Do *NOT* find Mukkulankatu 51 *AND* Mukkulankatu 51b by Mukkulankatu 51.
    # - Find Mukkulankatu 51 by Mukkulankatu 51 B.
    # - Only find Mukkulankatu 51 by Mukkulankatu 51.
    # - Only find Mukkulankatu 51b by Mukkulankatu 51b.
    rakennustiedot_from_osoitenumerot = [
        # first, check if the letter is actually part of osoitenumero
        rakennustiedot_by_address[
            (
                haltija.osoite.postinumero,
                katunimi_lower,
                osoitenumero + potential_osoitenumero_suffix,
            )
        ]
        or
        # if the letter is not found in osoitenumero, it is huoneistotunnus
        rakennustiedot_by_address[
            (
                haltija.osoite.postinumero,
                katunimi_lower,
                osoitenumero,
            )
        ]
        for osoitenumero in osoitenumerot
    ]
    rakennustiedot = [
        tiedot
        for tiedot in rakennustiedot_from_osoitenumerot
        for tiedot in tiedot
        if tiedot
    ]
    print("osoitenumerot yielded rakennustiedot")
    print(rakennustiedot)
    return rakennustiedot

    # # For some unfathomable reason, huoneistotunnus contains merged kirjain and asunto.
    # # Why didn't we parse letter and apartment number separately?
    # huoneistokirjain, huoneistonumero = (
    #     haltija.osoite.huoneistotunnus.split(" ", maxsplit=1)
    #     if haltija.osoite.huoneistotunnus and " " in haltija.osoite.huoneistotunnus
    #     else (haltija.osoite.huoneistotunnus, None)
    # )
    # huoneisto_condition = and_(
    #     # Vanhin must live in the huoneisto with the same kirjain (and apartment number if present).
    #     Osoite.osoitenumero.in_(osoitenumerot),
    #     RakennuksenVanhimmat.huoneistokirjain == huoneistokirjain,
    #     RakennuksenVanhimmat.huoneistonumero == huoneistonumero,
    # )
    #
    # Find Metsätähtikatu 3 by Metsätähtikatu 3 B. This is a case of paritalo, where
    # the owner of one half has address 3 B, although the building only has address 3.
    # TODO: In case of paritalo, the *asukas* address tells us which is which. The
    # building address is not enough. So let's check the inhabitant address *after* we
    # return the building for kohteet.


def _find_by_prt(session: "Session", prt_list: List[Rakennustunnus]) -> List[Rakennus]:
    statement = select(Rakennus).where(Rakennus.prt.in_(prt_list))
    rakennukset = session.execute(statement).scalars().all()

    return rakennukset


def _verify_rakennukset(
    session: "Session", rakennukset: List[Rakennus], asiakas: "Yhteystieto"
):

    return rakennukset
