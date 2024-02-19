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
    Rakennus,
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


def test_import_faulty_data(faulty_datadir):
    with pytest.raises(RuntimeError):
        import_paatokset(faulty_datadir + "/paatokset.xlsx")


def _assert_tapahtumalaji(session, koodi, selite):
    assert (
        koodi
        == session.query(Tapahtumalaji.koodi)
        .filter(Tapahtumalaji.selite == selite)
        .first()[0]
    )


def _assert_jatetyyppi(session, id, selite):
    assert (
        id
        == session.query(Jatetyyppi.id)
        .filter(Jatetyyppi.selite == selite)
        .first()[0]
    )


def _assert_akppoistosyy(session, id, selite):
    assert (
        id
        == session.query(AKPPoistoSyy.id)
        .filter(AKPPoistoSyy.selite == selite)
        .first()[0]
    )


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

    rakennus_123456789A_id = (
        session.query(Rakennus.id).filter(Rakennus.prt == "123456789A").first()[0]
    )
    rakennus_134567890B_id = (
        session.query(Rakennus.id).filter(Rakennus.prt == "134567890B").first()[0]
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
            Viranomaispaatokset.rakennus_id,
        )
        .filter(paatos_nimi_filter)
        .first()
    )
    assert paatos_123[0] == date(2020, 1, 1)
    assert paatos_123[1] == date(2022, 6, 15)
    assert paatos_123[2] is None
    assert paatos_123[3] == paatos_myonteinen
    _assert_tapahtumalaji(session, paatos_123[4], "AKP")
    _assert_akppoistosyy(session, paatos_123[5], "Pitkä matka")
    assert paatos_123[6] is None
    assert paatos_123[7] == rakennus_123456789A_id

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
            Viranomaispaatokset.rakennus_id,
        )
        .filter(paatos_nimi_filter)
        .first()
    )
    assert paatos_122[0] == 26
    _assert_tapahtumalaji(session, paatos_122[1], "Tyhjennysväli")
    assert paatos_122[2] is None
    _assert_jatetyyppi(session, paatos_122[3], "Sekajäte")
    assert paatos_122[4] == rakennus_123456789A_id

    # Päätös "121/2022"
    # - tapahtumalaji erilliskeräyksestä poikkeaminen
    # - jätelaji lasi
    paatos_nimi_filter = Viranomaispaatokset.paatosnumero == "121/2022"
    paatos_121 = (
        session.query(
            Viranomaispaatokset.tapahtumalaji_koodi,
            Viranomaispaatokset.jatetyyppi_id,
            Viranomaispaatokset.rakennus_id,
        )
        .filter(paatos_nimi_filter)
        .first()
    )
    _assert_tapahtumalaji(session, paatos_121[0], "Erilliskeräyksestä poikkeaminen")
    assert (
        paatos_121[1]
        == session.query(Jatetyyppi.id).filter((Jatetyyppi.selite == "Lasi")).first()[0]
    )
    assert paatos_121[2] == rakennus_134567890B_id

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
            Viranomaispaatokset.rakennus_id,
        )
        .filter(paatos_nimi_filter)
        .first()
    )
    assert paatos_120[0] == "Mikkolainen Matti"
    assert paatos_120[1] == paatos_kielteinen
    _assert_tapahtumalaji(session, paatos_120[2], "Keskeyttäminen")
    assert paatos_120[3] == rakennus_134567890B_id
