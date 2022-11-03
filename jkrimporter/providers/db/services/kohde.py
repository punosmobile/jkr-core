import datetime
from functools import lru_cache
from typing import TYPE_CHECKING

from psycopg2.extras import DateRange
from sqlalchemy import and_
from sqlalchemy import func as sqlalchemyFunc
from sqlalchemy import or_, select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.sql import text

from jkrimporter.model import Yhteystieto

from .. import codes
from ..codes import KohdeTyyppi, OsapuolenrooliTyyppi, RakennuksenKayttotarkoitusTyyppi
from ..models import (
    Katu,
    Kohde,
    KohteenOsapuolet,
    KohteenRakennukset,
    Kunta,
    Osapuoli,
    Osoite,
    Rakennus,
    RakennuksenOmistajat,
    RakennuksenVanhimmat,
    UlkoinenAsiakastieto,
)
from ..utils import form_display_name

if TYPE_CHECKING:
    from typing import Union, List

    from sqlalchemy.orm import Session
    from sqlalchemy.sql.selectable import Select

    from jkrimporter.model import Asiakas, Tunnus


def is_aluekerays(asiakas: "Asiakas") -> bool:
    return "aluejätepiste" in asiakas.haltija.nimi.lower()


def find_kohde(session: "Session", asiakas: "Asiakas") -> "Union[Kohde, None]":
    kohde = get_kohde_by_asiakasnumero(session, asiakas.asiakasnumero)
    if kohde:
        return kohde

    # kohde = get_kohde_by_address(session, asiakas)
    # if kohde:
    #     return kohde

    return None


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


def find_or_create_asiakastieto(
    session: "Session", asiakas: "Asiakas"
) -> UlkoinenAsiakastieto:
    tunnus = asiakas.asiakasnumero

    query = select(UlkoinenAsiakastieto).where(
        UlkoinenAsiakastieto.tiedontuottaja_tunnus == tunnus.jarjestelma,
        UlkoinenAsiakastieto.ulkoinen_id == tunnus.tunnus,
    )
    try:
        db_asiakastieto = session.execute(query).scalar_one()
    except NoResultFound:
        db_asiakastieto = UlkoinenAsiakastieto(
            tiedontuottaja_tunnus="PJH", ulkoinen_id=tunnus.tunnus
        )

    return db_asiakastieto


def update_ulkoinen_asiakastieto(ulkoinen_asiakastieto, asiakas: "Asiakas"):
    if ulkoinen_asiakastieto.ulkoinen_asiakastieto != asiakas.ulkoinen_asiakastieto:
        ulkoinen_asiakastieto.ulkoinen_asiakastieto = asiakas.ulkoinen_asiakastieto


def find_kohde_by_asiakastiedot(
    session: "Session", asiakas: "Asiakas"
) -> "Union[Kohde, None]":

    ulkoinen_asiakastieto_exists = (
        select(1)
        .where(
            UlkoinenAsiakastieto.kohde_id == Kohde.id,
            UlkoinenAsiakastieto.tiedontuottaja_tunnus
            == asiakas.asiakasnumero.jarjestelma,
        )
        .exists()
    )

    filters = []
    if (
        asiakas.haltija.osoite.postitoimipaikka
        and asiakas.haltija.osoite.katunimi
        and asiakas.haltija.osoite.osoitenumero
    ):
        filters.append(
            and_(
                sqlalchemyFunc.lower(Kunta.nimi_fi)
                == asiakas.haltija.osoite.postitoimipaikka.lower(),  # TODO: korjaa kunta <> postitoimipaikka
                or_(
                    sqlalchemyFunc.lower(Katu.katunimi_fi)
                    == asiakas.haltija.osoite.katunimi.lower(),
                    sqlalchemyFunc.lower(Katu.katunimi_sv)
                    == asiakas.haltija.osoite.katunimi.lower(),
                ),
                Osoite.osoitenumero == asiakas.haltija.osoite.osoitenumero,
            )
        )
    if asiakas.rakennukset:
        filters.append(Rakennus.prt.in_(asiakas.rakennukset))
    if asiakas.kiinteistot:
        filters.append(Rakennus.kiinteistotunnus.in_(asiakas.kiinteistot))

    query = (
        select(Kohde.id, Osapuoli.nimi)
        .join(Kohde.rakennus_collection)
        .join(KohteenOsapuolet)
        .join(Osapuoli)
        .join(Osoite, isouter=True)
        .join(Katu, isouter=True)
        .join(Kunta, isouter=True)
        .where(
            ~ulkoinen_asiakastieto_exists,
            Kohde.voimassaolo.overlaps(
                DateRange(
                    asiakas.alkupvm or datetime.date.min,
                    asiakas.loppupvm or datetime.date.max,
                )
            ),
            KohteenOsapuolet.osapuolenrooli
            == codes.osapuolenroolit[OsapuolenrooliTyyppi.ASIAKAS],
            or_(*filters),
        )
        .distinct()
    )

    try:
        kohteet = session.execute(query).all()
    except NoResultFound:
        return None

    haltija_name_parts = set(asiakas.haltija.nimi.lower().split())
    for kohde_id, db_asiakas_name in kohteet:
        db_asiakas_name_parts = set(db_asiakas_name.lower().split())
        if haltija_name_parts.issubset(
            db_asiakas_name_parts
        ) or db_asiakas_name_parts.issubset(haltija_name_parts):
            kohde = session.get(Kohde, kohde_id)
            return kohde

    return None


def update_kohde(kohde: Kohde, asiakas: "Asiakas"):
    if kohde.alkupvm != asiakas.alkupvm:
        kohde.alkupvm = asiakas.alkupvm
    if kohde.loppupvm != asiakas.loppupvm:
        kohde.loppupvm = asiakas.loppupvm


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
        alkupvm=asiakas.alkupvm,
        loppupvm=asiakas.loppupvm,
    )

    return kohde


def create_kohteet_from_vanhimmat(session: "Session", ids: "Select"):
    """
    Create separate kohde for each RakennuksenVanhimmat osapuoli id provided by
    the select query.
    """
    # iterate vanhimmat to create kohde with the right name, client and building
    vanhimmat_osapuolet_query = (
        select(RakennuksenVanhimmat, Osapuoli)
        .join(RakennuksenVanhimmat.osapuoli)
        .filter(RakennuksenVanhimmat.osapuoli_id.in_(ids))
    )
    vanhimmat_osapuolet = session.execute(vanhimmat_osapuolet_query).all()
    print(vanhimmat_osapuolet_query)
    print(vanhimmat_osapuolet)
    print(f"Found {len(vanhimmat_osapuolet)} vanhimmat without kohde")
    kohteet = []
    # assert False
    for vanhin_osapuoli in vanhimmat_osapuolet:
        # create kohde first
        kohde_display_name = form_display_name(
            Yhteystieto(vanhin_osapuoli[1].nimi, vanhin_osapuoli[1].katuosoite)
            )
        kohde = Kohde(
            nimi=kohde_display_name,
            kohdetyyppi=codes.kohdetyypit[KohdeTyyppi.KIINTEISTO],
            alkupvm=datetime.date.today()
        )
        session.add(kohde)
        kohteet.append(kohde)
        # we need to get the id for the kohde from db
        session.flush()
        print(f'created kohde {kohde_display_name}')

        # create dependent objects
        kohteen_rakennus = KohteenRakennukset(
            rakennus_id=vanhin_osapuoli[0].rakennus_id,
            kohde_id=kohde.id
        )
        session.add(kohteen_rakennus)
        asiakas = KohteenOsapuolet(
            osapuoli_id=vanhin_osapuoli[0].osapuoli_id,
            kohde_id=kohde.id,
            osapuolenrooli=codes.osapuolenroolit[OsapuolenrooliTyyppi.YHTEYSTIETO]
        )
        session.add(asiakas)
    return kohteet


def create_single_asunto_kohteet(session: "Session") -> "List(Kohde)":
    # also consider multiple buildings with only one combined inhabitant and owner
    # we have to do explicit joins since sqlalchemy ORM gets terribly confused
    # and refuses to cooperate with multiple many-to-many relations between rakennus
    # and osapuoli :(

    # kiinteistotunnus_with_single_omistaja = (
    #     select(Rakennus.kiinteistotunnus, RakennuksenOmistajat.osapuoli_id)
    #     .join(RakennuksenOmistajat, Rakennus.id == RakennuksenOmistajat.rakennus_id)
    #     .group_by(Rakennus.kiinteistotunnus, RakennuksenOmistajat.osapuoli_id)
    #     # This returns kiinteistötunnus for all owners that only own one rakennus!
    #     # .having(sqlalchemyFunc.count(RakennuksenOmistajat.osapuoli_id) == 1)
    #     # vs. owners for all kiinteistötunnus that only have one rakennus
    #     # .having(sqlalchemyFunc.count(Rakennus.kiinteistotunnus) == 1)
    #     # TODO: check owners for all rakennus with same kiinteistotunnus
    # )

    # Why do we need same omistajat? Cannot find a single case where it matters for now.
    # same_omistajat_for_all_rakennus_on_kiinteisto = (
    #     select(RakennuksenOmistajat.osapuoli_id, Rakennus.kiinteistotunnus)
    #     .join(Rakennus, Rakennus.id == RakennuksenOmistajat.rakennus_id)
    #     # all distinct owners for kiinteistötunnus
    #     .distinct(RakennuksenOmistajat.osapuoli_id, Rakennus.kiinteistotunnus)
    #     # TODO: check they own all buildings
    #     .having()
    # )

    # print(same_omistajat_for_all_rakennus_on_kiinteisto)
    # result = session.execute(same_omistajat_for_all_rakennus_on_kiinteisto).all()
    # print(result)
    # print(len(result))

    # Why do we need same omistajat? Cannot find a single case where it matters for now.
    # rakennus_in_single_omistaja_kiinteisto = (
    #     select(Rakennus.id)
    #     # do not import any rakennus with existing kohteet
    #     .filter(~Rakennus.kohde_collection.any())
    #     .filter(Rakennus.kiinteistotunnus.in_(kiinteistotunnus_with_single_omistaja))
    # )

    rakennus_id_without_kohde = (
        select(Rakennus.id)
        .filter(~Rakennus.kohde_collection.any())
    )
    # TODO: this will import also those cases where all buildings have different
    # inhabitants, but each building only has one inhabitant, even if they have a
    # common or separate owners on same kiinteistö.
    single_vanhimmat = (
        select(
            RakennuksenVanhimmat.rakennus_id,
            sqlalchemyFunc.count(RakennuksenVanhimmat.osapuoli_id)
            )
        .filter(RakennuksenVanhimmat.rakennus_id.in_(rakennus_id_without_kohde))
        .group_by(RakennuksenVanhimmat.rakennus_id)
        .having(sqlalchemyFunc.count(RakennuksenVanhimmat.osapuoli_id) == 1)
    )
    single_vanhimmat_rakennus_ids = (
        select(single_vanhimmat.subquery().c.rakennus_id)
    )
    single_vanhimmat_osapuoli_ids = (
        select(RakennuksenVanhimmat.osapuoli_id)
        .filter(RakennuksenVanhimmat.rakennus_id.in_(single_vanhimmat_rakennus_ids))
    )

    print('Creating single house kohteet...')
    return create_kohteet_from_vanhimmat(session, single_vanhimmat_osapuoli_ids)


def create_paritalo_kohteet(session: "Session") -> "List(Kohde)":
    # Each paritalo can belong to a maximum of two kohde. Therefore, we cannot filter
    # out those which already have e.g. one kohde. Filter any osapuoli without kohde?
    paritalo_rakennus_id_without_kohde = (
        select(Rakennus.id)
        .filter(
            Rakennus.rakennuksenkayttotarkoitus == codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.PARITALO
            ]
            )
        .filter(~Rakennus.kohde_collection.any())
    )
    result = session.execute(paritalo_rakennus_id_without_kohde).all()
    print(result)
    print(paritalo_rakennus_id_without_kohde)
    print(f"Found {len(result)} double houses without kohde")

    vanhimmat_ids = (
        select(RakennuksenVanhimmat.osapuoli_id)
        .filter(
            RakennuksenVanhimmat.rakennus_id.in_(paritalo_rakennus_id_without_kohde)
            )
    )
    result = session.execute(vanhimmat_ids).all()
    print(result)
    print(vanhimmat_ids)
    print(f"Found {len(result)} vanhimmat ids without paritalo kohde")
    print('Creating paritalo kohteet...')
    return create_kohteet_from_vanhimmat(session, vanhimmat_ids)
