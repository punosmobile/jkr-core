import csv
import os
import pytest

from sqlalchemy import create_engine, func, or_, select, text
from sqlalchemy.orm import Session

from jkrimporter import conf
from jkrimporter.cli.jkr import import_data, tiedontuottaja_add_new
from jkrimporter.providers.db.database import json_dumps
from jkrimporter.providers.db.models import (
    Jatetyyppi,
    Kohde,
    KohteenOsapuolet,
    Osapuolenrooli,
    Sopimus,
    SopimusTyyppi,
    Tiedontuottaja,
    Kuljetus,
    Tyhjennysvali,
)
from jkrimporter.providers.lahti.siirtotiedosto import LahtiSiirtotiedosto


@pytest.fixture(scope="module", autouse=True)
def engine():
    engine = create_engine(
        "postgresql://{username}:{password}@{host}:{port}/{dbname}".format(**conf.dbconf),
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

    # Kohteita ei pidä muodostua lisää (edelleen kuusi)
    lkm_kohteet = 6
    assert session.query(func.count(Kohde.id)).scalar() == lkm_kohteet

    # Kohteiden loppupäivämäärät eivät muutu kuljetuksissa
    loppu_pvms = [func.to_date('2023-01-30', 'YYYY-MM-DD'), func.to_date('2100-01-01', 'YYYY-MM-DD')]
    loppu_pvm_filter = or_(Kohde.loppupvm.in_(loppu_pvms), Kohde.loppupvm.is_(None))
    assert session.query(func.count(Kohde.id)).filter(loppu_pvm_filter).scalar() == lkm_kohteet

    # Kuljetusdatassa kahdeksan kelvollista sopimusta, joista kaksi on kahden kimppaa
    assert session.query(func.count(Sopimus.id)).scalar() == 10

    # Sopimuksissa kaksi validia sekajätesopimusta (joista toinen kimppa) ja muita yksi kutakin
    sekajate_id = select([Jatetyyppi.id]).where(Jatetyyppi.selite == 'Sekajäte').scalar_subquery()
    seka_sopimus_filter = Sopimus.jatetyyppi_id == sekajate_id
    assert session.query(func.count(Sopimus.id)).filter(seka_sopimus_filter).scalar() == 3
    biojate_id = select([Jatetyyppi.id]).where(Jatetyyppi.selite == 'Biojäte').scalar_subquery()
    bio_sopimus_filter = Sopimus.jatetyyppi_id == biojate_id
    assert session.query(func.count(Sopimus.id)).filter(bio_sopimus_filter).scalar() == 3
    lasi_id = select([Jatetyyppi.id]).where(Jatetyyppi.selite == 'Lasi').scalar_subquery()
    lasi_sopimus_filter = Sopimus.jatetyyppi_id == lasi_id
    assert session.query(func.count(Sopimus.id)).filter(lasi_sopimus_filter).scalar() == 1
    kartonki_id = select([Jatetyyppi.id]).where(Jatetyyppi.selite == 'Kartonki').scalar_subquery()
    kartonki_sopimus_filter = Sopimus.jatetyyppi_id == kartonki_id
    assert session.query(func.count(Sopimus.id)).filter(kartonki_sopimus_filter).scalar() == 1
    metalli_id = select([Jatetyyppi.id]).where(Jatetyyppi.selite == 'Metalli').scalar_subquery()
    metalli_sopimus_filter = Sopimus.jatetyyppi_id == metalli_id
    assert session.query(func.count(Sopimus.id)).filter(metalli_sopimus_filter).scalar() == 1
    muovi_id = select([Jatetyyppi.id]).where(Jatetyyppi.selite == 'Muovi').scalar_subquery()
    muovi_sopimus_filter = Sopimus.jatetyyppi_id == muovi_id
    assert session.query(func.count(Sopimus.id)).filter(muovi_sopimus_filter).scalar() == 1

    # Kohteella Asunto Oy Kahden Laulumuisto osapuolina tilaajaroolit eri jätelajeista
    kohde_nimi_filter = Kohde.nimi == 'Asunto Oy Kahden Laulumuisto'
    kohde_id = session.query(Kohde.id).filter(kohde_nimi_filter).scalar()
    osapuolen_roolit_query = \
        select([KohteenOsapuolet.osapuolenrooli_id]).where(KohteenOsapuolet.kohde_id == kohde_id)
    osapuolen_roolit = [row[0] for row in session.execute(osapuolen_roolit_query).fetchall()]
    sekajate_tilaaja_id = \
        session.query(Osapuolenrooli.id).filter(Osapuolenrooli.selite == 'Tilaaja sekajäte').scalar()
    assert sekajate_tilaaja_id in osapuolen_roolit
    biojate_tilaaja_id = \
        session.query(Osapuolenrooli.id).filter(Osapuolenrooli.selite == 'Tilaaja biojäte').scalar()
    assert biojate_tilaaja_id in osapuolen_roolit
    muovi_tilaaja_id = \
        session.query(Osapuolenrooli.id).filter(Osapuolenrooli.selite == 'Tilaaja muovipakkaus').scalar()
    assert muovi_tilaaja_id in osapuolen_roolit
    kartonki_tilaaja_id = \
        session.query(Osapuolenrooli.id).filter(Osapuolenrooli.selite == 'Tilaaja kartonkipakkaus').scalar()
    assert kartonki_tilaaja_id in osapuolen_roolit
    lasi_tilaaja_id = \
        session.query(Osapuolenrooli.id).filter(Osapuolenrooli.selite == 'Tilaaja lasipakkaus').scalar()
    assert lasi_tilaaja_id in osapuolen_roolit
    metalli_tilaaja_id = \
        session.query(Osapuolenrooli.id).filter(Osapuolenrooli.selite == 'Tilaaja metalli').scalar()
    assert metalli_tilaaja_id in osapuolen_roolit

    # Kohde Forsström on sekajätekimpan osakas
    kohde_nimi_filter = Kohde.nimi == 'Forsström'
    kohde_id = session.query(Kohde.id).filter(kohde_nimi_filter).scalar()
    kimppa_sopimus = \
        session.query(Sopimus.kimppaisanta_kohde_id, Sopimus.sopimustyyppi_id).\
        filter(Sopimus.kohde_id == kohde_id).filter(Sopimus.jatetyyppi_id == sekajate_id)
    assert kimppa_sopimus[0][0] is not None  # sopimuksella on kimppaisäntä
    assert kimppa_sopimus[0][1] == \
        session.query(SopimusTyyppi.id).filter(SopimusTyyppi.selite == 'Kimppasopimus').scalar()
    osapuolen_roolit_query = \
        select([KohteenOsapuolet.osapuolenrooli_id]).where(KohteenOsapuolet.kohde_id == kohde_id)
    osapuolen_roolit = [row[0] for row in session.execute(osapuolen_roolit_query).fetchall()]
    sekajate_kimppaosakas_id = \
        session.query(Osapuolenrooli.id).filter(Osapuolenrooli.selite == 'Kimppaosakas sekajäte').scalar()
    assert sekajate_kimppaosakas_id in osapuolen_roolit

    # Kohde Forsström on myös biojätekimpan osakas
    kohde_nimi_filter = Kohde.nimi == 'Forsström'
    kohde_id = session.query(Kohde.id).filter(kohde_nimi_filter).scalar()
    kimppa_sopimus = \
        session.query(Sopimus.kimppaisanta_kohde_id, Sopimus.sopimustyyppi_id).\
        filter(Sopimus.kohde_id == kohde_id).filter(Sopimus.jatetyyppi_id == biojate_id)
    assert kimppa_sopimus[0][0] is not None  # sopimuksella on kimppaisäntä
    assert kimppa_sopimus[0][1] == \
        session.query(SopimusTyyppi.id).filter(SopimusTyyppi.selite == 'Kimppasopimus').scalar()
    osapuolen_roolit_query = \
        select([KohteenOsapuolet.osapuolenrooli_id]).where(KohteenOsapuolet.kohde_id == kohde_id)
    osapuolen_roolit = [row[0] for row in session.execute(osapuolen_roolit_query).fetchall()]
    biojate_kimppaosakas_id = \
        session.query(Osapuolenrooli.id).filter(Osapuolenrooli.selite == 'Kimppaosakas biojäte').scalar()
    assert biojate_kimppaosakas_id in osapuolen_roolit

    # Kohde Lindroth on sekajätekimpan isäntä
    kohde_nimi_filter = Kohde.nimi == 'Lindroth'
    kohde_id = session.query(Kohde.id).filter(kohde_nimi_filter).scalar()
    kimppa_sopimus = \
        session.query(Sopimus.kimppaisanta_kohde_id, Sopimus.sopimustyyppi_id).\
        filter(Sopimus.kohde_id == kohde_id).filter(Sopimus.jatetyyppi_id == sekajate_id)
    assert kimppa_sopimus[0][0] is None  # sopimuksella ei ole kimppaisäntää
    assert kimppa_sopimus[0][1] == \
        session.query(SopimusTyyppi.id).filter(SopimusTyyppi.selite == 'Kimppasopimus').scalar()
    osapuolen_roolit_query = \
        select([KohteenOsapuolet.osapuolenrooli_id]).where(KohteenOsapuolet.kohde_id == kohde_id)
    osapuolen_roolit = [row[0] for row in session.execute(osapuolen_roolit_query).fetchall()]
    sekajate_kimppaisanta_id = \
        session.query(Osapuolenrooli.id).filter(Osapuolenrooli.selite == 'Kimppaisäntä sekajäte').scalar()
    assert sekajate_kimppaisanta_id in osapuolen_roolit

    # Kohde Lindroth on myös biojätekimpan isäntä
    kohde_nimi_filter = Kohde.nimi == 'Lindroth'
    kohde_id = session.query(Kohde.id).filter(kohde_nimi_filter).scalar()
    kimppa_sopimus = \
        session.query(Sopimus.kimppaisanta_kohde_id, Sopimus.sopimustyyppi_id).\
        filter(Sopimus.kohde_id == kohde_id).filter(Sopimus.jatetyyppi_id == biojate_id)
    assert kimppa_sopimus[0][0] is None  # sopimuksella ei ole kimppaisäntää
    assert kimppa_sopimus[0][1] == \
        session.query(SopimusTyyppi.id).filter(SopimusTyyppi.selite == 'Kimppasopimus').scalar()
    osapuolen_roolit_query = \
        select([KohteenOsapuolet.osapuolenrooli_id]).where(KohteenOsapuolet.kohde_id == kohde_id)
    osapuolen_roolit = [row[0] for row in session.execute(osapuolen_roolit_query).fetchall()]
    biojate_kimppaisanta_id = \
        session.query(Osapuolenrooli.id).filter(Osapuolenrooli.selite == 'Kimppaisäntä biojäte').scalar()
    assert biojate_kimppaisanta_id in osapuolen_roolit

    # Kiinteänjätteen massa kenttä on tyhjä.
    assert session.query(func.count(Kuljetus.id)).filter(text("massa is NULL")).scalar() == 10

    # Tyhjennysvalejä on seitsemän, yhdellä sopimuksista on kaksi tyhjennysväliä.
    assert session.query(func.count(Tyhjennysvali.id)).scalar() == 7
    sopimus_id_5_count = session.query(func.count()).filter(Tyhjennysvali.sopimus_id == 5).scalar()
    assert sopimus_id_5_count == 2

    # Kohdentumattomat.csv sisältää viisi kohdentumatonta Asiakas-riviä.
    csv_file_path = os.path.join(datadir, "kohdentumattomat.csv")
    assert os.path.isfile(csv_file_path), f"File not found: {csv_file_path}"
    with open(csv_file_path, 'r') as csvfile:
        csv_reader = csv.reader(csvfile)
        header = next(csv_reader, None)
        assert header is not None
        rows = list(csv_reader)
        assert len(rows) == 5
