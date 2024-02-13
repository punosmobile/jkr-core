from datetime import date

import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session

from jkrimporter import conf
from jkrimporter.cli.jkr import import_ilmoitukset
from jkrimporter.providers.db.database import json_dumps
from jkrimporter.model import KompostiIlmoitus
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


def test_readable(datadir):
    assert Ilmoitustiedosto.readable_by_me(datadir + "/ilmoitukset.xlsx")


def test_import_ilmoitukset(engine, datadir):
    import_ilmoitukset(datadir + "/ilmoitukset.xlsx")

    session = Session(engine)
    # add test data later
    assert session.query(func.count(KompostiIlmoitus.id)).scalar() == 0
