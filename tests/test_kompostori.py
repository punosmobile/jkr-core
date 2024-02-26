import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session

from jkrimporter import conf
from jkrimporter.cli.jkr import import_ilmoitukset
from jkrimporter.providers.db.database import json_dumps
from jkrimporter.providers.lahti.ilmoitustiedosto import Ilmoitustiedosto
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


def test_readable(datadir):
    assert Ilmoitustiedosto.readable_by_me(datadir + "/ilmoitukset.xlsx")


def test_kompostori(engine, datadir):
    import_ilmoitukset(datadir + "/ilmoitukset.xlsx")
    session = Session(engine)
    # Ilmoitus.xlsx sisältää 5 riviä, joista kompostoreita syntyy 2.
    # Yksi rivi ei kohdennu, yksi on hylätty, ja yksi on kahden kimppa.
    # Note! Kohdennus not implemented.
    assert session.query(func.count(Kompostori.id)).scalar() == 2


def test_kompostorin_kohteet(engine):
    session = Session(engine)
    # KompostorinKohteet taulussa kolme kohdentunutta kohdetta.
    # Kahden kimppa sekä yksittäinen.
    assert session.query(func.count(KompostorinKohteet.kompostori_id)).scalar() == 3


def test_kompostori_osakkaan_lisays(engine, datadir):
    import_ilmoitukset(datadir + "/ilmoitukset_lisaa_komposti_osakas.xlsx")
    session = Session(engine)
    # Tuodaan yksi rivi lisää, joka liitetään jo löytyvään kompostoriin osakkaaksi.
    assert session.query(func.count(Kompostori.id)).scalar() == 2


def test_kompostorin_kohteet_lisays(engine):
    session = Session(engine)
    # KompostorinKohteet taulussa neljä kohdentunutta kohdetta.
    # Kolmen kimppa sekä yksittäinen.
    assert session.query(func.count(KompostorinKohteet.kompostori_id)).scalar() == 4
