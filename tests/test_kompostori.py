import pytest
import os
from sqlalchemy import create_engine, func
from sqlalchemy.orm import Session

from jkrimporter import conf
from openpyxl.reader.excel import load_workbook
from jkrimporter.cli.jkr import import_ilmoitukset
from jkrimporter.providers.db.database import json_dumps
from jkrimporter.providers.db.models import Kompostori, KompostorinKohteet
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


def test_kompostori(engine, datadir):
    import_ilmoitukset(datadir + "/ilmoitukset.xlsx")
    session = Session(engine)
    # Ilmoitus.xlsx sisältää 5 riviä, joista kompostoreita syntyy 2.
    # Yksi rivi ei kohdennu, yksi on hylätty, ja yksi on kahden kimppa.
    assert session.query(func.count(Kompostori.id)).scalar() == 2

    # KompostorinKohteet taulussa kolme kohdentunutta kohdetta.
    # Kahden kimppa sekä yksittäinen.
    assert session.query(func.count(KompostorinKohteet.kompostori_id)).scalar() == 3

    # Kohdentumattomat.xlsx sisältää neljä kohdentumatonta ilmoitusriviä.
    xlsx_file_path = os.path.join(datadir, "kohdentumattomat.xlsx")
    workbook = load_workbook(xlsx_file_path)
    sheet = workbook[workbook.sheetnames[0]]
    assert sheet.max_row == 5


def test_kompostori_osakkaan_lisays(engine, datadir):
    import_ilmoitukset(datadir + "/ilmoitukset_lisaa_komposti_osakas.xlsx")
    session = Session(engine)
    # Tuodaan kaksi rivi lisää, toinen liitetään jo löytyvään kompostoriin osakkaaksi
    # toinen luo uuden kompostorin uudella päivämäärällä.
    assert session.query(func.count(Kompostori.id)).scalar() == 3

    # KompostorinKohteet taulussa viisi kohdentunutta kohdetta.
    # Kolmen kimppa sekä kaksi yksittäistä, joilla sama kohde_id.
    assert session.query(func.count(KompostorinKohteet.kompostori_id)).scalar() == 5
