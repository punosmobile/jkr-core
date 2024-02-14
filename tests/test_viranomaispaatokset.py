from datetime import date

import pytest
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session

from jkrimporter import conf
from jkrimporter.cli.jkr import import_paatokset
from jkrimporter.providers.db.database import json_dumps
from jkrimporter.providers.db.models import (
    AKPPoistoSyy,
    Jatetyyppi,
    Paatostulos,
    Tapahtumalaji,
    Viranomaispaatokset,
)
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

    paatos_myonteinen = (
        session.query(Paatostulos.koodi)
        .filter((Paatostulos.selite == "myönteinen"))
        .first()[0]
    )
    paatos_kielteinen = (
        session.query(Paatostulos.koodi)
        .filter((Paatostulos.selite == "kielteinen"))
        .first()[0]
    )

    # Päätös "123/2022"
    # - voimassa 1.1.2020 alkaen 15.6.2022 asti
    # - myönteinen päätös
    # - tapahtumalaji AKP
    # - AKP:n poiston syy pitkä matka
    paatos_nimi_filter = Viranomaispaatokset.paatosnumero == "123/2022"
    paatos_123 = (
        session.query(
            Viranomaispaatokset.alkupvm,
            Viranomaispaatokset.loppupvm,
            Viranomaispaatokset.tyhjennysvali,
            Viranomaispaatokset.paatostulos_koodi,
            Viranomaispaatokset.tapahtumalaji_koodi,
            Viranomaispaatokset.akppoistosyy_id,
            Viranomaispaatokset.jatetyyppi_id,
        )
        .filter(paatos_nimi_filter)
        .first()
    )
    assert paatos_123[0] == date(2020, 1, 1)
    assert paatos_123[1] == date(2022, 6, 15)
    assert paatos_123[2] is None
    assert paatos_123[3] == paatos_myonteinen
    assert (
        paatos_123[4]
        == session.query(Tapahtumalaji.koodi)
        .filter((Tapahtumalaji.selite == "AKP"))
        .first()[0]
    )
    assert (
        paatos_123[5]
        == session.query(AKPPoistoSyy.id)
        .filter(AKPPoistoSyy.selite == "Pitkä matka")
        .first()[0]
    )
    assert paatos_123[6] is None

    # Päätos "122/2022"
    # - tyhjennysväli 26
    # - tapahtumalaji tyhjennysväli
    paatos_nimi_filter = Viranomaispaatokset.paatosnumero == "122/2022"
    paatos_122 = (
        session.query(
            Viranomaispaatokset.tyhjennysvali,
            Viranomaispaatokset.tapahtumalaji_koodi,
            Viranomaispaatokset.akppoistosyy_id,
            Viranomaispaatokset.jatetyyppi_id,
        )
        .filter(paatos_nimi_filter)
        .first()
    )
    assert paatos_122[0] == 26
    assert (
        paatos_122[1]
        == session.query(Tapahtumalaji.koodi)
        .filter((Tapahtumalaji.selite == "Tyhjennysväli"))
        .first()[0]
    )
    assert paatos_122[2] is None
    assert (
        paatos_122[3]
        == session.query(Jatetyyppi.id)
        .filter((Jatetyyppi.selite == "Sekajäte"))
        .first()[0]
    )

    # Päätös "121/2022"
    # - tapahtumalaji erilliskeräyksestä poikkeaminen
    # - jätelaji lasi
    paatos_nimi_filter = Viranomaispaatokset.paatosnumero == "121/2022"
    paatos_121 = (
        session.query(
            Viranomaispaatokset.tapahtumalaji_koodi,
            Viranomaispaatokset.jatetyyppi_id,
        )
        .filter(paatos_nimi_filter)
        .first()
    )
    assert (
        paatos_121[0]
        == session.query(Tapahtumalaji.koodi)
        .filter((Tapahtumalaji.selite == "Erilliskeräyksestä poikkeaminen"))
        .first()[0]
    )
    assert (
        paatos_121[1]
        == session.query(Jatetyyppi.id).filter((Jatetyyppi.selite == "Lasi")).first()[0]
    )

    # Päätös "120/2022"
    # - vastaanottaja Mikkolainen Matti
    # - päätöstulos kielteinen
    # - tapahtumalaji keskeyttäminen
    paatos_nimi_filter = Viranomaispaatokset.paatosnumero == "120/2022"
    paatos_120 = (
        session.query(
            Viranomaispaatokset.vastaanottaja,
            Viranomaispaatokset.paatostulos_koodi,
            Viranomaispaatokset.tapahtumalaji_koodi,
        )
        .filter(paatos_nimi_filter)
        .first()
    )
    assert paatos_120[0] == "Mikkolainen Matti"
    assert paatos_120[1] == paatos_kielteinen
    assert (
        paatos_120[2]
        == session.query(Tapahtumalaji.koodi)
        .filter((Tapahtumalaji.selite == "Keskeyttäminen"))
        .first()[0]
    )
