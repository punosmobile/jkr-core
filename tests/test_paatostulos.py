import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from jkrimporter import conf
from jkrimporter.providers.db.database import json_dumps
from jkrimporter.providers.db.models import Paatostulos


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


def test_paatostulos(engine):
    paatostulokset = [("0", "kielteinen"), ("1", "myönteinen")]
    session = Session(engine)
    result = session.execute(select([Paatostulos.koodi, Paatostulos.selite]))
    assert [tuple(row) for row in result] == paatostulokset
