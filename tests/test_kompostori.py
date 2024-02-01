import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session

from jkrimporter import conf
from jkrimporter.providers.db.database import json_dumps
from jkrimporter.providers.db.models import Kompostori, KompostorinKohteet


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


def test_kompostori(engine):
    session = Session(engine)
    # add test data later
    assert session.query(func.count(Kompostori.id)).scalar() == 0


def test_kompostorin_kohteet(engine):
    session = Session(engine)
    # add test data later
    assert session.query(func.count(KompostorinKohteet.kompostori_id)).scalar() == 0
