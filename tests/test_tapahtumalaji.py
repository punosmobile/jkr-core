import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from jkrimporter import conf
from jkrimporter.providers.db.database import json_dumps
from jkrimporter.providers.db.models import Tapahtumalaji


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


def test_tapahtumalajit(engine):
    tapahtumalajit = [
        ("1", "Perusmaksu"),
        ("2", "AKP"),
        ("3", "Tyhjennysväli"),
        ("4", "Keskeyttäminen"),
        ("5", "Erilliskeräyksestä poikkeaminen"),
        ("100", "Muu poikkeaminen"),
    ]
    session = Session(engine)
    result = session.execute(select([Tapahtumalaji.koodi, Tapahtumalaji.selite]))
    assert [tuple(row) for row in result] == tapahtumalajit
