import csv
import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, or_
from sqlalchemy.orm import Session

from jkrimporter import conf
from jkrimporter.cli.jkr import import_data, tiedontuottaja_add_new
from jkrimporter.providers.db.database import json_dumps
from jkrimporter.providers.db.models import (
    Jatetyyppi,
    Keskeytys,
    Kohde,
    KohteenOsapuolet,
    Kuljetus,
    Osapuolenrooli,
    Sopimus,
    SopimusTyyppi,
    Tiedontuottaja,
    Tyhjennysvali,
)
from jkrimporter.providers.lahti.siirtotiedosto import LahtiSiirtotiedosto


@pytest.fixture(scope="module", autouse=True)
def engine():
    engine = create_engine(
        "postgresql://{username}:{password}@{host}:{port}/{dbname}".format(
            **conf.dbconf
        ),
        future=True,
        json_serializer=json_dumps
    )
    return engine


def test_tiedontuottaja_add_new(engine):
    tiedontuottaja_add_new('LSJ', 'Testituottaja')
    session = Session(engine)
    testituottaja_filter = Tiedontuottaja.nimi.like('Testituottaja')
    assert session.query(Tiedontuottaja.tunnus).filter(testituottaja_filter).scalar() == 'LSJ'


def test_readable(datadir):
    assert LahtiSiirtotiedosto.readable_by_me(datadir)


def test_kohteet(datadir):
    asiakastiedot = LahtiSiirtotiedosto(datadir).asiakastiedot
    header_row = asiakastiedot[0]
    headers = header_row.dict().keys()
    assert 'UrakoitsijaId' in headers


def test_import_faulty_data(faulty_datadir):
    with pytest.raises(RuntimeError):
        import_data(faulty_datadir, 'LSJ', False, False, True, '1.1.2023', '31.3.2023')


def test_import_data(engine, datadir):
    import_data(datadir, 'LSJ', False, False, True, '1.1.2023', '31.3.2023')

    session = Session(engine)

    # Kohteita ei pidä muodostua lisää
    lkm_kohteet = 15
    assert session.query(func.count(Kohde.id)).scalar() == lkm_kohteet

    # Kohteiden loppupäivämäärät eivät muutu kuljetuksissa
    loppu_pvms = [
        func.to_date("2022-06-16", "YYYY-MM-DD"),
        func.to_date("2023-01-22", "YYYY-MM-DD"),
        func.to_date("2023-01-30", "YYYY-MM-DD"),
        func.to_date("2100-01-01", "YYYY-MM-DD"),
        func.to_date("2023-01-31", "YYYY-MM-DD"),
    ]
    loppu_pvm_filter = or_(Kohde.loppupvm.in_(loppu_pvms), Kohde.loppupvm.is_(None))
    assert session.query(func.count(Kohde.id)).filter(loppu_pvm_filter).scalar() == lkm_kohteet
