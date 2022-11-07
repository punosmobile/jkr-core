import datetime
from functools import lru_cache
from typing import TYPE_CHECKING

from openpyxl import load_workbook
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
    RakennuksenOmistajat,
    RakennuksenVanhimmat,
    Rakennus,
    UlkoinenAsiakastieto,
)
from ..utils import form_display_name

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Dict, List, Optional, Set, Union

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


def create_new_kohde_from_buildings(
    session: "Session",
    rakennus_ids: "List[int]",
    osapuoli: "Osapuoli",
):
    """
    Create combined kohde for the given list of building ids. Osapuoli will be
    used for kohde name and contact info.
    """
    kohde_display_name = form_display_name(
        Yhteystieto(osapuoli.nimi, osapuoli.katuosoite, osapuoli.ytunnus)
    )
    kohde = Kohde(
        nimi=kohde_display_name,
        kohdetyyppi=codes.kohdetyypit[KohdeTyyppi.KIINTEISTO],
        alkupvm=datetime.date.today(),
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
    # TODO: a separate query to get all the owners, or is it okay just to pick the first
    # owner as *the* yhteystieto?
    asiakas = KohteenOsapuolet(
        osapuoli_id=osapuoli.id,
        kohde_id=kohde.id,
        osapuolenrooli=codes.osapuolenroolit[OsapuolenrooliTyyppi.YHTEYSTIETO],
    )
    session.add(asiakas)
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
    print(f"Found {len(vanhimmat_osapuolet)} vanhimmat without kohde")
    kohteet = []
    # assert False
    for (vanhin, osapuoli) in vanhimmat_osapuolet:
        kohde = create_new_kohde_from_buildings(
            session, [vanhin.rakennus_id], osapuoli
        )
        kohteet.append(kohde)
    return kohteet


def create_kohteet_from_kiinteisto_and_omistaja(
    session: "Session", kiinteistotunnus_osapuoli_ids: "Select"
):
    """
    Create kohde from each kiinteistotunnus provided by the select query.

    If the query provides multiple osapuoli_ids for the same kiinteistotunnus,
    first kohde will contain all buildings owned by the first owner.

    Then, create second kohde from remaining buildings owned by the second owner,
    etc., until all buildings have kohde named after their owner.
    """
    kiinteistotunnukset_with_osapuoli_ids = session.execute(
        kiinteistotunnus_osapuoli_ids
    ).all()
    # fastest to load the whole rakennus table to memory first
    rakennus_ids = session.execute(select(Rakennus.kiinteistotunnus, Rakennus.id)).all()
    rakennus_ids_by_kiinteistotunnus = {}
    for (tunnus, id) in rakennus_ids:
        if tunnus not in rakennus_ids_by_kiinteistotunnus:
            rakennus_ids_by_kiinteistotunnus[tunnus] = set()
        rakennus_ids_by_kiinteistotunnus[tunnus].add(id)
    kohteet = []
    for (kiinteistotunnus, osapuoli_id) in kiinteistotunnukset_with_osapuoli_ids:
        # check if there are remaining rakennukset
        remaining_rakennukset = session.execute(
            select(Rakennus)
            .filter(Rakennus.kiinteistotunnus == kiinteistotunnus)
            .filter(~Rakennus.kohde_collection.any())
        )
        if remaining_rakennukset:
            pass
            # TODO: create_new_kohde_from_buildings(list(remaining_rakennukset.id), ...)
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
        # do not import any rakennus with existing kohteet
        .filter(~Rakennus.kohde_collection.any())
    )
    # TODO: this will import also those cases where all buildings have different
    # inhabitants, but each building only has one inhabitant, even if they have a
    # common or separate owners on same kiinteistö.
    single_vanhimmat = (
        select(
            RakennuksenVanhimmat.rakennus_id,
            sqlalchemyFunc.count(RakennuksenVanhimmat.osapuoli_id),
        )
        .filter(RakennuksenVanhimmat.rakennus_id.in_(rakennus_id_without_kohde))
        .group_by(RakennuksenVanhimmat.rakennus_id)
        .having(sqlalchemyFunc.count(RakennuksenVanhimmat.osapuoli_id) == 1)
    )
    single_vanhimmat_rakennus_ids = select(single_vanhimmat.subquery().c.rakennus_id)
    single_vanhimmat_osapuoli_ids = select(RakennuksenVanhimmat.osapuoli_id).filter(
        RakennuksenVanhimmat.rakennus_id.in_(single_vanhimmat_rakennus_ids)
    )

    print("Creating single house kohteet...")
    return create_kohteet_from_vanhimmat(session, single_vanhimmat_osapuoli_ids)


def create_paritalo_kohteet(session: "Session") -> "List(Kohde)":
    # Each paritalo can belong to a maximum of two kohde. Therefore, we cannot filter
    # out those which already have e.g. one kohde. Filter any osapuoli without kohde?
    paritalo_rakennus_id_without_kohde = (
        select(Rakennus.id)
        .filter(
            Rakennus.rakennuksenkayttotarkoitus
            == codes.rakennuksenkayttotarkoitukset[
                RakennuksenKayttotarkoitusTyyppi.PARITALO
            ]
        )
        .filter(~Rakennus.kohde_collection.any())
    )
    vanhimmat_ids = select(RakennuksenVanhimmat.osapuoli_id).filter(
        RakennuksenVanhimmat.rakennus_id.in_(paritalo_rakennus_id_without_kohde)
    )
    print("Creating paritalo kohteet...")
    return create_kohteet_from_vanhimmat(session, vanhimmat_ids)


def create_multiple_asunto_kohteet(session: "Session") -> "List(Kohde)":
    # One kiinteistö and omistaja -> one kohde.
    # - Name after first omistaja if there are multiple.
    # - Separate buildings in kiinteistö if omistajas differ.

    # we have to do explicit joins since sqlalchemy ORM gets terribly confused
    # and refuses to cooperate with multiple many-to-many relations between rakennus
    # and osapuoli :(
    kiinteistotunnus_with_omistaja = (
        select(Rakennus.kiinteistotunnus, RakennuksenOmistajat.osapuoli_id).join(
            RakennuksenOmistajat, Rakennus.id == RakennuksenOmistajat.rakennus_id
        )
        # do not import any rakennus with existing kohteet
        .filter(~Rakennus.kohde_collection.any())
        # list all owners for the same kiinteistötunnus
        .group_by(Rakennus.kiinteistotunnus, RakennuksenOmistajat.osapuoli_id)
    )
    result = session.execute(kiinteistotunnus_with_omistaja).all()
    print(f"Found {len(result)} kiinteistötunnus-owner combinations without kohde")
    print("Creating multiple asunto kohteet...")
    return create_kohteet_from_kiinteisto_and_omistaja(
        session, kiinteistotunnus_with_omistaja
    )


def create_perusmaksurekisteri_kohteet(session: "Session", perusmaksutiedosto: "Path"):
    """
    Create kohteet combining all dvv buildings that have the same asiakasnumero in
    perusmaksurekisteri. No need to import anything from perusmaksurekisteri, so
    we don't want a complete provider for the file.
    """
    perusmaksut = load_workbook(filename=perusmaksutiedosto)
    sheet = perusmaksut["Tietopyyntö asiakasrekisteristä"]
    buildings_to_combine = {}
    for index, row in enumerate(sheet.values):
        # skip header
        if index == 0:
            continue
        asiakasnumero = str(row[1])
        prt = str(row[3])
        # asiakkaan_nimi = row[6].value
        # yhteyshenkilon_nimi = row[7].value
        # katuosoite = row[8].value
        # postitoimipaikka = row[9].value
        if asiakasnumero not in buildings_to_combine:
            buildings_to_combine[asiakasnumero] = {}
            # some asiakasnumero occur multiple times for the same prt
            buildings_to_combine[asiakasnumero]["prt"] = set((prt,))
        else:
            buildings_to_combine[asiakasnumero]["prt"].add(prt)
    print(f"Found {len(buildings_to_combine)} perusmaksu clients")
    # Just pick the first owner to name the kohde with.
    dvv_rakennustiedot_query = (
        select(Rakennus.prt, Rakennus.id, Osapuoli)
        .join(Rakennus.osapuoli_collection)
        # do not import any rakennus with existing kohteet
        .filter(~Rakennus.kohde_collection.any())
    )
    dvv_rakennustiedot_by_prt = {
        prt: {"rakennus_id": rakennus_id, "osapuoli": osapuoli}
        for prt, rakennus_id, osapuoli in session.execute(
            dvv_rakennustiedot_query
        ).all()
    }
    print(f"Found {len(dvv_rakennustiedot_by_prt)} DVV buildings without kohde")
    print("Checking if they are perusmaksu clients...")
    kohteet = []
    for kohde_datum in buildings_to_combine.values():
        kohde_prt = kohde_datum["prt"]
        rakennustiedot = []
        for prt in kohde_prt:
            try:
                rakennustieto = dvv_rakennustiedot_by_prt[prt]
            except KeyError:
                print(f"PRT {prt} not found in DVV data, skipping building")
                continue
            rakennustiedot.append(rakennustieto)
        if len(rakennustiedot) == 0:
            print("No DVV buildings found for asiakas, skipping asiakas")
            continue
        # TODO: Try to find an osapuoli with y-tunnus for better naming
        osapuoli = rakennustiedot[0]["osapuoli"]
        kohde = create_new_kohde_from_buildings(
            session, [entry["rakennus_id"] for entry in rakennustiedot], osapuoli
        )
        kohteet.append(kohde)
    return kohteet
