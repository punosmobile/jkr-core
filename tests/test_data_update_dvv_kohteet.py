import csv
import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from shutil import copytree

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
    Keskeytys,
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
    Tyhjennysvali,
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


@pytest.fixture
def datadir(tmpdir):
    """Käytetään test_data_import-kansiota testidatana."""
    source = Path(__file__).parent / "data" / "test_data_import"
    if source.is_dir():
        copytree(source, tmpdir, dirs_exist_ok=True)
    return tmpdir


def _cleanup_all(engine):
    """Poistaa testin luomat tiedot kannasta FK-järjestyksessä.

    Ei poisteta 'ilmoitus'-tiedontuottajaa (tulee Flyway-migraatiosta V2.30.0)
    eikä 'dvv'-tiedontuottajaa.
    """
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM jkr.kompostorin_kohteet"))
        conn.execute(text("DELETE FROM jkr.kompostori"))
        conn.execute(text("DELETE FROM jkr.keskeytys"))
        conn.execute(text("DELETE FROM jkr.kuljetus"))
        conn.execute(text("DELETE FROM jkr.tyhjennysvali"))
        conn.execute(text("DELETE FROM jkr.sopimus"))
        conn.execute(text("DELETE FROM jkr.viranomaispaatokset"))
        conn.execute(text("DELETE FROM jkr.kohteen_osapuolet"))
        conn.execute(text("DELETE FROM jkr.kohteen_rakennukset"))
        conn.execute(text("DELETE FROM jkr.kohde"))
        conn.execute(text("DELETE FROM jkr.dvv_poimintapvm"))
        # Poistetaan vain testin luomat osapuolet ja tiedontuottajat.
        # 'dvv' ja 'ilmoitus' tulevat migraatiosta/init:stä → ei poisteta.
        conn.execute(text(
            "DELETE FROM jkr.osapuoli "
            "WHERE tiedontuottaja_tunnus NOT IN ('dvv', 'ilmoitus')"
        ))
        conn.execute(text(
            "DELETE FROM jkr_koodistot.tiedontuottaja "
            "WHERE tunnus NOT IN ('dvv', 'ilmoitus')"
        ))
        conn.commit()


def _assert_kohteen_alkupvm(session, pvmstr, nimi):
    kohde = (
        session.query(Kohde.id)
        .filter(Kohde.nimi == nimi)
        .filter(Kohde.alkupvm == func.to_date(pvmstr, "YYYY-MM-DD"))
        .all()
    )
    assert kohde is not None and len(kohde) > 0, \
        f"Ei löytynyt alkupäivää {pvmstr} ja nimeä {nimi} vastaavaa kohdetta"


def _assert_kohteen_loppupvm(session, pvmstr, nimi):
    kohde_id = (
        session.query(Kohde.id)
        .filter(Kohde.nimi == nimi)
        .filter(Kohde.loppupvm == func.to_date(pvmstr, "YYYY-MM-DD"))
        .scalar()
    )
    assert kohde_id is not None, \
        f"Ei löytynyt loppupäivää {pvmstr} ja nimeä {nimi} vastaavaa kohdetta"


def test_update_dvv_kohteet(engine, datadir):
    """Testaa DVV-kohteiden päivitys uudella DVV-poiminnalla.

    Vaiheet:
    1. Luodaan kohteet ensimmäisellä import_dvv_kohteet-ajolla (poimintapvm 28.1.2022)
    2. Päivitetään DVV-raakadata (DVV_update.xlsx → update_database-skripti)
    3. Ajetaan import_dvv_kohteet uudelleen (poimintapvm 31.1.2023)
    4. Tarkistetaan kohteiden päivitykset (loppupvm:t, uudet kohteet, osapuolet)

    Lopussa siivotaan kaikki luodut tietueet.
    """
    _cleanup_all(engine)
    try:
        # --- Vaihe 1: Ensimmäinen import_dvv_kohteet ---
        with Session(engine) as session:
            init_code_objects(session)
            import_dvv_kohteet(
                session,
                poimintapvm=datetime.strptime("28.1.2022", "%d.%m.%Y").date(),
                perusmaksutiedosto=datadir / "perusmaksurekisteri.xlsx",
            )

        # --- Vaihe 2: Tuodaan kuljetukset, päätökset ja ilmoitukset ---
        # Luodaan tiedontuottajat suoraan SQL:llä (typer-komento tekee .upper())
        with engine.connect() as conn:
            conn.execute(text(
                "INSERT INTO jkr_koodistot.tiedontuottaja (tunnus, nimi) "
                "VALUES ('LSJ', 'Testituottaja') ON CONFLICT DO NOTHING"
            ))
            conn.execute(text(
                "INSERT INTO jkr_koodistot.tiedontuottaja (tunnus, nimi) "
                "VALUES ('ilmoitus', 'Ilmoitukset') ON CONFLICT DO NOTHING"
            ))
            conn.commit()

        import_data(str(datadir) + "/kuljetus1", "LSJ", "1.1.2022", "31.12.2022")
        import_data(str(datadir) + "/kuljetus2", "LSJ", "1.1.2023", "31.12.2023")
        import_paatokset(str(datadir) + "/paatokset.xlsx")
        import_ilmoitukset(str(datadir) + "/ilmoitukset.xlsx")

        # --- Vaihe 3: Päivitetään DVV-raakadata ---
        in_container = os.path.exists("/.dockerenv")
        scripts_dir = Path(__file__).parent / "scripts"
        if in_container:
            update_cmd = str(scripts_dir / "update_database_container.sh")
        elif platform.system() == "Windows":
            update_cmd = str(scripts_dir / "update_database.bat")
        else:
            update_cmd = str(scripts_dir / "update_database.sh")

        subprocess.check_output(
            update_cmd, shell=True, stderr=subprocess.STDOUT,
            cwd=str(Path(__file__).parent),
        )

        # --- Vaihe 4: Toinen import_dvv_kohteet ---
        with Session(engine) as session:
            init_code_objects(session)
            import_dvv_kohteet(
                session,
                poimintapvm=datetime.strptime("31.1.2023", "%d.%m.%Y").date(),
            )

            # === Kohteiden lukumäärä ===
            assert session.query(func.count(Kohde.id)).scalar() == 12

            # === Päättyneet kohteet ===
            paattyneet = session.query(func.count(Kohde.id)).filter(
                Kohde.loppupvm != None
            ).scalar()
            assert paattyneet == 3, f"Päättyneitä kohteita: {paattyneet}, odotettiin 3"

            # Päättyneille kohteille oikeat loppupäivämäärät
            _assert_kohteen_loppupvm(session, "2023-01-30", "Granström")
            _assert_kohteen_loppupvm(session, "2023-01-22", "Pohjonen")
            _assert_kohteen_loppupvm(session, "2023-01-30", "Kauko")

            # === Uusi Granström-kohde (alkupvm 2015-04-01, ei loppupvm) ===
            granstrom_new = session.execute(
                select(Kohde.id).where(
                    and_(Kohde.nimi == "Granström", Kohde.loppupvm == None)
                )
            ).scalars().all()
            assert len(granstrom_new) == 1, "Uutta Granström-kohdetta ei löydy"
            granstrom_id = granstrom_new[0]

            # Uudella Granström-kohteella osapuolina Granström (omistaja) ja Kemp (vanhin asukas + kompostointi)
            granstrom_osapuolet = session.execute(
                select(Osapuolenrooli.selite, Osapuoli.nimi).
                select_from(KohteenOsapuolet).
                join(Osapuolenrooli, KohteenOsapuolet.osapuolenrooli_id == Osapuolenrooli.id).
                join(Osapuoli, KohteenOsapuolet.osapuoli_id == Osapuoli.id).
                where(KohteenOsapuolet.kohde_id == granstrom_id)
            ).all()
            granstrom_roolit = [r[0] for r in granstrom_osapuolet]
            granstrom_nimet = [r[1] for r in granstrom_osapuolet]
            assert "Omistaja" in granstrom_roolit, "Granström-kohteella ei omistajaa"
            assert any("Granström" in n for n in granstrom_nimet), "Granström-omistajaa ei löydy"
            assert "Vanhin asukas" in granstrom_roolit, "Granström-kohteella ei vanhinta asukasta"
            assert any("Kemp" in n for n in granstrom_nimet), "Kemp-asukasta ei löydy"

            # === Uusi Pohjonen-kohde (alkupvm 2023-01-23, ei loppupvm) ===
            _assert_kohteen_alkupvm(session, "2023-01-23", "Pohjonen")

            # === Riipinen pysyy aktiivisena (ei pääty, ei uutta kohdetta) ===
            riipinen_all = session.query(Kohde.id, Kohde.loppupvm).filter(
                Kohde.nimi == "Riipinen"
            ).all()
            assert len(riipinen_all) == 1, \
                f"Riipinen-kohteita odotettiin 1, löytyi {len(riipinen_all)}"
            assert riipinen_all[0][1] is None, "Riipinen-kohteen loppupvm ei saa olla asetettu"

            # === Sopimukset siirtyneet uudelle Granström-kohteelle ===
            granstrom_sopimukset = session.query(func.count(Sopimus.id)).filter(
                Sopimus.kohde_id == granstrom_id
            ).scalar()
            assert granstrom_sopimukset == 5, \
                f"Granström-kohteella sopimuksia: {granstrom_sopimukset}, odotettiin 5"

            # Granström-kohteella kuljetuksia
            granstrom_kuljetukset = session.query(func.count(Kuljetus.id)).filter(
                Kuljetus.kohde_id == granstrom_id
            ).scalar()
            assert granstrom_kuljetukset == 5, \
                f"Granström-kohteella kuljetuksia: {granstrom_kuljetukset}, odotettiin 5"

            # === Sopimukset yhteensä ===
            assert session.query(func.count(Sopimus.id)).scalar() == 5

            # === Kuljetukset yhteensä ===
            assert session.query(func.count(Kuljetus.id)).scalar() == 5

            # === Tyhjennysvälit yhteensä ===
            assert session.query(func.count(Tyhjennysvali.id)).scalar() == 5

            # === Viranomaispaatokset ===
            assert session.query(func.count(Viranomaispaatokset.id)).scalar() == 2

            # === Kompostorit ===
            assert session.query(func.count(Kompostori.id)).scalar() == 3

            # Forsström-kohteella on kompostori
            forstrom_id = session.query(Kohde.id).filter(
                Kohde.nimi == "Forsström"
            ).scalar()
            assert forstrom_id is not None, "Forsström-kohdetta ei löydy"
            forstrom_komp_count = session.query(func.count(KompostorinKohteet.kohde_id)).filter(
                KompostorinKohteet.kohde_id == forstrom_id
            ).scalar()
            assert forstrom_komp_count == 1, \
                f"Forsström-kohteella kompostoreita: {forstrom_komp_count}, odotettiin 1"

            # Uudella Granström-kohteella on kompostoreita
            granstrom_komp_count = session.query(func.count(KompostorinKohteet.kohde_id)).filter(
                KompostorinKohteet.kohde_id == granstrom_id
            ).scalar()
            assert granstrom_komp_count >= 1, \
                f"Granström-kohteella kompostoreita: {granstrom_komp_count}, odotettiin >= 1"

            # === Kohdentumattomat kuljetukset CSV ===
            for kuljdir in ["kuljetus1", "kuljetus2"]:
                csv_path = os.path.join(
                    str(datadir), kuljdir, "kohdentumattomat_kuljetukset.csv"
                )
                assert os.path.isfile(csv_path), \
                    f"Kohdentumattomat CSV ei löydy: {csv_path}"

    finally:
        _cleanup_all(engine)
