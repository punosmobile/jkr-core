from datetime import datetime
import subprocess

import pytest
from sqlalchemy import and_, create_engine, distinct, func, or_, select
from sqlalchemy.orm import Session

from jkrimporter import conf
from jkrimporter.providers.db.codes import init_code_objects
from jkrimporter.providers.db.database import json_dumps
from jkrimporter.providers.db.dbprovider import import_dvv_kohteet
from jkrimporter.providers.db.models import Kohde, KohteenOsapuolet, Osapuoli, Osapuolenrooli


@pytest.fixture(scope="module", autouse=True)
def engine():
    engine = create_engine(
        "postgresql://{username}:{password}@{host}:{port}/{dbname}".format(**conf.dbconf),
        future=True,
        json_serializer=json_dumps
    )
    return engine


def test_osapuolenrooli(engine):
    osapuolenroolit = [(1, 'Omistaja'),
                       (2, 'Vanhin asukas')]
    session = Session(engine)
    result = session.execute(select([Osapuolenrooli.id, Osapuolenrooli.selite]))
    assert [tuple(row) for row in result] == osapuolenroolit


def test_import_dvv_kohteet(engine, datadir):
    try:
        with Session(engine) as session:
            init_code_objects(session)
            import_dvv_kohteet(session,
                               datetime.strptime("1.1.2022", "%d.%m.%Y").date(),
                               datetime.strptime("31.12.2022", "%d.%m.%Y").date(),
                               datadir / "perusmaksurekisteri.xlsx")
    except Exception as e:
        print(f"Creating kohteet failed: {e}")

    # Kohteiden lkm
    assert session.query(func.count(Kohde.id)).scalar() == 3

    # Kaikilla kohteilla vähintään yksi omistaja
    kohteet = select(Kohde.id)
    kohteet_having_omistaja = \
        select([distinct(KohteenOsapuolet.kohde_id)]).where(KohteenOsapuolet.osapuolenrooli_id == 1)
    assert [row[0] for row in session.execute(kohteet)] == \
        [row[0] for row in session.execute(kohteet_having_omistaja)]

    # Kohteissa nimeltä Forsström ja Kemp vain yksi asuttu huoneisto, vanhin asukas osapuoleksi
    vanhin_asukas_filter = KohteenOsapuolet.osapuolenrooli_id == 2
    kohde_ids = \
        session.execute(select(Kohde.id).where(or_(Kohde.nimi == 'Forsström', Kohde.nimi == 'Kemp'))).fetchall()
    vanhin_asukas_id = \
        session.execute(select(KohteenOsapuolet.kohde_id).where(vanhin_asukas_filter)).fetchall()
    assert kohde_ids == vanhin_asukas_id

    # Muissa kohteissa ei vanhinta asukasta osapuolena
    assert session.query(func.count(KohteenOsapuolet.kohde_id)).filter(vanhin_asukas_filter).scalar() == 2


def test_update_dvv_kohteet(engine):
    # Updating the test database created before test fixtures
    update_test_db_command = ".\\scripts\\update_database.bat"
    try:
        subprocess.check_output(update_test_db_command, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print(f"Creating test database failed: {e.output}")

    try:
        with Session(engine) as session:
            init_code_objects(session)
            import_dvv_kohteet(session,
                               datetime.strptime("1.1.2023", "%d.%m.%Y").date(),
                               datetime.strptime("31.12.2023", "%d.%m.%Y").date(),
                               None)
    except Exception as e:
        print(f"Updating kohteet failed: {e}")

    # Kohteiden lkm
    assert session.query(func.count(Kohde.id)).scalar() == 5

    # Uudessa kohteessa Kyykoski osapuolina Granström (omistaja) ja Kyykoski (uusi asukas)
    kohde_filter = and_(Kohde.nimi == 'Kyykoski', Kohde.alkupvm == '2023-01-01')
    kohde_id = session.execute(select(Kohde.id).where(kohde_filter)).fetchone()[0]
    osapuoli_filter = or_(Osapuoli.nimi.like('Granström%'), Osapuoli.nimi.like('Kyykoski%'))
    osapuoli_ids = \
        session.query(Osapuoli.id).filter(osapuoli_filter).order_by(Osapuoli.id)
    kohteen_osapuolet_ids = \
        session.query(KohteenOsapuolet.osapuoli_id).filter(KohteenOsapuolet.kohde_id == kohde_id).order_by(KohteenOsapuolet.osapuoli_id)
    assert [r1.id for r1 in osapuoli_ids] == [r2.osapuoli_id for r2 in kohteen_osapuolet_ids]
