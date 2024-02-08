import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from jkrimporter import conf
from jkrimporter.cli.jkr import import_paatokset
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


def test_import_paatokset(engine, datadir):
    import_paatokset(datadir + "/paatokset.xlsx")

    session = Session(engine)

    assert session.query(func.count(Viranomaispaatokset.id)).scalar() == 4

    paatosnumerot = ["123/2022", "122/2022", "121/2022", "120/2022"]
    result = session.query(Viranomaispaatokset.paatosnumero)
    assert [row[0] for row in result] == paatosnumerot
