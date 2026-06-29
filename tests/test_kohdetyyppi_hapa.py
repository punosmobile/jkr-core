"""
Testit kohdetyypin määräytymiselle HAPA-aineiston perusteella (LAH-227).

Tarkistaa kohteen kohdetyypin *ennen* HAPA-aineiston lisäystä ja *sen jälkeen*.

DVV-tuonnissa kohteet saavat kohdetyypin asuinkiinteistö (7) rakennusten
käyttötarkoituksen perusteella. Kun HAPA-aineistoon (jkr.hapa_aineisto) lisätään
rivi, jonka rakennustunnus (prt) vastaa kohteen rakennusta ja jonka voimassaolo
leikkaa kohteen voimassaolon, kannan trigger (trg_update_kohde_type_from_hapa,
ks. V2.48.0) päivittää kohteen tyypiksi:
    - hapa     -> 5
    - biohapa  -> 6
BIOHAPA on ensisijainen HAPAan nähden.

Käytetään testikannan DVV-seedin rakennustunnuksia (prt), jotka ovat 1:1
kohteiden kanssa. Jokainen testimetodi käyttää eri prt:tä, joten ne ovat
toisistaan riippumattomia.
"""

from datetime import datetime
from pathlib import Path
from shutil import copytree

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from jkrimporter import conf
from jkrimporter.providers.db.codes import init_code_objects
from jkrimporter.providers.db.database import json_dumps
from jkrimporter.providers.db.dbprovider import import_dvv_kohteet

# Kohdetyyppikoodit (jkr_koodistot.kohdetyyppi)
ASUINKIINTEISTO = 7
HAPA = 5
BIOHAPA = 6

# Testikannan DVV-seedin rakennustunnukset (yksi kohde per prt)
PRT_HAPA = "100456789B"       # Forsström
PRT_BIOHAPA = "200000000A"    # Granström
PRT_PRIORITEETTI = "134567890B"  # Lindroth (saa sekä hapa- että biohapa-rivin)
PRT_EI_HAPA = "000000000A"    # Teivonen (ei koskaan HAPA-aineistossa)


def _cleanup(engine):
    """Poistaa kohteet ja HAPA-aineiston puhtaaseen tilaan."""
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM jkr.kompostorin_kohteet"))
        conn.execute(text("DELETE FROM jkr.kompostori"))
        conn.execute(text("DELETE FROM jkr.keskeytys"))
        conn.execute(text("DELETE FROM jkr.kuljetus"))
        conn.execute(text("DELETE FROM jkr.tyhjennysvali"))
        conn.execute(text("DELETE FROM jkr.sopimus"))
        conn.execute(text("DELETE FROM jkr.viranomaispaatokset"))
        conn.execute(text("DELETE FROM jkr.kohteen_osapuolet"))
        conn.execute(text("DELETE FROM jkr.kohteen_rakennukset"))
        conn.execute(text("DELETE FROM jkr.kohde"))
        conn.execute(text("DELETE FROM jkr.dvv_poimintapvm"))
        conn.execute(text("DELETE FROM jkr.hapa_aineisto"))
        conn.execute(text(
            "DELETE FROM jkr.osapuoli "
            "WHERE tiedontuottaja_tunnus NOT IN ('dvv', 'ilmoitus')"
        ))
        conn.commit()


def _kohdetyyppi_by_prt(session, prt):
    """Palauttaa prt:tä vastaavan kohteen kohdetyyppi_id:n."""
    return session.execute(
        text(
            "SELECT k.kohdetyyppi_id FROM jkr.kohde k "
            "JOIN jkr.kohteen_rakennukset kr ON kr.kohde_id = k.id "
            "JOIN jkr.rakennus r ON r.id = kr.rakennus_id "
            "WHERE r.prt = :prt"
        ),
        {"prt": prt},
    ).scalar()


def _lisaa_hapa_aineisto(session, prt, kohdetyyppi):
    """Lisää HAPA-aineistoriville prt + kohdetyyppi, voimassa 2000-01-01 ->.

    Insert laukaisee triggerin, joka päivittää kohteen tyypin.
    """
    session.execute(
        text(
            "INSERT INTO jkr.hapa_aineisto "
            "(rakennus_id_tunnus, kohdetyyppi, voimassa) "
            "VALUES (:prt, :tyyppi, daterange('2000-01-01', NULL))"
        ),
        {"prt": prt, "tyyppi": kohdetyyppi},
    )
    session.commit()


class TestKohdetyyppiHapa:
    """Kohdetyypin muutos HAPA-aineiston perusteella (ennen/jälkeen)."""

    @pytest.fixture(scope="class", autouse=True)
    def kohteet(self):
        """Luo testikohteet DVV-tuonnilla kerran luokan testeille."""
        engine = create_engine(
            "postgresql://{username}:{password}@{host}:{port}/{dbname}".format(
                **conf.dbconf
            ),
            future=True,
            json_serializer=json_dumps,
        )
        _cleanup(engine)
        source = Path(__file__).parent / "data" / "test_data_import"
        with Session(engine) as session:
            init_code_objects(session)
            import_dvv_kohteet(
                session,
                poimintapvm=datetime.strptime("28.1.2022", "%d.%m.%Y").date(),
                perusmaksutiedosto=source / "perusmaksurekisteri.xlsx",
            )
        try:
            yield engine
        finally:
            _cleanup(engine)

    def test_hapa_aineisto_muuttaa_kohteen_hapaksi(self, kohteet):
        engine = kohteet
        with Session(engine) as session:
            # Ennen: asuinkiinteistö
            assert _kohdetyyppi_by_prt(session, PRT_HAPA) == ASUINKIINTEISTO, \
                "Kohteen tulisi olla asuinkiinteistö ennen HAPA-aineistoa"

            _lisaa_hapa_aineisto(session, PRT_HAPA, "hapa")

            # Jälkeen: hapa
            assert _kohdetyyppi_by_prt(session, PRT_HAPA) == HAPA, \
                "Kohteen tulisi olla hapa HAPA-aineiston lisäyksen jälkeen"

    def test_biohapa_aineisto_muuttaa_kohteen_biohapaksi(self, kohteet):
        engine = kohteet
        with Session(engine) as session:
            assert _kohdetyyppi_by_prt(session, PRT_BIOHAPA) == ASUINKIINTEISTO, \
                "Kohteen tulisi olla asuinkiinteistö ennen BIOHAPA-aineistoa"

            _lisaa_hapa_aineisto(session, PRT_BIOHAPA, "biohapa")

            assert _kohdetyyppi_by_prt(session, PRT_BIOHAPA) == BIOHAPA, \
                "Kohteen tulisi olla biohapa BIOHAPA-aineiston lisäyksen jälkeen"

    def test_biohapa_priorisoituu_hapan_yli(self, kohteet):
        engine = kohteet
        with Session(engine) as session:
            assert _kohdetyyppi_by_prt(session, PRT_PRIORITEETTI) == ASUINKIINTEISTO

            # Sama rakennus sekä hapa- että biohapa-aineistossa -> biohapa voittaa
            _lisaa_hapa_aineisto(session, PRT_PRIORITEETTI, "hapa")
            _lisaa_hapa_aineisto(session, PRT_PRIORITEETTI, "biohapa")

            assert _kohdetyyppi_by_prt(session, PRT_PRIORITEETTI) == BIOHAPA, \
                "BIOHAPA on ensisijainen HAPAan nähden"

    def test_ei_hapa_aineistossa_sailyy_asuinkiinteistona(self, kohteet):
        engine = kohteet
        with Session(engine) as session:
            # Tämä kohde ei ole missään testimetodissa HAPA-aineistossa,
            # joten sen tulee säilyä asuinkiinteistönä riippumatta muista riveistä.
            assert _kohdetyyppi_by_prt(session, PRT_EI_HAPA) == ASUINKIINTEISTO, \
                "HAPA-aineiston ulkopuolisen kohteen tyyppi ei saa muuttua"
