import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from jkrimporter import conf
from jkrimporter.providers.db.database import json_dumps
from jkrimporter.providers.db.models import AKPPoistoSyy


@pytest.fixture(scope="module", autouse=True)
def engine():
    engine = create_engine(
        "postgresql://{username}:{password}@{host}:{port}/{dbname}".format(
            **conf.dbtestconf
        ),
        future=True,
        json_serializer=json_dumps,
    )
    return engine


def test_akppoistosyyt(engine):
    akppoistosyyt = [(1, "Pihapiiri"), (2, "Pitkä matka"), (11, "Ei käytössä")]
    session = Session(engine)
    result = session.execute(select([AKPPoistoSyy.id, AKPPoistoSyy.selite]))
    assert [tuple(row) for row in result] == akppoistosyyt
