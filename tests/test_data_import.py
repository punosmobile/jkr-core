import subprocess

from datetime import datetime
from sqlalchemy import create_engine, distinct, func, select
from sqlalchemy.orm import Session

import pytest

from jkrimporter import conf
from jkrimporter.providers.db.codes import init_code_objects
from jkrimporter.providers.db.database import json_dumps
from jkrimporter.providers.db.dbprovider import import_dvv_kohteet
from jkrimporter.providers.db.models import Kohde, KohteenOsapuolet, Osapuolenrooli


@pytest.fixture(scope="module", autouse=True)
def init_database():
    # Create everything from scratch for each test run
    init_test_db_command = ".\\scripts\\init_database.bat"
    try:
        subprocess.check_output(init_test_db_command, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        print(f"Creating test database failed: {e.output}")


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

    # Kohteessa nimeltä Forsström vain yksi asuttu huoneisto, vanhin asukas osapuoleksi
    vanhin_asukas_filter = KohteenOsapuolet.osapuolenrooli_id == 2
    forsstrom_id = session.execute(select(Kohde.id).where(Kohde.nimi == 'Forsström')).fetchone()[0]
    vanhin_asukas_id = \
        session.execute(select(KohteenOsapuolet.kohde_id).where(vanhin_asukas_filter)).fetchone()[0]
    assert forsstrom_id == vanhin_asukas_id

    # Muissa kohteissa ei vanhinta asukasta osapuolena
    assert session.query(func.count(KohteenOsapuolet.kohde_id)).filter(vanhin_asukas_filter).scalar() == 1
