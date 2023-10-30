import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session

from jkrimporter import conf
from jkrimporter.cli.jkr import import_data, tiedontuottaja_add_new
from jkrimporter.providers.db.database import json_dumps
from jkrimporter.providers.db.models import Sopimus, Tiedontuottaja
from jkrimporter.providers.lahti.siirtotiedosto import LahtiSiirtotiedosto


@pytest.fixture(scope="module", autouse=True)
def engine():
    engine = create_engine(
        "postgresql://{username}:{password}@{host}:{port}/{dbname}".format(**conf.dbconf),
        future=True,
        json_serializer=json_dumps
    )
    return engine


def test_tiedontuottaja_add_new(engine):
    tiedontuottaja_add_new('LSJ', 'Testituottaja')
    session = Session(engine)
    testituottaja_filter = Tiedontuottaja.nimi.like('Testituottaja')
    assert session.query(Tiedontuottaja.tunnus).filter(testituottaja_filter).scalar() == 'LSJ'


def test_readable(datadir):
    assert LahtiSiirtotiedosto.readable_by_me(datadir)


def test_kohteet(datadir):
    asiakastiedot = LahtiSiirtotiedosto(datadir).asiakastiedot
    assert 'UrakoitsijaId' in asiakastiedot.headers


def test_import_data(engine, datadir):
    import_data(datadir, 'LSJ', False, False, '1.1.2023', '31.3.2023')

    session = Session(engine)

    # Kuljetusdatassa kaksi sopimusta
    assert session.query(func.count(Sopimus.id)).scalar() == 2
