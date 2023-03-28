import datetime
import re
from collections import defaultdict
from functools import lru_cache
from typing import TYPE_CHECKING

from openpyxl import load_workbook
from psycopg2.extras import DateRange
from sqlalchemy import and_, exists
from sqlalchemy import func as sqlalchemyFunc
from sqlalchemy import or_, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm.decl_api import DeclarativeMeta

from jkrimporter.model import Yhteystieto

from .. import codes
from ..codes import KohdeTyyppi, OsapuolenrooliTyyppi, RakennuksenKayttotarkoitusTyyppi
from ..models import (
    Katu,
    Kohde,
    KohteenOsapuolet,
    KohteenRakennukset,
    Osapuoli,
    Osoite,
    RakennuksenOmistajat,
    RakennuksenVanhimmat,
    Rakennus,
    UlkoinenAsiakastieto,
)
from ..utils import clean_asoy_name, form_display_name, is_asoy, is_company, is_yhteiso

if TYPE_CHECKING:
    from pathlib import Path
    from typing import (
        Callable,
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

    from jkrimporter.model import Asiakas, Tunnus

    class Kohdetiedot(NamedTuple):
        kohde: Kohde
        rakennukset: FrozenSet[KohteenRakennukset]
        lisarakennukset: FrozenSet[KohteenRakennukset]
        asukkaat: FrozenSet[KohteenOsapuolet]
        omistajat: FrozenSet[KohteenOsapuolet]

    class Rakennustiedot(NamedTuple):
        rakennus: Rakennus
        vanhimmat: FrozenSet[RakennuksenVanhimmat]
        omistajat: FrozenSet[RakennuksenOmistajat]
        osoitteet: FrozenSet[Osoite]


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


def find_kohde_by_prt(session: "Session", asiakas: "Asiakas") -> "Union[Kohde, None]":
    print(f"asiakas has prts {asiakas.rakennukset}")
    return _find_kohde_by_asiakastiedot(
        session, Rakennus.prt.in_(asiakas.rakennukset), asiakas
    )


def find_kohde_by_kiinteisto(
    session: "Session", asiakas: "Asiakas"
) -> "Union[Kohde, None]":
    print(f"asiakas has kiinteistöt {asiakas.kiinteistot}")
    return _find_kohde_by_asiakastiedot(
        session, Rakennus.kiinteistotunnus.in_(asiakas.kiinteistot), asiakas
    )


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
    # TODO: Do we need to check the kohde has vanhemmat with the correct
    # huoneistotunnus?
    # We do it when adding buildings to a new kohde in buildings.py.

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


def _find_kohde_by_asiakastiedot(
    session: "Session", filter, asiakas: "Asiakas"
) -> "Union[Kohde, None]":
    # The same kohde may be client at multiple urakoitsijat and have multiple customer
    # ids. Do *not* filter by missing/existing customer id.
    print(filter)
    query = (
        select(Kohde.id, Osapuoli.nimi)
        .join(Kohde.rakennus_collection)
        .join(KohteenOsapuolet)
        .join(Osapuoli)
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
    # TODO: etsi kohde etsimällä rakennukset käyttäen find_buildings_for_kohde
    # funktiota. Valitse näistä oikea kohde.
    ...


def get_dvv_rakennustiedot_without_kohde(
    session: "Session",
    alkupvm: "Optional[datetime.date]",
    loppupvm: "Optional[datetime.date]",
) -> "Dict[int, Rakennustiedot]":
    # Fastest to load everything to memory first.
    rakennus_id_with_current_kohde = (
        select(Rakennus.id)
        .join(KohteenRakennukset)
        .join(Kohde)
        .filter(Kohde.voimassaolo.overlaps(DateRange(alkupvm, loppupvm)))
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
                Rakennus.kaytostapoisto_pvm > alkupvm,
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


def _is_significant_building(rakennustiedot: "Rakennustiedot"):
    """
    Determines which buildings should always be contained in a kohde, either separate
    or combined with other buildings. This function requires rakennustiedot, because
    any building with a permanent inhabitant (no matter what the building type) is
    always significant, if it has an owner. Conversely, if owners are not found, the
    building cannot be created separately as kohde.
    """
    rakennus = rakennustiedot[0]
    asukkaat = rakennustiedot[1]
    omistajat = rakennustiedot[2]
    return omistajat and (
        asukkaat
        or rakennus.rakennuksenkayttotarkoitus
        in (
            codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.YKSITTAISTALO
            ],
            codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.PARITALO
            ],
            codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.MUU_PIENTALO
            ],
            codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.RIVITALO
            ],
            codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.LUHTITALO
            ],
            codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.KETJUTALO
            ],
            codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.KERROSTALO
            ],
            codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.VAPAA_AJANASUNTO
            ],
            codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.MUU_ASUNTOLA
            ],
            codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.VANHAINKOTI
            ],
            codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.LASTENKOTI
            ],
            codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.KEHITYSVAMMAHOITOLAITOS
            ],
            codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.MUU_HUOLTOLAITOS
            ],
            codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.PAIVAKOTI
            ],
            codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.MUU_SOSIAALITOIMEN_RAKENNUS
            ],
            codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.YLEISSIVISTAVA_OPPILAITOS
            ],
            codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.AMMATILLINEN_OPPILAITOS
            ],
            codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.KORKEAKOULU
            ],
            codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.TUTKIMUSLAITOS
            ],
            codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.OPETUSRAKENNUS
            ],
            codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.MUU_OPETUSRAKENNUS
            ],
            codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.SAUNA],
        )
    )


def _add_auxiliary_buildings(
    dvv_rakennustiedot: "Dict[int, Rakennustiedot]",
    building_sets: "List[Set[Rakennustiedot]]",
) -> "List[Set[Rakennustiedot]]":
    """
    For each building set, adds any auxiliary building(s) on the same kiinteistö(t)
    having the same owner(s) (or missing owners!) and address(es) as any of the existing
    buildings.
    """
    dvv_rakennustiedot_by_kiinteistotunnus: "dict[int, Set[Rakennustiedot]]" = (
        defaultdict(set)
    )
    for rakennus, vanhimmat, omistajat, osoitteet in dvv_rakennustiedot.values():
        dvv_rakennustiedot_by_kiinteistotunnus[rakennus.kiinteistotunnus].add(
            (rakennus, vanhimmat, omistajat, osoitteet)
        )
    print(f"Found {len(dvv_rakennustiedot_by_kiinteistotunnus)} DVV kiinteistöt")
    sets_to_return: "List[Set[Rakennustiedot]]" = []
    for building_set in building_sets:
        set_to_return = building_set.copy()
        print("---")
        print(f"Adding to building set {set_to_return}")
        for building, elders, owners, addresses in building_set:
            print(f"has inhabitants {elders}")
            print(f"has owners {owners}")
            print(f"has addresses {addresses}")
            kiinteistotunnus = building.kiinteistotunnus
            owner_ids = {owner.osapuoli_id for owner in owners}
            # Some buildings have missing kiinteistötunnus. Cannot join them =)
            if kiinteistotunnus:
                # TODO: check maximum distance!!
                print(f"has kiinteistötunnus {kiinteistotunnus}")
                kiinteiston_lisarakennukset: "Set[Rakennustiedot]" = {
                    rakennustiedot
                    for rakennustiedot in dvv_rakennustiedot_by_kiinteistotunnus[  # noqa
                        kiinteistotunnus
                    ]
                    if not _is_significant_building(rakennustiedot)
                }
                if kiinteiston_lisarakennukset:
                    print(f"has lisärakennukset {kiinteiston_lisarakennukset}")

                # only add lisärakennukset having at least one common owner and address,
                # or no owner and common address
                rakennustiedot_to_add = {
                    (rakennus, vanhimmat, omistajat, osoitteet)
                    for rakennus, vanhimmat, omistajat, osoitteet in kiinteiston_lisarakennukset
                    if (
                        not omistajat
                        or (  # owner ids must match if present!
                            {omistaja.osapuoli_id for omistaja in omistajat} & owner_ids
                        )
                    )
                    and _match_addresses(osoitteet, addresses)
                }
                # If the addresses or owners differ, remaining objects on the same
                # kiinteistö will create separate kohteet in the last import stage,
                # if they are significant
                print(f"owners own only {rakennustiedot_to_add} at same address")

                # Only add auxiliary buildings to one kohde, remove them from
                # future processing. They are mapped to the first owner and address
                # found.
                dvv_rakennustiedot_by_kiinteistotunnus[
                    kiinteistotunnus
                ] -= rakennustiedot_to_add
                print(
                    f"Remaining rakennustiedot {dvv_rakennustiedot_by_kiinteistotunnus[kiinteistotunnus]}"
                )
                set_to_return |= rakennustiedot_to_add
        print(f"Final building set {set_to_return}")
        sets_to_return.append(set_to_return)
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


def create_new_kohde_from_buildings(
    session: "Session",
    rakennus_ids: "List[int]",
    asukkaat: "Set[Osapuoli]",
    omistajat: "Set[Osapuoli]",
    alkupvm: "Optional[datetime.date]",
    loppupvm: "Optional[datetime.date]",
):
    """
    Create combined kohde for the given list of building ids. Asukkaat or, if empty,
    omistajat will be used for kohde name. Asukkaat will be added as asiakkaat, and
    omistajat will be added as yhteystiedot.
    """
    if asukkaat:
        asiakas = next(iter(asukkaat))
    else:
        # prefer companies over private owners when naming combined objects
        asoy_asiakkaat = {osapuoli for osapuoli in omistajat if is_asoy(osapuoli.nimi)}
        company_asiakkaat = {
            osapuoli for osapuoli in omistajat if is_company(osapuoli.nimi)
        }
        yhteiso_asiakkaat = {
            osapuoli for osapuoli in omistajat if is_yhteiso(osapuoli.nimi)
        }
        if asoy_asiakkaat:
            asiakas = next(iter(asoy_asiakkaat))
        elif company_asiakkaat:
            asiakas = next(iter(company_asiakkaat))
        elif yhteiso_asiakkaat:
            asiakas = next(iter(yhteiso_asiakkaat))
        elif omistajat:
            asiakas = next(iter(omistajat))
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
            osapuolenrooli=codes.osapuolenroolit[OsapuolenrooliTyyppi.ASIAKAS],
        )
        session.add(asiakas)
    # save all omistajat as yhteystiedot, even if they also live in the building.
    # This is needed so the kohde can be identified by owner at later import.
    for osapuoli in omistajat:
        yhteystieto = KohteenOsapuolet(
            osapuoli_id=osapuoli.id,
            kohde_id=kohde.id,
            osapuolenrooli=codes.osapuolenroolit[OsapuolenrooliTyyppi.YHTEYSTIETO],
        )
        session.add(yhteystieto)
    return kohde


def update_or_create_kohde_from_buildings(
    session: "Session",
    dvv_rakennustiedot: "Dict[int, Rakennustiedot]",
    rakennukset: "Set[Rakennustiedot]",
    asukkaat: "Set[Osapuoli]",
    omistajat: "Set[Osapuoli]",
    alkupvm: "Optional[datetime.date]",
    loppupvm: "Optional[datetime.date]"
):
    """
    Check the database for existing kohde with the same inhabitants, owners and
    significant building_ids. Create new kohde if not found.

    Input building ids, as well as existing database building ids, are checked
    so that non-significant building ids are discarded.

    Therefore, the existing kohde may have more *or* less auxiliary buildings than the
    incoming kohde. In that case, we will use existing kohde, but add or remove the
    buildings that have changed.

    In case of paritalo, we don't know which owner owned which part of the building.
    Therefore, we will have to create new kohteet for both halves when somebody sells
    their half.
    """
    rakennus_ids = {rakennustiedot[0].id for rakennustiedot in rakennukset}
    # Incoming building list may have extra auxiliary buildings
    significant_buildings = set(
        filter(lambda x: _is_significant_building(x), rakennukset)
    )
    significant_building_ids = {
        rakennustiedot[0].id for rakennustiedot in significant_buildings
    }
    asukas_ids = {osapuoli.id for osapuoli in asukkaat}
    omistaja_ids = {osapuoli.id for osapuoli in omistajat}
    osapuoli_ids = asukas_ids | omistaja_ids
    print(
        f"looking for existing kohde with buildings {rakennus_ids}, inhabitants {asukas_ids} and owners {omistaja_ids}"
    )
    # List all kohde buildings here, check significance later. We may need to add and remove
    # significant buildings if kohde is found.
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

    # List significant buildings, auxiliary buildings, inhabitants and owners for each kohde
    kohdetiedot_by_kohde: "dict[int, Kohdetiedot]" = {}
    for kohde, rakennus, osapuoli in potential_kohdetiedot:
        if kohde.id not in kohdetiedot_by_kohde:
            kohdetiedot_by_kohde[kohde.id] = (kohde, set(), set(), set(), set())
        # Separate significant and auxiliary buildings
        if _is_significant_building(dvv_rakennustiedot[rakennus.rakennus_id]):
            kohdetiedot_by_kohde[kohde.id][1].add(rakennus)
        else:
            kohdetiedot_by_kohde[kohde.id][2].add(rakennus)
        # separate asukkaat from omistajat
        if (
            osapuoli.osapuolenrooli_id
            == codes.osapuolenroolit[OsapuolenrooliTyyppi.ASIAKAS].id
        ):
            kohdetiedot_by_kohde[kohde.id][3].add(osapuoli)
        if (
            osapuoli.osapuolenrooli_id
            == codes.osapuolenroolit[OsapuolenrooliTyyppi.YHTEYSTIETO].id
        ):
            kohdetiedot_by_kohde[kohde.id][4].add(osapuoli)
    for kohdetiedot in kohdetiedot_by_kohde.values():
        kohde = kohdetiedot[0]
        kohteen_rakennus_ids = set(rakennus.rakennus_id for rakennus in kohdetiedot[1])
        if not kohteen_rakennus_ids:
            # If kohde has no significant buildings, it should not be there in the first place
            continue
        kohteen_lisarakennukset = set(rakennus for rakennus in kohdetiedot[2])
        kohteen_lisarakennus_ids = set(
            rakennus.rakennus_id for rakennus in kohdetiedot[2]
        )
        kohteen_asukas_ids = set(osapuoli.osapuoli_id for osapuoli in kohdetiedot[3])
        kohteen_omistaja_ids = set(osapuoli.osapuoli_id for osapuoli in kohdetiedot[4])
        print("checking significant buildings of potential kohde")
        print(kohdetiedot)
        # 1) use kohde if rakennukset and osapuolet are same
        if (
            kohteen_rakennus_ids == significant_building_ids
            and kohteen_asukas_ids == asukas_ids
            and kohteen_omistaja_ids == omistaja_ids
        ):
            break
        # 3) discard kohde if rakennukset are missing
        if significant_building_ids < kohteen_rakennus_ids:
            continue
        # 4) use kohde if rakennukset are added
        if (
            kohteen_rakennus_ids < significant_building_ids
            and kohteen_asukas_ids == asukas_ids
            and kohteen_omistaja_ids == omistaja_ids
        ):
            break
        # 4, 5, 6) discard kohde if owners or inhabitants have changed
        if kohteen_asukas_ids != asukas_ids or kohteen_omistaja_ids != omistaja_ids:
            continue
        # All combinations are checked above.
    else:
        print("kohde not found, creating new kohde")
        return create_new_kohde_from_buildings(
            session, rakennus_ids, asukkaat, omistajat, alkupvm, loppupvm
        )

    # Return existing kohde when found
    print("found matching kohde!")
    print(kohdetiedot)
    # Remove extra auxiliary buildings
    for kohteen_rakennus in kohteen_lisarakennukset:
        print("checking auxiliary building")
        print(kohteen_rakennus.rakennus_id)
        if kohteen_rakennus.id not in rakennus_ids:
            print("deleting from kohde")
            session.delete(kohteen_rakennus)
    # Add new auxiliary buildings
    for rakennus_id in rakennus_ids - significant_building_ids:
        print("checking auxiliary building")
        print(rakennus_id)
        print("kohde has auxiliary buildings:")
        print(kohteen_lisarakennus_ids)
        if rakennus_id not in kohteen_lisarakennus_ids:
            print("not found on kohde, adding")
            kohteen_rakennus = KohteenRakennukset(
                rakennus_id=rakennus_id, kohde_id=kohde.id
            )
            session.add(kohteen_rakennus)

    # Update kohde to be valid for the whole import period
    if not alkupvm or (kohde.alkupvm and alkupvm < kohde.alkupvm):
        kohde.alkupvm = alkupvm
    if not loppupvm or (kohde.loppupvm and loppupvm > kohde.loppupvm):
        kohde.loppupvm = loppupvm
    return kohde


def get_or_create_kohteet_from_vanhimmat(
    session: "Session",
    ids: "Select",
    alkupvm: "Optional[datetime.date]",
    loppupvm: "Optional[datetime.date]",
):
    """
    Create one kohde for each RakennuksenVanhimmat osapuoli id provided by
    the select query.
    """
    dvv_rakennustiedot = get_dvv_rakennustiedot_without_kohde(
        session, alkupvm, loppupvm
    )
    # iterate vanhimmat to create kohde with the right name, client and building
    vanhimmat_osapuolet_query = (
        select(RakennuksenVanhimmat, Osapuoli)
        .join(RakennuksenVanhimmat.osapuoli)
        .filter(RakennuksenVanhimmat.osapuoli_id.in_(ids))
    )
    vanhimmat_osapuolet = session.execute(vanhimmat_osapuolet_query).all()
    print(f"Found {len(vanhimmat_osapuolet)} vanhimmat without kohde")
    kohteet = []
    for (vanhin, osapuoli) in vanhimmat_osapuolet:
        # The oldest inhabitant is the customer. Also save owners as backup
        # contacts.
        omistajat_query = (
            select(RakennuksenOmistajat, Osapuoli)
            .join(RakennuksenOmistajat.osapuoli)
            .where(RakennuksenOmistajat.rakennus_id == vanhin.rakennus_id)
        )
        omistajat = {row[1] for row in session.execute(omistajat_query).all()}
        print(f"Building {vanhin.rakennus_id} has owners {omistajat}")
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
            alkupvm,
            loppupvm,
        )
        kohteet.append(kohde)
    return kohteet


def get_or_create_kohteet_from_rakennustiedot(
    session: "Session",
    dvv_rakennustiedot: "Dict[int, Rakennustiedot]",
    building_sets: "List[Set[Rakennustiedot]]",
    owners_by_rakennus_id: "Dict[int, Set[Osapuoli]]",
    inhabitants_by_rakennus_id: "Dict[int, Set[Osapuoli]]",
    alkupvm: "Optional[datetime.date]",
    loppupvm: "Optional[datetime.date]",
):
    # merge empty buildings with same address and owner on kiinteistö(t) to the main
    # building(s), if they are close enough.
    building_sets = _add_auxiliary_buildings(dvv_rakennustiedot, building_sets)
    kohteet = []
    for building_set in building_sets:
        print(f"Getting or creating kohde with {building_set}")
        owners = set().union(
            *[
                owners_by_rakennus_id[rakennustiedot[0].id]
                for rakennustiedot in building_set
            ]
        )
        print(f"Using owners {owners}")
        inhabitants = set().union(
            *[
                inhabitants_by_rakennus_id[rakennustiedot[0].id]
                for rakennustiedot in building_set
            ]
        )
        print(f"Using inhabitants {inhabitants}")

        kohde = update_or_create_kohde_from_buildings(
            session,
            dvv_rakennustiedot,
            building_set,
            inhabitants,
            owners,
            alkupvm,
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
            print(f"comparing {osoite} to {address}")
            if _match_address(osoite, address):
                print("found common address")
                return True
    print("no common addresses!")
    return False


# def _is_auxiliary_building(rakennustiedot: "Rakennustiedot"):
#     """
#     Determines which buildings should always be merged in same kohde with the main
#     building. This function requires rakennustiedot, because any building with a
#     permanent inhabitant (no matter what the building type) is always significant.
#     """
#     # TODO: just use not _is_significant_building?
#     rakennus = rakennustiedot[0]
#     asukkaat = rakennustiedot[1]
#     return not asukkaat and rakennus.rakennuksenkayttotarkoitus in (
#         codes.rakennuksenkayttotarkoitukset[RakennuksenKayttotarkoitusTyyppi.SAUNA],
#         codes.rakennuksenkayttotarkoitukset[
#             RakennuksenKayttotarkoitusTyyppi.TALOUSRAKENNUS
#         ],
#     )


def get_or_create_kohteet_from_kiinteistot(
    session: "Session",
    kiinteistotunnukset: "Select",
    alkupvm: "Optional[datetime.date]",
    loppupvm: "Optional[datetime.date]",
):
    """
    Create at least one kohde from each kiinteistotunnus provided by the select query,
    if the kiinteistotunnus has any buildings without existing kohde for the provided
    time period. Only create separate kohde from *significant* buildings.
    *Non-significant* buildings may be added to kohde or left out.

    If the same kiinteistotunnus has buildings with multiple owners,
    first kohde will contain all buildings owned by the owner with the most buildings.

    Then, create second kohde from remaining significant buildings owned by the owner
    with the second largest number of buildings, etc., until all significant buildings
    have kohde named after their owner.

    Finally, if the buildings have different addresses, separate buildings to
    those having the same address.
    """
    print("Loading kiinteistötunnukset...")
    kiinteistotunnukset = [
        result[0] for result in session.execute(kiinteistotunnukset).all()
    ]
    print(f"Found {len(kiinteistotunnukset)} kiinteistötunnukset to import")
    print("Loading rakennukset...")
    # Fastest to load everything to memory first.
    # Cannot filter buildings to load here by type. *Any* buildings that have an
    # inhabitant should be imported wholesale.
    #
    # We must only filter out buildings with existing kohde here, since the same
    # kiinteistö might have buildings both with and without kohde, in case some
    # buildings have been imported in previous steps.
    dvv_rakennustiedot = get_dvv_rakennustiedot_without_kohde(
        session, alkupvm, loppupvm
    )
    rakennustiedot_by_kiinteistotunnus: Dict[int, Set[Rakennustiedot]] = defaultdict(
        set
    )
    for rakennus, vanhimmat, omistajat, osoitteet in dvv_rakennustiedot.values():
        rakennustiedot_by_kiinteistotunnus[rakennus.kiinteistotunnus].add(
            (rakennus, vanhimmat, omistajat, osoitteet)
        )

    print("Loading omistajat...")
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

    print("Loading vanhimmat...")
    rakennus_inhabitants = session.execute(
        select(RakennuksenVanhimmat.rakennus_id, Osapuoli).join(
            Osapuoli, RakennuksenVanhimmat.osapuoli_id == Osapuoli.id
        )
    ).all()
    inhabitants_by_rakennus_id = defaultdict(set)
    for (rakennus_id, inhabitant) in rakennus_inhabitants:
        inhabitants_by_rakennus_id[rakennus_id].add(inhabitant)

    print("Loading addresses...")
    rakennus_addresses = session.execute(
        select(Rakennus.id, Osoite).join(Osoite, Rakennus.id == Osoite.rakennus_id)
    ).all()
    addresses_by_rakennus_id: "Dict[int, Set[Osoite]]" = defaultdict(set)
    for (rakennus_id, address) in rakennus_addresses:
        addresses_by_rakennus_id[rakennus_id].add(address)

    building_sets: List[Set[Rakennustiedot]] = []
    print("Processing kiinteistötunnukset...")
    for kiinteistotunnus in kiinteistotunnukset:
        print(f"----- Processing kiinteistötunnus {kiinteistotunnus} -----")
        if not kiinteistotunnus:
            # some buildings have missing kiinteistötunnus. cannot import them here.
            continue
        rakennustiedot_to_add = rakennustiedot_by_kiinteistotunnus[kiinteistotunnus]
        # Only use significant buildings to create new kohde.
        ids_to_add = {
            rakennustiedot[0].id
            for rakennustiedot in rakennustiedot_to_add
            if _is_significant_building(rakennustiedot)
        }
        while ids_to_add:
            print("---")
            print("found significant buildings:")
            print(ids_to_add)
            owners = set().union(*[dvv_rakennustiedot[id][2] for id in ids_to_add])
            # Only use significant buildings. Add auxiliary buildings to each building
            # set that is found.
            building_ids_by_owner = {
                owner: ids_to_add & rakennus_ids_by_owner_id[owner.osapuoli_id]
                for owner in owners
            }
            # Start from the owner with the most buildings
            owners_by_buildings = sorted(
                building_ids_by_owner.items(),
                key=lambda item: len(item[1]),
                reverse=True,
            )
            first_owner, building_ids_owned = owners_by_buildings[0]
            # split buildings further by address
            while building_ids_owned:
                # All significant buildings at same address should be together.
                building_ids_by_address = defaultdict(set)
                for building in building_ids_owned:
                    for address in addresses_by_rakennus_id[building]:
                        street = address.katu_id
                        number = address.osoitenumero
                        building_ids_by_address[(street, number)].add(building)
                # Start from the address with the most buildings
                addresses_by_buildings = sorted(
                    building_ids_by_address.items(),
                    key=lambda item: len(item[1]),
                    reverse=True,
                )
                (street, number), building_ids_at_address = addresses_by_buildings[0]
                print(f"Processing street {street} osoitenumero {number}")
                print(f"with buildings {building_ids_at_address}")
                rakennustiedot_at_address = {
                    dvv_rakennustiedot[id] for id in building_ids_at_address
                }
                building_sets.append(rakennustiedot_at_address)
                # do not import the building again from second address
                building_ids_owned -= building_ids_at_address
                ids_to_add -= building_ids_at_address

    kohteet = get_or_create_kohteet_from_rakennustiedot(
        session,
        dvv_rakennustiedot,
        building_sets,
        owners_by_rakennus_id,
        inhabitants_by_rakennus_id,
        alkupvm,
        loppupvm,
    )
    return kohteet


def get_or_create_single_asunto_kohteet(
    session: "Session",
    alkupvm: "Optional[datetime.date]",
    loppupvm: "Optional[datetime.date]",
) -> "List(Kohde)":
    """
    Get or create kohteet from all yksittäistalot that do not have kohde on the
    specified time interval. Also consider yksittäistalot that do not have an
    inhabitant.

    If there are multiple inhabited buildings on a kiinteistö, it will not be imported
    here.
    """
    # Do not import any rakennus with existing kohteet
    rakennus_id_with_current_kohde = (
        select(Rakennus.id)
        .filter(
            Rakennus.rakennuksenkayttotarkoitus
            == codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.YKSITTAISTALO
            ]
        )
        .join(KohteenRakennukset)
        .join(Kohde)
        .filter(Kohde.voimassaolo.overlaps(DateRange(alkupvm, loppupvm)))
    )
    rakennus_id_without_kohde = (
        select(Rakennus.id)
        .filter(
            Rakennus.rakennuksenkayttotarkoitus
            == codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.YKSITTAISTALO
            ]
        )
        .filter(~Rakennus.id.in_(rakennus_id_with_current_kohde))
        # Do not import rakennus that have been removed from DVV data
        .filter(
            or_(
                Rakennus.kaytostapoisto_pvm.is_(None),
                Rakennus.kaytostapoisto_pvm > alkupvm,
            )
        )
    )
    # Oldest inhabitant should get the bill only if there are no multiple
    # yksittäistalo on the same kiinteistö.
    single_asunto_kiinteistotunnus = (
        select(
            Rakennus.kiinteistotunnus,
            sqlalchemyFunc.count(Rakennus.id),
        )
        .filter(Rakennus.id.in_(rakennus_id_without_kohde))
        .group_by(Rakennus.kiinteistotunnus)
        .having(sqlalchemyFunc.count(Rakennus.id) == 1)
    )

    print("Creating single house kohteet...")
    # merge empty buildings on kiinteistö to the main building only if they have the
    # same owner. Separate owners will get separate kohde, OR
    # TODO: optionally, do not create separate kohteet after all??
    return get_or_create_kohteet_from_kiinteistot(
        session, single_asunto_kiinteistotunnus, alkupvm, loppupvm
    )


def get_or_create_paritalo_kohteet(
    session: "Session",
    alkupvm: "Optional[datetime.date]",
    loppupvm: "Optional[datetime.date]",
) -> "List(Kohde)":
    """
    Create kohteet from all paritalo buildings that do not have kohde for the
    specified date range.
    """
    # Each paritalo can belong to a maximum of two kohde. Create both in this
    # step. If there is only one inhabitant (i.e. another flat is empty, flats
    # are combined, etc.), the building already has one kohde from previous
    # step and needs not be imported here.
    paritalo_rakennus_id_with_current_kohde = (
        select(Rakennus.id)
        .filter(
            Rakennus.rakennuksenkayttotarkoitus
            == codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.PARITALO
            ]
        )
        .join(KohteenRakennukset)
        .join(Kohde)
        .filter(Kohde.voimassaolo.overlaps(DateRange(alkupvm, loppupvm)))
    )
    paritalo_rakennus_id_without_kohde = (
        select(Rakennus.id).filter(
            Rakennus.rakennuksenkayttotarkoitus
            == codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.PARITALO
            ]
        )
        # do not import any rakennus with existing kohteet
        .filter(~Rakennus.id.in_(paritalo_rakennus_id_with_current_kohde))
        # Do not import rakennus that have been removed from DVV data
        .filter(
            or_(
                Rakennus.kaytostapoisto_pvm.is_(None),
                Rakennus.kaytostapoisto_pvm > alkupvm,
            )
        )
    )
    vanhimmat_ids = select(RakennuksenVanhimmat.osapuoli_id).filter(
        RakennuksenVanhimmat.rakennus_id.in_(paritalo_rakennus_id_without_kohde)
    )
    print("Creating paritalokohteet...")
    # TODO: instead, merge all empty buildings on kiinteistö to the main building
    # Where to merge? We have two identical owners. Better not merge at all?
    return get_or_create_kohteet_from_vanhimmat(
        session, vanhimmat_ids, alkupvm, loppupvm
    )


def get_or_create_multiple_and_uninhabited_kohteet(
    session: "Session",
    alkupvm: "Optional[datetime.date]",
    loppupvm: "Optional[datetime.date]",
) -> "List(Kohde)":
    """
    Create kohteet from all kiinteistötunnus that have buildings without kohde for the
    specified date range.
    """
    # One kiinteistö and omistaja -> one kohde.
    # - Name after largest omistaja if there are multiple.
    # - Separate buildings in kiinteistö if omistajas differ.
    # - Separate buildings in kiinteistö if osoitteet differ (prevent huge kiinteistöt)

    rakennus_id_with_current_kohde = (
        select(Rakennus.id)
        .join(KohteenRakennukset)
        .join(Kohde)
        .filter(Kohde.voimassaolo.overlaps(DateRange(alkupvm, loppupvm)))
    )
    kiinteistotunnus_without_kohde = (
        select(Rakennus.kiinteistotunnus)
        # TODO: filter building types here. in that case, must also include all
        # buildings with any inhabitants.
        #
        # 1) yhden asunnon talot (tyhjillään)
        # 2) kunnan palvelutoiminta (pitkä lista)
        # 3) vapaa-ajanasunnot (ei perusmaksua/ei perusmaksutiedostoa)
        # 4) kerrostalot, rivitalot jne (ei perusmaksutiedostoa)
        # do not import any rakennus with existing kohteet
        .filter(~Rakennus.id.in_(rakennus_id_with_current_kohde))
        # Do not import rakennus that have been removed from DVV data
        .filter(
            or_(
                Rakennus.kaytostapoisto_pvm.is_(None),
                Rakennus.kaytostapoisto_pvm > alkupvm,
            )
        ).group_by(Rakennus.kiinteistotunnus)
    )
    print("Creating remaining kohteet...")
    # Merge all empty buildings with same owner to the main building.
    # Separate owners will get separate kohde, OR
    # TODO: optionally, do not create separate kohteet after all??
    return get_or_create_kohteet_from_kiinteistot(
        session, kiinteistotunnus_without_kohde, alkupvm, loppupvm
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
    session: "Session",
    perusmaksutiedosto: "Path",
    alkupvm: "Optional[datetime.date]",
    loppupvm: "Optional[datetime.date]",
):
    """
    Create kohteet combining all dvv buildings that have the same asiakasnumero in
    perusmaksurekisteri and have the desired type. No need to import anything from
    perusmaksurekisteri, so we don't want a complete provider for the file.

    Since perusmaksurekisteri may be missing sauna and talousrakennus, add them from
    each kiinteistö, matching owner and address.
    """
    perusmaksut = load_workbook(filename=perusmaksutiedosto)
    sheet = perusmaksut["Tietopyyntö asiakasrekisteristä"]
    # some asiakasnumero occur multiple times for the same prt
    buildings_to_combine = defaultdict(lambda: {"prt": set()})
    for index, row in enumerate(sheet.values):
        # skip header
        if index == 0:
            continue
        asiakasnumero = str(row[2])
        prt = str(row[3])
        # asiakkaan_nimi = row[6].value
        # yhteyshenkilon_nimi = row[7].value
        # katuosoite = row[8].value
        # postitoimipaikka = row[9].value
        buildings_to_combine[asiakasnumero]["prt"].add(prt)
    print(f"Found {len(buildings_to_combine)} perusmaksu clients")

    print("Loading rakennukset...")
    # Fastest to load everything to memory first.
    # Do not import any rakennus with existing kohteet. Kerrostalokohteet
    # are eternal, so they cannot ever be imported again once imported here.
    dvv_rakennustiedot = get_dvv_rakennustiedot_without_kohde(
        session, alkupvm, loppupvm
    )
    print(f"Found {len(dvv_rakennustiedot)} DVV buildings without current kohde")

    dvv_rakennustiedot_by_prt: "Dict[int, Rakennustiedot]" = {}
    for rakennus, vanhimmat, omistajat, osoitteet in dvv_rakennustiedot.values():
        dvv_rakennustiedot_by_prt[rakennus.prt] = (
            rakennus,
            vanhimmat,
            omistajat,
            osoitteet,
        )

    print("Checking perusmaksu clients...")

    building_sets: List[Set[Rakennustiedot]] = []
    for kohde_datum in buildings_to_combine.values():
        kohde_prt = kohde_datum["prt"]
        print(f"Got perusmaksu prt numbers {kohde_prt}")
        building_set: "Set[Rakennustiedot]" = set()
        for prt in kohde_prt:
            try:
                rakennus, omistajat, asukkaat, osoitteet = dvv_rakennustiedot_by_prt[
                    prt
                ]
            except KeyError:
                print(f"PRT {prt} not found in DVV data, skipping building")
                continue
            # NOTE: optionally, add other buildings to building set if already
            # at least one perusmaksu specific building is found, i.e. set is not empty
            if _should_have_perusmaksu_kohde(rakennus):  # or building_set:
                print(
                    f"{rakennus.prt} should be perusmaksukohde or part of perusmaksukohde"
                )
                # add all owners and addresses for each rakennus
                building_set.add((rakennus, omistajat, asukkaat, osoitteet))
        if len(building_set) == 0:
            print("No DVV buildings of desired type found, skipping asiakas")
            continue
        print(f"Combining buildings {building_set}")
        building_sets.append(building_set)

    print("Loading omistajat...")
    rakennus_owners = session.execute(
        select(RakennuksenOmistajat.rakennus_id, Osapuoli).join(
            Osapuoli, RakennuksenOmistajat.osapuoli_id == Osapuoli.id
        )
    ).all()
    owners_by_rakennus_id = defaultdict(set)
    for (rakennus_id, owner) in rakennus_owners:
        owners_by_rakennus_id[rakennus_id].add(owner)

    kohteet = get_or_create_kohteet_from_rakennustiedot(
        session,
        dvv_rakennustiedot,
        building_sets,
        owners_by_rakennus_id,
        # No need to add asukkaat. Asoy kohteet should not be separated or named after
        # inhabitants, and inhabitants should not be contacted.
        defaultdict(set),
        alkupvm,
        None,  # Let's make perusmaksu kohde last forever.
    )
    # TODO: Should rivitalokohteet be created by asukkaat instead? This way, they
    # would be separated by asukkaat (and each kohde created separately), even if
    # they have the same building and same owners.
    return kohteet
