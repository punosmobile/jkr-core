from datetime import date

import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session

from jkrimporter import conf
from jkrimporter.cli.jkr import import_ilmoitukset
from jkrimporter.providers.db.database import json_dumps
from jkrimporter.providers.db.models import Ilmoitus
from jkrimporter.providers.lahti.ilmoitustiedosto import Ilmoitustiedosto


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

def test_ilmoitukset(engine):
def test_readable(datadir):
    assert Ilmoitustiedosto.readable_by_me(datadir + "/ilmoitukset.xlsx")


def test_import_ilmoitukset(engine, datadir):
    import_ilmoitukset(datadir + "/ilmoitukset.xlsx")

    session = Session(engine)
    # add test data later
    assert session.query(func.count(Ilmoitus.id)).scalar() == 0

    # assert session.query(func.count(Viranomaispaatokset.id)).scalar() == 4

    # paatosnumerot = ["123/2022", "122/2022", "121/2022", "120/2022"]
    # result = session.query(Viranomaispaatokset.paatosnumero)
    # assert [row[0] for row in result] == paatosnumerot

    # Päätös "123/2022"
    # - voimassa 1.1.2020 alkaen 15.6.2022 asti
    # paatos_nimi_filter = Viranomaispaatokset.paatosnumero == "123/2022"
    # paatos_123 = (
        # session.query(Viranomaispaatokset.alkupvm, Viranomaispaatokset.loppupvm)
        # .filter(paatos_nimi_filter)
        # .first()
    # )
    # assert paatos_123[0] == date(2020, 1, 1)
    # assert paatos_123[1] == date(2022, 6, 15)

    # Päätös "120/2022"
    # - vastaanottaja Mikkolainen Matti
    # paatos_nimi_filter = Viranomaispaatokset.paatosnumero == "120/2022"
    # paatos_120 = (
        # session.query(Viranomaispaatokset.vastaanottaja)
        # .filter(paatos_nimi_filter)
        # .first()
    # )
    # assert paatos_120[0] == "Mikkolainen Matti"