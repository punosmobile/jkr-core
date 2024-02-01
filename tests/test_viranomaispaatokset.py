import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session

from jkrimporter import conf
from jkrimporter.providers.db.database import json_dumps
from jkrimporter.providers.db.models import Viranomaispaatokset
from jkrimporter.providers.lahti.paatostiedosto import Paatostiedosto


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


def test_readable(datadir):
    assert Paatostiedosto.readable_by_me(datadir + "/paatokset.xlsx")


def test_import_paatokset(engine):
    session = Session(engine)

    assert session.query(func.count(Viranomaispaatokset.id)).scalar() == 4
