import subprocess
from datetime import datetime

import pytest
from sqlalchemy import and_, create_engine, distinct, func, or_, select
from sqlalchemy.orm import Session

from jkrimporter import conf
from jkrimporter.cli.jkr import (
    import_data,
    import_ilmoitukset,
    import_paatokset,
    tiedontuottaja_add_new,
)
from jkrimporter.providers.db.codes import init_code_objects
from jkrimporter.providers.db.database import json_dumps
from jkrimporter.providers.db.dbprovider import import_dvv_kohteet
from jkrimporter.providers.db.models import (
    Jatetyyppi,
    Kohde,
    KohteenOsapuolet,
    Kompostori,
    KompostorinKohteet,
    Kuljetus,
    Osapuolenrooli,
    Osapuoli,
    RakennuksenOmistajat,
    RakennuksenVanhimmat,
    Sopimus,
    Tiedontuottaja,
    Viranomaispaatokset,
)


@pytest.fixture(scope="module", autouse=True)
def engine():
    engine = create_engine(
        "postgresql://{username}:{password}@{host}:{port}/{dbname}".format(
            **conf.dbconf
        ),
        future=True,
        json_serializer=json_dumps,
    )
    return engine


def test_osapuolenrooli(engine):
    osapuolenroolit = [
        (1, "Omistaja"),
        (2, "Vanhin asukas"),
        (11, "Tilaaja sekajäte"),
        (12, "Tilaaja biojäte"),
        (13, "Tilaaja muovipakkaus"),
        (14, "Tilaaja kartonkipakkaus"),
        (15, "Tilaaja lasipakkaus"),
        (16, "Tilaaja metalli"),
        (17, "Tilaaja monilokero"),
        (18, "Tilaaja liete"),
        (111, "Kimppaisäntä sekajäte"),
        (112, "Kimppaisäntä biojäte"),
        (113, "Kimppaisäntä muovipakkaus"),
        (114, "Kimppaisäntä kartonkipakkaus"),
        (115, "Kimppaisäntä lasipakkaus"),
        (116, "Kimppaisäntä metalli"),
        (211, "Kimppaosakas sekajäte"),
        (212, "Kimppaosakas biojäte"),
        (213, "Kimppaosakas muovipakkaus"),
        (214, "Kimppaosakas kartonkipakkaus"),
        (215, "Kimppaosakas lasipakkaus"),
        (216, "Kimppaosakas metalli"),
        (311, "Yhteyshenkilö kompostointi"),
    ]
    session = Session(engine)
    result = session.execute(select([Osapuolenrooli.id, Osapuolenrooli.selite]))
    assert [tuple(row) for row in result] == osapuolenroolit


def _assert_kohde_has_sopimus_with_jatelaji(
    session, kohde_nimi, jatetyyppi_selite, exists=True
):
    jatetyyppi_id = (
        select([Jatetyyppi.id])
        .where(Jatetyyppi.selite == jatetyyppi_selite)
        .scalar_subquery()
    )
    kohde_nimi_filter = Kohde.nimi == kohde_nimi
    kohde_id = session.query(Kohde.id).filter(kohde_nimi_filter).scalar()
    if exists:
        assert (
            session.query(Sopimus.id)
            .filter(Sopimus.kohde_id == kohde_id)
            .filter(Sopimus.jatetyyppi_id == jatetyyppi_id)
            .scalar()
            is not None
        )
    else:
        assert (
            session.query(Sopimus.id)
            .filter(Sopimus.kohde_id == kohde_id)
            .filter(Sopimus.jatetyyppi_id == jatetyyppi_id)
            .scalar()
            is None
        )


def _assert_kohde_has_kuljetus_with_jatelaji(
    session, kohde_nimi, jatetyyppi_selite, exists=True
):
    jatetyyppi_id = (
        select([Jatetyyppi.id])
        .where(Jatetyyppi.selite == jatetyyppi_selite)
        .scalar_subquery()
    )
    kohde_nimi_filter = Kohde.nimi == kohde_nimi
    kohde_id = session.query(Kohde.id).filter(kohde_nimi_filter).scalar()
    if exists:
        assert (
            session.query(Kuljetus.id)
            .filter(Kuljetus.kohde_id == kohde_id)
            .filter(Kuljetus.jatetyyppi_id == jatetyyppi_id)
            .scalar()
            is not None
        )
    else:
        assert (
            session.query(Kuljetus.id)
            .filter(Kuljetus.kohde_id == kohde_id)
            .filter(Kuljetus.jatetyyppi_id == jatetyyppi_id)
            .scalar()
            is None
        )


def _assert_kohde_has_osapuoli_with_rooli(session, kohde_nimi, rooli_selite):
    kohde_nimi_filter = Kohde.nimi == kohde_nimi
    kohde_id = session.query(Kohde.id).filter(kohde_nimi_filter).scalar()
    osapuolen_roolit_query = select([KohteenOsapuolet.osapuolenrooli_id]).where(
        KohteenOsapuolet.kohde_id == kohde_id
    )
    osapuolen_roolit = [
        row[0] for row in session.execute(osapuolen_roolit_query).fetchall()
    ]
    tilaaja_id = (
        session.query(Osapuolenrooli.id)
        .filter(Osapuolenrooli.selite == rooli_selite)
        .scalar()
    )
    assert tilaaja_id in osapuolen_roolit


def test_import_dvv_kohteet(engine, datadir):
    try:
        with Session(engine) as session:
            init_code_objects(session)
            import_dvv_kohteet(
                session,
                poimintapvm=datetime.strptime("28.1.2022", "%d.%m.%Y").date(),
                perusmaksutiedosto=datadir / "perusmaksurekisteri.xlsx",
            )
    except Exception as e:
        print(f"Creating kohteet failed: {e}")

    # Kohteiden lkm
    lkm_kohteet = 7
    assert session.query(func.count(Kohde.id)).scalar() == lkm_kohteet

    # Kohteiden alkupäivämääränä on poimintapäivämäärä
    alku_pvm_filter = Kohde.alkupvm == func.to_date("2022-01-28", "YYYY-MM-DD")
    assert (
        session.query(func.count(Kohde.id)).filter(alku_pvm_filter).scalar()
        == lkm_kohteet
    )

    # Perusmaksurekisteristä luodulla kohteella Asunto Oy Kahden Laulumuisto on loppupäivämäärä
    kohde_nimi_filter = Kohde.nimi == "Asunto Oy Kahden Laulumuisto"
    loppu_pvm_filter = Kohde.loppupvm == func.to_date("2100-01-01", "YYYY-MM-DD")
    kohde_id = (
        session.query(Kohde.id)
        .filter(kohde_nimi_filter)
        .filter(loppu_pvm_filter)
        .scalar()
    )
    assert kohde_id is not None

    # Muilla kohteilla ei loppupäivämäärää
    loppu_pvm_filter = Kohde.loppupvm != None
    assert session.query(func.count(Kohde.id)).filter(loppu_pvm_filter).scalar() == 1

    # Kaikilla kohteilla vähintään yksi omistaja
    kohteet = select(Kohde.id)
    kohteet_having_omistaja = select([distinct(KohteenOsapuolet.kohde_id)]).where(
        KohteenOsapuolet.osapuolenrooli_id == 1
    )
    assert [row[0] for row in session.execute(kohteet)] == [
        row[0] for row in session.execute(kohteet_having_omistaja)
    ]

    # Kohteissa nimeltä Forsström, Kemp ja Lindroth vain yksi asuttu huoneisto, vanhin asukas osapuoleksi
    kohde_nimi_filter = or_(
        Kohde.nimi == "Forsström", Kohde.nimi == "Kemp", Kohde.nimi == "Lindroth"
    )
    vanhin_asukas_filter = KohteenOsapuolet.osapuolenrooli_id == 2
    kohde_ids = session.execute(select(Kohde.id).where(kohde_nimi_filter)).fetchall()
    vanhin_asukas_id = session.execute(
        select(KohteenOsapuolet.kohde_id).where(vanhin_asukas_filter)
    ).fetchall()
    assert kohde_ids == vanhin_asukas_id

    # Muissa kohteissa ei vanhinta asukasta osapuolena
    assert (
        session.query(func.count(KohteenOsapuolet.kohde_id))
        .filter(vanhin_asukas_filter)
        .scalar()
        == 3
    )

    # Lisätään kuljetukset kohteelle Kemp
    tiedontuottaja_add_new("LSJ", "Testituottaja")
    import_data(
        datadir + "/kuljetus1", "LSJ", False, False, True, "1.1.2022", "31.12.2022"
    )
    _assert_kohde_has_sopimus_with_jatelaji(session, "Kemp", "Sekajäte")
    _assert_kohde_has_kuljetus_with_jatelaji(session, "Kemp", "Sekajäte")
    import_data(
        datadir + "/kuljetus2", "LSJ", False, False, True, "1.1.2023", "31.12.2023"
    )
    _assert_kohde_has_sopimus_with_jatelaji(session, "Kemp", "Kartonki")
    _assert_kohde_has_kuljetus_with_jatelaji(session, "Kemp", "Kartonki")

    # Lisätään päätökset kohteelle Kemp
    import_paatokset(datadir + "/paatokset.xlsx")

    # Lisätään kompostointi-ilmoitukset kohteelle Kemp
    import_ilmoitukset(datadir + "/ilmoitukset.xlsx")


def _assert_kohteen_alkupvm(session, pvmstr, nimi):
    kohde_nimi_filter = Kohde.nimi == nimi
    alku_pvm_filter = Kohde.alkupvm == func.to_date(pvmstr, "YYYY-MM-DD")
    kohde_id = (
        session.query(Kohde.id)
        .filter(kohde_nimi_filter)
        .filter(alku_pvm_filter)
        .scalar()
    )
    assert kohde_id is not None


def _assert_kohteen_loppupvm(session, pvmstr, nimi):
    kohde_nimi_filter = Kohde.nimi == nimi
    loppu_pvm_filter = Kohde.loppupvm == func.to_date(pvmstr, "YYYY-MM-DD")
    kohde_id = (
        session.query(Kohde.id)
        .filter(kohde_nimi_filter)
        .filter(loppu_pvm_filter)
        .scalar()
    )
    assert kohde_id is not None


def _remove_kuljetusdata_from_database(session):
    session.query(Kuljetus).delete()
    session.query(Sopimus).delete()
    session.query(Osapuoli).filter(
        Osapuoli.tiedontuottaja_tunnus == "0000000-0"
    ).delete()
    session.query(Tiedontuottaja).filter(Tiedontuottaja.tunnus == "0000000-0").delete()
    session.query(Tiedontuottaja).filter(Tiedontuottaja.tunnus == "LSJ").delete()
    session.commit()


def _remove_paatosdata_from_database(session):
    session.query(Viranomaispaatokset).delete()
    session.commit()


def _remove_kompostoridata_from_database(session):
    session.query(KompostorinKohteet).delete()
    session.query(Kompostori).delete()
    session.commit()


def test_update_dvv_kohteet(engine, datadir):
    # Updating the test database created before test fixtures
    update_test_db_command = ".\\scripts\\update_database.bat"
    try:
        subprocess.check_output(
            update_test_db_command, shell=True, stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        print(f"Creating test database failed: {e.output}")

    try:
        with Session(engine) as session:
            init_code_objects(session)
            import_dvv_kohteet(
                session, poimintapvm=datetime.strptime("31.1.2023", "%d.%m.%Y").date()
            )
    except Exception as e:
        print(f"Updating kohteet failed: {e}")

    # Kohteiden lkm
    assert session.query(func.count(Kohde.id)).scalar() == 11

    # Perusmaksurekisteristä luodun kohteen Asunto Oy Kahden Laulumuisto loppupäivämäärä ei ole muuttunut
    _assert_kohteen_loppupvm(session, "2100-01-01", "Asunto Oy Kahden Laulumuisto")

    # Päättyneelle kohteelle Kemp (asukas vaihtunut) asetettu loppupäivämäärät oikein
    _assert_kohteen_loppupvm(session, "2022-06-16", "Kemp")
    osapuoli_nimi_filter = Osapuoli.nimi == "Kemp Johan"
    osapuoli_tiedontuottaja_filter = Osapuoli.tiedontuottaja_tunnus == "dvv"
    osapuoli_id = (
        session.query(Osapuoli.id)
        .filter(osapuoli_nimi_filter)
        .filter(osapuoli_tiedontuottaja_filter)
        .scalar()
    )
    loppu_pvm_filter = RakennuksenVanhimmat.loppupvm == func.to_date(
        "2022-06-16", "YYYY-MM-DD"
    )
    rakennuksen_vanhimmat_id = (
        session.query(RakennuksenVanhimmat.id)
        .filter(RakennuksenVanhimmat.osapuoli_id == osapuoli_id)
        .filter(loppu_pvm_filter)
        .scalar()
    )
    assert rakennuksen_vanhimmat_id is not None

    # Päättyneelle ja uudelle kohteelle Riipinen (asukas vaihtunut) asetettu alku- ja loppupäivämäärät oikein
    _assert_kohteen_alkupvm(session, "2022-01-28", "Riipinen")
    _assert_kohteen_loppupvm(session, "2023-01-30", "Riipinen")
    _assert_kohteen_alkupvm(session, "2023-01-31", "Riipinen")

    # Päättyneelle kohteelle Pohjonen (omistaja vaihtunut) asetettu loppupäivämäärät oikein
    _assert_kohteen_loppupvm(session, "2023-01-22", "Pohjonen")
    osapuoli_nimi_filter = Osapuoli.nimi == "Pohjonen Aarno Armas"
    osapuoli_id = session.query(Osapuoli.id).filter(osapuoli_nimi_filter).scalar()
    loppu_pvm_filter = RakennuksenOmistajat.omistuksen_loppupvm == func.to_date(
        "2023-01-22", "YYYY-MM-DD"
    )
    rakennuksen_vanhimmat_id = (
        session.query(RakennuksenOmistajat.id)
        .filter(RakennuksenOmistajat.osapuoli_id == osapuoli_id)
        .filter(loppu_pvm_filter)
        .scalar()
    )
    assert rakennuksen_vanhimmat_id is not None

    # Muilla kohteilla ei loppupäivämäärää
    loppu_pvm_filter = Kohde.loppupvm != None
    assert session.query(func.count(Kohde.id)).filter(loppu_pvm_filter).scalar() == 4

    # Uudessa kohteessa Kyykoski osapuolina Granström (omistaja) ja Kyykoski (uusi asukas)
    kohde_filter = and_(Kohde.nimi == "Kyykoski", Kohde.alkupvm == "2022-06-17")
    kohde_id = session.execute(select(Kohde.id).where(kohde_filter)).fetchone()[0]
    osapuoli_filter = or_(
        Osapuoli.nimi.like("Granström%"),
        Osapuoli.nimi.like("Kyykoski%"),
        # Osapuoli.nimi.like("Pyykoski%"),
    )
    osapuoli_ids = (
        session.query(Osapuoli.id).filter(osapuoli_filter).order_by(Osapuoli.id)
    )
    kohteen_osapuolet_ids = (
        session.query(KohteenOsapuolet.osapuoli_id)
        .filter(KohteenOsapuolet.kohde_id == kohde_id)
        .order_by(KohteenOsapuolet.osapuoli_id)
    )
    assert [r1.id for r1 in osapuoli_ids] == [
        r2.osapuoli_id for r2 in kohteen_osapuolet_ids
    ]

    # Uudella kohteella Tuntematon ei ole osapuolia
    kohde_nimi_filter = Kohde.nimi == "Tuntematon"
    kohde_id = session.query(Kohde.id).filter(kohde_nimi_filter).scalar()
    assert (
        session.query(func.count(KohteenOsapuolet.osapuoli_id))
        .filter(KohteenOsapuolet.kohde_id == kohde_id)
        .scalar()
        == 0
    )

    # Saman ajanjakson sopimukset ja kuljetukset ovat siirtyneet Kempiltä Kyykoskelle
    _assert_kohde_has_sopimus_with_jatelaji(session, "Kemp", "Sekajäte", False)
    _assert_kohde_has_kuljetus_with_jatelaji(session, "Kemp", "Sekajäte", False)
    _assert_kohde_has_sopimus_with_jatelaji(session, "Kemp", "Kartonki", False)
    _assert_kohde_has_kuljetus_with_jatelaji(session, "Kemp", "Kartonki", False)
    _assert_kohde_has_sopimus_with_jatelaji(session, "Kemp", "Biojäte", False)
    _assert_kohde_has_kuljetus_with_jatelaji(session, "Kemp", "Biojäte", False)
    _assert_kohde_has_sopimus_with_jatelaji(session, "Kemp", "Metalli")
    _assert_kohde_has_kuljetus_with_jatelaji(session, "Kemp", "Metalli")
    _assert_kohde_has_sopimus_with_jatelaji(session, "Kyykoski", "Sekajäte")
    _assert_kohde_has_kuljetus_with_jatelaji(session, "Kyykoski", "Sekajäte")
    _assert_kohde_has_sopimus_with_jatelaji(session, "Kyykoski", "Kartonki")
    _assert_kohde_has_kuljetus_with_jatelaji(session, "Kyykoski", "Kartonki")
    _assert_kohde_has_sopimus_with_jatelaji(session, "Kyykoski", "Metalli")
    _assert_kohde_has_kuljetus_with_jatelaji(session, "Kyykoski", "Metalli")
    _assert_kohde_has_sopimus_with_jatelaji(session, "Kyykoski", "Biojäte")
    _assert_kohde_has_kuljetus_with_jatelaji(session, "Kyykoski", "Biojäte")

    # Kyykoskelle syntyy tilaajarooli seuraavasta kuljetuksesta
    import_data(
        datadir + "/kuljetus3", "LSJ", False, False, True, "1.4.2023", "30.6.2023"
    )
    _assert_kohde_has_osapuoli_with_rooli(session, "Kyykoski", "Tilaaja sekajäte")
    _remove_kuljetusdata_from_database(session)

    # Kempin viranonmaispäätökselle on vaihdettu loppupäivämäärä ja luotu uusi
    loppu_pvm_filter = Viranomaispaatokset.loppupvm == func.to_date(
        "2022-06-16", "YYYY-MM-DD"
    )
    new_paatos_filter = Viranomaispaatokset.loppupvm == func.to_date(
        "2100-01-01", "YYYY-MM-DD"
    )
    assert (
        session.query(func.count(Viranomaispaatokset.id))
        .filter(loppu_pvm_filter)
        .scalar()
        == 1
    )
    assert (
        session.query(func.count(Viranomaispaatokset.id))
        .filter(new_paatos_filter)
        .scalar()
        == 1
    )
    _remove_paatosdata_from_database(session)

    # Kempin kompostorille on vaihdettu loppupäivämäärä ja luotu uusi.
    loppu_pvm_filter = Kompostori.loppupvm == func.to_date(
        "2022-06-16", "YYYY-MM-DD"
    )
    new_ilmoitus_filter = Kompostori.loppupvm == func.to_date(
        "2027-01-11", "YYYY-MM-DD"
    )
    assert (
        session.query(func.count(Kompostori.id))
        .filter(loppu_pvm_filter)
        .scalar()
        == 1
    )
    assert (
        session.query(func.count(Kompostori.id))
        .filter(new_ilmoitus_filter)
        .scalar()
        == 1
    )
    _remove_kompostoridata_from_database(session)
