import os
from datetime import datetime
from pathlib import Path
from shutil import copytree

import pytest
from sqlalchemy import and_, create_engine, distinct, func, or_, select, text
from sqlalchemy.orm import Session

from jkrimporter import conf
from jkrimporter.providers.db.codes import init_code_objects
from jkrimporter.providers.db.database import json_dumps
from jkrimporter.providers.db.dbprovider import import_dvv_kohteet
from jkrimporter.providers.db.models import (
    Kohde,
    KohteenOsapuolet,
    Osapuolenrooli,
    Osapuoli,
    RakennuksenOmistajat,
    RakennuksenVanhimmat,
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


def _cleanup_dvv_kohteet(engine):
    """Poistaa import_dvv_kohteet:n luomat tiedot kannasta.

    Järjestys on tärkeä foreign key -rajoitteiden takia.
    Poistetaan myös mahdollisten muiden testien jättämä data
    (kompostorit, sopimukset, kuljetukset jne.) jotta testi
    alkaa aina puhtaasta tilasta.
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
        conn.execute(text(
            "DELETE FROM jkr.osapuoli "
            "WHERE tiedontuottaja_tunnus NOT IN ('dvv', 'ilmoitus')"
        ))
        conn.execute(text(
            "DELETE FROM jkr_koodistot.tiedontuottaja "
            "WHERE tunnus NOT IN ('dvv', 'ilmoitus')"
        ))
        conn.commit()


def test_import_dvv_kohteet(engine, datadir):
    """Testaa DVV-kohteiden luonti perusmaksurekisterillä.

    Testikannassa on valmiiksi DVV-rakennus-, osoite-, omistaja- ja asukastiedot
    (init_database). import_dvv_kohteet luo/päivittää kohteet näiden perusteella.

    Testin lopussa siivotaan kaikki import_dvv_kohteet:n luomat tietueet,
    jotta kanta pysyy puhtaana muille testeille.
    """
    _cleanup_dvv_kohteet(engine)
    try:
        with Session(engine) as session:
            init_code_objects(session)
            import_dvv_kohteet(
                session,
                poimintapvm=datetime.strptime("28.1.2022", "%d.%m.%Y").date(),
                perusmaksutiedosto=datadir / "perusmaksurekisteri.xlsx",
            )

            # Kohteiden lukumäärä
            lkm_kohteet = 9
            assert session.query(func.count(Kohde.id)).scalar() == lkm_kohteet

            # Yhdelläkään kohteella ei ole loppupäivämäärää
            paattyneet = session.query(func.count(Kohde.id)).filter(
                Kohde.loppupvm != None
            ).scalar()
            assert paattyneet == 0, f"Päättyneitä kohteita: {paattyneet}, odotettiin 0"

            # Kaikilla kohteilla vähintään yksi omistaja
            kohteet_ids = [row[0] for row in session.execute(select(Kohde.id))]
            omistaja_rooli_id = 1
            kohteet_having_omistaja = [
                row[0] for row in session.execute(
                    select(distinct(KohteenOsapuolet.kohde_id)).where(
                        KohteenOsapuolet.osapuolenrooli_id == omistaja_rooli_id
                    )
                )
            ]
            assert sorted(kohteet_ids) == sorted(kohteet_having_omistaja), \
                "Kaikilla kohteilla ei ole omistajaa"

            # Kohteilla Forsström ja Lindroth on vanhin asukas -osapuoli
            vanhin_asukas_rooli_id = 2
            for nimi in ["Forsström", "Lindroth"]:
                kohde_ids = session.execute(
                    select(Kohde.id).where(Kohde.nimi == nimi)
                ).scalars().all()
                assert len(kohde_ids) > 0, f"Kohdetta {nimi!r} ei löydy"
                va_count = session.execute(
                    select(func.count()).select_from(KohteenOsapuolet).where(
                        and_(
                            KohteenOsapuolet.osapuolenrooli_id == vanhin_asukas_rooli_id,
                            KohteenOsapuolet.kohde_id.in_(kohde_ids),
                        )
                    )
                ).scalar()
                assert va_count >= 1, f"Kohteella {nimi!r} ei ole vanhinta asukasta"

            # Vanhin asukas -osapuolien kokonaismäärä
            vanhin_asukas_count = (
                session.query(func.count(KohteenOsapuolet.kohde_id))
                .filter(KohteenOsapuolet.osapuolenrooli_id == vanhin_asukas_rooli_id)
                .scalar()
            )
            assert vanhin_asukas_count == 7, \
                f"Vanhin asukas -osapuolien määrä: {vanhin_asukas_count}, odotettiin 7"

    finally:
        _cleanup_dvv_kohteet(engine)
