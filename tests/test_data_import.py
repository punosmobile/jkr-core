import subprocess
from datetime import datetime

import platform
import csv
import os
from pathlib import Path
import pytest
from sqlalchemy import and_, create_engine, distinct, func, or_, select, text
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
    SopimusTyyppi,
    Tiedontuottaja,
    Viranomaispaatokset,
    Keskeytys,
    Tyhjennysvali,
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
    loppupvm_filter = Kohde.loppupvm == None
    kohde_id = session.query(Kohde.id).filter(kohde_nimi_filter).filter(loppupvm_filter).scalar()
    if exists:
        assert (
            session.query(Sopimus.id)
            .filter(Sopimus.kohde_id == kohde_id)
            .filter(Sopimus.jatetyyppi_id == jatetyyppi_id)
            .scalar()
            is not None
        ), f"Ei sopimuksia kohteelle {kohde_nimi} selitteellä {jatetyyppi_selite}"
    else:
        assert (
            session.query(Sopimus.id)
            .filter(Sopimus.kohde_id == kohde_id)
            .filter(Sopimus.jatetyyppi_id == jatetyyppi_id)
            .scalar()
            is None
        ), f"Saatiin sopimuks kohteelle {kohde_nimi} selitteellä {jatetyyppi_selite}"


def _assert_kohde_has_kuljetus_with_jatelaji(
    session, kohde_nimi, jatetyyppi_selite, exists=True
):
    jatetyyppi_id = (
        select([Jatetyyppi.id])
        .where(Jatetyyppi.selite == jatetyyppi_selite)
        .scalar_subquery()
    )
    kohde_nimi_filter = Kohde.nimi == kohde_nimi
    loppupvm_filter = Kohde.loppupvm == None
    kohde_id = session.query(Kohde.id).filter(kohde_nimi_filter).filter(loppupvm_filter).scalar()
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
    lkm_kohteet = 9
    assert session.query(func.count(Kohde.id)).scalar() == lkm_kohteet

    # Kohteiden alkupäivämääränä on poimintapäivämäärä
    alku_pvm_filter = Kohde.alkupvm == func.to_date("2022-01-28", "YYYY-MM-DD")
    assert (
        session.query(func.count(Kohde.id)).filter(alku_pvm_filter).scalar()
        == lkm_kohteet
    )

    # Perusmaksurekisteristä luodulla kohteella Asunto Oy Kahden Laulumuisto ei ole loppupäivämäärää
    kohde_nimi_filter = Kohde.nimi == "Asunto Oy Kahden Laulumuisto"
    kohde_id = (
        session.query(Kohde.id)
        .filter(kohde_nimi_filter)
        .filter(Kohde.loppupvm.isnot(None))
        .scalar()
    )
    assert kohde_id is None, "Löytyi päättymispäivällisiä kohteita"

    # Muilla kohteilla ei loppupäivämäärää
    loppu_pvm_filter = Kohde.loppupvm != None
    paattyneet_kohteet = session.query(func.count(Kohde.id)).filter(loppu_pvm_filter).scalar()
    assert paattyneet_kohteet == 0, f"Löytyi päättyneitä kohteita {paattyneet_kohteet}"

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
    kohde_ids = [row[0] for row in session.execute(select(Kohde.id).where(kohde_nimi_filter)).fetchall()]
    vanhin_asukas_ids = session.execute(
        select(KohteenOsapuolet.kohde_id).where(
            and_(
                vanhin_asukas_filter,
                KohteenOsapuolet.kohde_id.in_(kohde_ids)
            ))
    ).scalars().all()
    assert kohde_ids == vanhin_asukas_ids, f"Vanhimpia asukkaita on liikaa {kohde_ids} vs {vanhin_asukas_ids}"

    # Muissa kohteissa ei vanhinta asukasta osapuolena - 12.05.2025 havaittu että koodi asettaa lähes kaikki vanhimmmiksi osapuoli asukkaiksi
    assert (
        session.query(func.count(KohteenOsapuolet.kohde_id))
        .filter(vanhin_asukas_filter)
        .scalar()
        == 7
    )

    # Lisätään kuljetukset kohteelle Kemp
    tiedontuottaja_add_new("LSJ", "Testituottaja")
    import_data(
        datadir + "/kuljetus1", "LSJ", False, False, True, "1.1.2022", "31.12.2022"
    )
    _assert_kohde_has_sopimus_with_jatelaji(session, "Asunto Oy Kahden Laulumuisto", "Sekajäte")
    _assert_kohde_has_kuljetus_with_jatelaji(session, "Asunto Oy Kahden Laulumuisto", "Sekajäte")
    import_data(
        datadir + "/kuljetus2", "LSJ", False, False, True, "1.1.2023", "31.12.2023"
    )
    _assert_kohde_has_sopimus_with_jatelaji(session, "Asunto Oy Kahden Laulumuisto", "Kartonki")
    _assert_kohde_has_kuljetus_with_jatelaji(session,"Asunto Oy Kahden Laulumuisto", "Kartonki")

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
        .all()
    )
    assert kohde_id is not None, f"Ei löytynyt alkupäivää {pvmstr} ja nimeä {nimi} vastaavaa kohdetta"


def _assert_kohteen_loppupvm(session, pvmstr, nimi):
    kohde_nimi_filter = Kohde.nimi == nimi
    loppu_pvm_filter = Kohde.loppupvm == func.to_date(pvmstr, "YYYY-MM-DD")
    kohde_id = (
        session.query(Kohde.id)
        .filter(kohde_nimi_filter)
        .filter(loppu_pvm_filter)
        .scalar()
    )
    assert kohde_id is not None, f"Ei löytynyt loppupäivää {pvmstr} ja nimeä {nimi} vastaavaa kohdetta"


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
    if platform.system() == 'Windows':
        update_test_db_command = ".\\scripts\\update_database.bat"
    else:
        update_test_db_command = "./scripts/update_database.sh"

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
    assert session.query(func.count(Kohde.id)).scalar() == 15

    # Perusmaksurekisteristä luodun kohteen Asunto Oy Kahden Laulumuisto loppupäivämäärä ei ole muuttunut
    _assert_kohteen_loppupvm(session, "2023-01-31", "Asunto Oy Kahden Laulumuisto")

    # Päättyneelle kohteelle Kemp (asukas vaihtunut) asetettu loppupäivämäärät oikein
    _assert_kohteen_loppupvm(session, "2023-01-31", "Granström")
    osapuoli_nimi_filter = Osapuoli.nimi == "Kemp Johan"
    osapuoli_tiedontuottaja_filter = Osapuoli.tiedontuottaja_tunnus == "dvv"
    osapuoli_id = (
        session.query(Osapuoli.id)
        .filter(osapuoli_nimi_filter)
        .filter(osapuoli_tiedontuottaja_filter)
        .scalar()
    )
    loppu_pvm_filter = RakennuksenVanhimmat.loppupvm == func.to_date(
        "2023-01-31", "YYYY-MM-DD"
    )
    rakennuksen_vanhimmat_id = (
        session.query(RakennuksenVanhimmat.id)
        .filter(RakennuksenVanhimmat.osapuoli_id == osapuoli_id)
        .filter(loppu_pvm_filter)
        .scalar()
    )
    assert rakennuksen_vanhimmat_id is not None, "Ei löytynyt asukkaita"

    # Päättyneelle ja uudelle kohteelle Kauko (asukas vaihtunut) asetettu alku- ja loppupäivämäärät oikein
    _assert_kohteen_alkupvm(session, "2022-01-28", "Kauko")
    _assert_kohteen_loppupvm(session, "2023-01-31", "Kauko")
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
    assert rakennuksen_vanhimmat_id is not None, "Ei löytynyt asukkaita päivityksen jälkeen"

    # Muilla kohteilla ei loppupäivämäärää
    loppu_pvm_filter = Kohde.loppupvm != None
    assert session.query(func.count(Kohde.id)).filter(loppu_pvm_filter).scalar() == 6, f"Päätyneiden kohteiden määrä ei täsmää, tulisi olla {6}"

    # Uudessa kohteessa Granström osapuolina Granström (omistaja) ja Kemp (uusi asukas)
    kohde_filter = and_(Kohde.nimi == "Granström", Kohde.alkupvm == "2023-01-31")
    kohde_id = session.execute(select(Kohde.id).where(kohde_filter)).fetchone()[0]
    osapuoli_filter = or_(
        Osapuoli.nimi.like("Granström%"),
        Osapuoli.nimi.like("Kemp%"),
        Osapuoli.nimi.like("Pyykoski%"),
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
    _assert_kohde_has_sopimus_with_jatelaji(session, "Asunto Oy Kahden Laulumuisto", "Sekajäte", False)
    _assert_kohde_has_kuljetus_with_jatelaji(session, "Asunto Oy Kahden Laulumuisto", "Sekajäte", False)
    _assert_kohde_has_sopimus_with_jatelaji(session, "Asunto Oy Kahden Laulumuisto", "Kartonki", False)
    _assert_kohde_has_kuljetus_with_jatelaji(session, "Asunto Oy Kahden Laulumuisto", "Kartonki", False)
    _assert_kohde_has_sopimus_with_jatelaji(session, "Asunto Oy Kahden Laulumuisto", "Biojäte", False)
    _assert_kohde_has_kuljetus_with_jatelaji(session, "Asunto Oy Kahden Laulumuisto", "Biojäte", False)
    _assert_kohde_has_sopimus_with_jatelaji(session, "Asunto Oy Kahden Laulumuisto", "Metalli")
    _assert_kohde_has_kuljetus_with_jatelaji(session, "Asunto Oy Kahden Laulumuisto", "Metalli")
    _assert_kohde_has_sopimus_with_jatelaji(session, "Asunto Oy Kahden Laulumuisto", "Sekajäte")
    _assert_kohde_has_kuljetus_with_jatelaji(session, "Asunto Oy Kahden Laulumuisto", "Sekajäte")
    _assert_kohde_has_sopimus_with_jatelaji(session, "Asunto Oy Kahden Laulumuisto", "Kartonki")
    _assert_kohde_has_kuljetus_with_jatelaji(session, "Asunto Oy Kahden Laulumuisto", "Kartonki")
    _assert_kohde_has_sopimus_with_jatelaji(session, "Asunto Oy Kahden Laulumuisto", "Metalli")
    _assert_kohde_has_kuljetus_with_jatelaji(session, "Asunto Oy Kahden Laulumuisto", "Metalli")
    _assert_kohde_has_sopimus_with_jatelaji(session, "Asunto Oy Kahden Laulumuisto", "Biojäte")
    _assert_kohde_has_kuljetus_with_jatelaji(session, "Asunto Oy Kahden Laulumuisto", "Biojäte")

    # Kohteella Asunto Oy Kahden Laulumuisto osapuolina tilaajaroolit eri jätelajeista
    kohde_nimi_filter = Kohde.nimi == 'Asunto Oy Kahden Laulumuisto'
    kohde_loppupvm_filter = Kohde.loppupvm is None
    kohde_id = session.query(Kohde.id).filter(kohde_nimi_filter).filter(kohde_loppupvm_filter).scalar()
    osapuolen_roolit_query = \
        select([KohteenOsapuolet.osapuolenrooli_id]).where(KohteenOsapuolet.kohde_id == kohde_id)
    osapuolen_roolit = [row[0] for row in session.execute(osapuolen_roolit_query).fetchall()]
    sekajate_tilaaja_id = \
        session.query(Osapuolenrooli.id).filter(Osapuolenrooli.selite == 'Tilaaja sekajäte').scalar()
    assert sekajate_tilaaja_id in osapuolen_roolit
    biojate_tilaaja_id = \
        session.query(Osapuolenrooli.id).filter(Osapuolenrooli.selite == 'Tilaaja biojäte').scalar()
    assert biojate_tilaaja_id in osapuolen_roolit
    muovi_tilaaja_id = \
        session.query(Osapuolenrooli.id).filter(Osapuolenrooli.selite == 'Tilaaja muovipakkaus').scalar()
    assert muovi_tilaaja_id in osapuolen_roolit
    kartonki_tilaaja_id = \
        session.query(Osapuolenrooli.id).filter(Osapuolenrooli.selite == 'Tilaaja kartonkipakkaus').scalar()
    assert kartonki_tilaaja_id in osapuolen_roolit
    lasi_tilaaja_id = \
        session.query(Osapuolenrooli.id).filter(Osapuolenrooli.selite == 'Tilaaja lasipakkaus').scalar()
    assert lasi_tilaaja_id in osapuolen_roolit
    metalli_tilaaja_id = \
        session.query(Osapuolenrooli.id).filter(Osapuolenrooli.selite == 'Tilaaja metalli').scalar()
    assert metalli_tilaaja_id in osapuolen_roolit

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

    # Forsströmin kompostori on edelleen voimassa.
    kohde_filter = Kohde.nimi == "Forsström"
    kohde_id = session.execute(select(Kohde.id).where(kohde_filter)).fetchone()[0]
    assert (
        session.query(func.count(KompostorinKohteet.kohde_id))
        .filter(KompostorinKohteet.kohde_id == kohde_id)
        .scalar()
        == 1
    )

    # Kuljetusdatassa on 11 kelvollista sopimusta, joista kaksi on kahden kimppaa.
    lkm_sopimukset = 7
    assert session.query(func.count(Sopimus.id)).scalar() == lkm_sopimukset

    # Sopimuksissa kaksi validia sekajätesopimusta (joista toinen kimppa),
    # kaksi lasisopimusta (eri ajanjaksoilla), kaksi metallisopimusta ja muita yksi kutakin
    sekajate_id = select([Jatetyyppi.id]).where(Jatetyyppi.selite == 'Sekajäte').scalar_subquery()
    seka_sopimus_filter = Sopimus.jatetyyppi_id == sekajate_id
    seka_sopimukset = session.query(func.count(Sopimus.id)).filter(seka_sopimus_filter).scalar()
    assert seka_sopimukset == 1, f"seka sopimuksia ei ole {1}, vaan {seka_sopimukset}"
    biojate_id = select([Jatetyyppi.id]).where(Jatetyyppi.selite == 'Biojäte').scalar_subquery()
    bio_sopimus_filter = Sopimus.jatetyyppi_id == biojate_id
    bio_sopimukset = session.query(func.count(Sopimus.id)).filter(bio_sopimus_filter).scalar()
    assert bio_sopimukset == 1, f"bio sopimuksia ei ole {1}, vaan {bio_sopimukset}"
    lasi_id = select([Jatetyyppi.id]).where(Jatetyyppi.selite == 'Lasi').scalar_subquery()
    lasi_sopimus_filter = Sopimus.jatetyyppi_id == lasi_id
    lasi_sopimukset = session.query(func.count(Sopimus.id)).filter(lasi_sopimus_filter).scalar()
    assert lasi_sopimukset == 2, f"bio sopimuksia ei ole {2}, vaan {lasi_sopimukset}"
    kartonki_id = select([Jatetyyppi.id]).where(Jatetyyppi.selite == 'Kartonki').scalar_subquery()
    kartonki_sopimus_filter = Sopimus.jatetyyppi_id == kartonki_id
    kartonki_sopimukset =session.query(func.count(Sopimus.id)).filter(kartonki_sopimus_filter).scalar()
    assert kartonki_sopimukset == 1, f"kartonki sopimuksia ei ole {1}, vaan {kartonki_sopimukset}"
    metalli_id = select([Jatetyyppi.id]).where(Jatetyyppi.selite == 'Metalli').scalar_subquery()
    metalli_sopimus_filter = Sopimus.jatetyyppi_id == metalli_id
    metalli_sopimukset = session.query(func.count(Sopimus.id)).filter(metalli_sopimus_filter).scalar()
    assert metalli_sopimukset == 1, f"metalli sopimuksia ei ole {1}, vaan {metalli_sopimukset}"
    muovi_id = select([Jatetyyppi.id]).where(Jatetyyppi.selite == 'Muovi').scalar_subquery()
    muovi_sopimus_filter = Sopimus.jatetyyppi_id == muovi_id
    muovi_sopimukset = session.query(func.count(Sopimus.id)).filter(muovi_sopimus_filter).scalar()
    assert muovi_sopimukset == 1, f"muovi sopimuksia ei ole {1}, vaan {muovi_sopimukset}"

    # Kohde Forsström on sekajätekimpan osakas
    kohde_nimi_filter = Kohde.nimi == 'Forsström'
    kohde_loppupvm_filter = Kohde.loppupvm is None
    kohde_id = session.query(Kohde.id).filter(kohde_nimi_filter).filter(kohde_loppupvm_filter).scalar()
    kimppa_sopimus_query = \
        session.query(Sopimus.kimppaisanta_kohde_id, Sopimus.sopimustyyppi_id).\
        filter(Sopimus.kohde_id == kohde_id).filter(Sopimus.jatetyyppi_id == sekajate_id)
    print("kimppa_sopimus")
    print(kohde_id)
    kimppa_sopimus = session.execute(kimppa_sopimus_query).fetchall()
    print(kimppa_sopimus)
    assert kimppa_sopimus and kimppa_sopimus[0][0] is not None, "Sopimuksen kimppaisäntää ei löydy"  # sopimuksella on kimppaisäntä
    assert kimppa_sopimus and kimppa_sopimus[0][1] == \
        session.query(SopimusTyyppi.id).filter(SopimusTyyppi.selite == 'Kimppasopimus').scalar()
    osapuolen_roolit_query = \
        select([KohteenOsapuolet.osapuolenrooli_id]).where(KohteenOsapuolet.kohde_id == kohde_id)
    osapuolen_roolit = [row[0] for row in session.execute(osapuolen_roolit_query).fetchall()]
    sekajate_kimppaosakas_id = \
        session.query(Osapuolenrooli.id).filter(Osapuolenrooli.selite == 'Kimppaosakas sekajäte').scalar()
    assert sekajate_kimppaosakas_id in osapuolen_roolit

    # Kohde Forsström on myös biojätekimpan osakas
    kohde_nimi_filter = Kohde.nimi == 'Forsström'
    kohde_id = session.query(Kohde.id).filter(kohde_nimi_filter).scalar()
    kimppa_sopimus = \
        session.query(Sopimus.kimppaisanta_kohde_id, Sopimus.sopimustyyppi_id).\
        filter(Sopimus.kohde_id == kohde_id).filter(Sopimus.jatetyyppi_id == biojate_id)
    assert kimppa_sopimus and kimppa_sopimus[0][0] is not None  # sopimuksella on kimppaisäntä
    assert kimppa_sopimus and kimppa_sopimus[0][1] == \
        session.query(SopimusTyyppi.id).filter(SopimusTyyppi.selite == 'Kimppasopimus').scalar()
    osapuolen_roolit_query = \
        select([KohteenOsapuolet.osapuolenrooli_id]).where(KohteenOsapuolet.kohde_id == kohde_id)
    osapuolen_roolit = [row[0] for row in session.execute(osapuolen_roolit_query).fetchall()]
    biojate_kimppaosakas_id = \
        session.query(Osapuolenrooli.id).filter(Osapuolenrooli.selite == 'Kimppaosakas biojäte').scalar()
    assert biojate_kimppaosakas_id in osapuolen_roolit

    # Kohde Lindroth on sekajätekimpan isäntä
    kohde_nimi_filter = Kohde.nimi == 'Lindroth'
    kohde_id = session.query(Kohde.id).filter(kohde_nimi_filter).scalar()
    kimppa_sopimus = \
        session.query(Sopimus.kimppaisanta_kohde_id, Sopimus.sopimustyyppi_id).\
        filter(Sopimus.kohde_id == kohde_id).filter(Sopimus.jatetyyppi_id == sekajate_id)
    assert kimppa_sopimus and kimppa_sopimus[0][0] is None  # sopimuksella ei ole kimppaisäntää
    assert kimppa_sopimus and kimppa_sopimus[0][1] == \
        session.query(SopimusTyyppi.id).filter(SopimusTyyppi.selite == 'Kimppasopimus').scalar()
    osapuolen_roolit_query = \
        select([KohteenOsapuolet.osapuolenrooli_id]).where(KohteenOsapuolet.kohde_id == kohde_id)
    osapuolen_roolit = [row[0] for row in session.execute(osapuolen_roolit_query).fetchall()]
    sekajate_kimppaisanta_id = \
        session.query(Osapuolenrooli.id).filter(Osapuolenrooli.selite == 'Kimppaisäntä sekajäte').scalar()
    assert sekajate_kimppaisanta_id in osapuolen_roolit

    # Kohde Lindroth on myös biojätekimpan isäntä
    kohde_nimi_filter = Kohde.nimi == 'Lindroth'
    kohde_id = session.query(Kohde.id).filter(kohde_nimi_filter).scalar()
    kimppa_sopimus = \
        session.query(Sopimus.kimppaisanta_kohde_id, Sopimus.sopimustyyppi_id).\
        filter(Sopimus.kohde_id == kohde_id).filter(Sopimus.jatetyyppi_id == biojate_id)
    assert kimppa_sopimus and kimppa_sopimus[0][0] is None  # sopimuksella ei ole kimppaisäntää
    assert kimppa_sopimus and kimppa_sopimus[0][1] == \
        session.query(SopimusTyyppi.id).filter(SopimusTyyppi.selite == 'Kimppasopimus').scalar()
    osapuolen_roolit_query = \
        select([KohteenOsapuolet.osapuolenrooli_id]).where(KohteenOsapuolet.kohde_id == kohde_id)
    osapuolen_roolit = [row[0] for row in session.execute(osapuolen_roolit_query).fetchall()]
    biojate_kimppaisanta_id = \
        session.query(Osapuolenrooli.id).filter(Osapuolenrooli.selite == 'Kimppaisäntä biojäte').scalar()
    assert biojate_kimppaisanta_id in osapuolen_roolit

    # Kohteella Kyykoski on aluekeräyspistesopimus.
    kohde_nimi_filter = Kohde.nimi == "Kyykoski"
    kohde_id = session.query(Kohde.id).filter(kohde_nimi_filter).scalar()
    akp_sopimus_id = (
        session.query(Sopimus.sopimustyyppi_id)
        .filter(Sopimus.kohde_id == kohde_id)
        .scalar()
    )
    assert (
        akp_sopimus_id
        == session.query(SopimusTyyppi.id)
        .filter(SopimusTyyppi.selite == "Aluekeräyssopimus")
        .scalar()
    )

    # Osapuolettomalla kohteella Tuntematon on sopimus ja kuljetus.
    kohde_nimi_filter = Kohde.nimi == "Tuntematon"
    kohde_id = session.query(Kohde.id).filter(kohde_nimi_filter).scalar()
    assert (
        session.query(Sopimus.id).filter(Sopimus.kohde_id == kohde_id).scalar()
        is not None
    )
    assert (
        session.query(Kuljetus.id).filter(Kuljetus.kohde_id == kohde_id).scalar()
        is not None
    )

    # Kiinteänjätteen massa kenttä on tyhjä.
    assert (
        session.query(func.count(Kuljetus.id)).filter(text("massa is NULL")).scalar()
        == lkm_sopimukset
    )

    # Tyhjennysvalejä on 15, kahdella sopimuksista on useita tyhjennysvälejä.
    assert session.query(func.count(Tyhjennysvali.id)).scalar() == 15


    # Kohteella Asunto Oy Kahden Laulumuisto on kaksi tyhjennysväliä muovijätteellä ja kolme kartongilla.
    kohde_nimi_filter = Kohde.nimi == 'Asunto Oy Kahden Laulumuisto'
    kohde_id = session.query(Kohde.id).filter(kohde_nimi_filter).filter(kohde_loppupvm_filter).scalar()
    muovi_sopimus_id = \
        session.query(Sopimus.id).\
        filter(Sopimus.kohde_id == kohde_id).filter(Sopimus.jatetyyppi_id == muovi_id).scalar()
    muovi_sopimus_tyhjennysvali_count = \
        session.query(func.count()).filter(Tyhjennysvali.sopimus_id == muovi_sopimus_id).scalar()
    assert muovi_sopimus_tyhjennysvali_count == 2
    kartonki_sopimus_id = \
        session.query(Sopimus.id).\
        filter(Sopimus.kohde_id == kohde_id).filter(Sopimus.jatetyyppi_id == kartonki_id).scalar()
    kartonki_sopimus_tyhjennysvali_count = \
        session.query(func.count()).filter(Tyhjennysvali.sopimus_id == kartonki_sopimus_id).scalar()
    assert kartonki_sopimus_tyhjennysvali_count == 3, f"kartonki eroaa {kartonki_sopimus_tyhjennysvali_count} vs 3"

    # Kuljetusdatassa on yksi keskeytys.
    assert session.query(func.count(Keskeytys.id)).scalar() == 1

    # Kohdentumattomat.csv sisältää kahdeksan kohdentumatonta Asiakas-riviä.
    csv_file_path = os.path.join(datadir, "kohdentumattomat_kuljetukset.csv")
    assert os.path.isfile(csv_file_path), f"File not found: {csv_file_path}"
    with open(csv_file_path, 'r') as csvfile:
        csv_reader = csv.reader(csvfile)
        header = next(csv_reader, None)
        assert header is not None
        rows = list(csv_reader)
        assert len(rows) == 8

    # Korjataan kuljetuksen PRT kohdentumattomissa.
    with open(csv_file_path, "r") as csvfile:
        csv_file_content = csvfile.read()
    fixed_content = csv_file_content.replace("000000000W", "100456789B")
    fixed_folder = os.path.join(datadir, "fixed")
    os.makedirs(fixed_folder)
    csv_file_write_path = os.path.join(fixed_folder, "kohdentumattomat_kuljetukset.csv")
    with open(csv_file_write_path, "w") as csvfile:
        csvfile.write(fixed_content)


    import_data(Path(fixed_folder), "LSJ", False, False, True, "1.1.2023", "31.3.2023")

    # Korjattu kuljetus on aiheuttanut uuden sopimuksen sopimus-tauluun.
    lkm_sopimukset += 1
    assert session.query(func.count(Sopimus.id)).scalar() == lkm_sopimukset

    _remove_kompostoridata_from_database(session)
